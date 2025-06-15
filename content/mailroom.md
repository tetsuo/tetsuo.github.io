---
title: Account workflow automation with PostgreSQL and C
cover_title: Account workflow automation with PostgreSQL and C
description: How PostgreSQL alone can automate your account activation and password reset workflows without needing a message broker
tags: sql,c,rust,tutorial
published: 2024-11-17T00:00:00
updated: 2025-06-15T13:37:00
---

> How PostgreSQL alone can automate your account activation and password reset workflows without needing a message broker.

[**mailroom**](https://github.com/tetsuo/mailroom/) uses PostgreSQL [triggers](https://www.postgresql.org/docs/current/sql-createtrigger.html) and [notification events](https://www.postgresql.org/docs/current/sql-notify.html) to detect account status changes and send relevant email notifications to users.

In this tutorial, we'll walk through the mailroom architecture by building a real-world onboarding workflow step by step. We'll start by setting up the schema and triggers to track account updates using a PostgreSQL-backed queue. Then, we'll implement a collector in C using the `libpq` library to consume the events triggered by those account changes and process action tokens in batches.

---

## Overview

The system comprises two main actors:

- **User**: Responsible for creating and activating accounts.
- **Admin**: Can suspend accounts.

Key components include:

- **Accounts**: A table for storing users and their lifecycle states.
- **Tokens**: A table for managing activation and recovery tokens.
- **Triggers**: Automate processes like status updates, notifications, and timestamp modifications.

Here's the sequence diagram outlining the workflows:

![Workflows](./images/mercury-postgresql-workflows.svg)

---

## Accounts table

The `accounts` table manages user data and tracks account lifecycle states.

```sql
CREATE TYPE account_status AS ENUM (
    'provisioned',
    'active',
    'suspended'
);

CREATE TABLE accounts (
    id                  BIGSERIAL PRIMARY KEY,
    email               VARCHAR(254) UNIQUE NOT NULL,
    status              account_status DEFAULT 'provisioned' NOT NULL,
    login               VARCHAR(254) UNIQUE NOT NULL,
    created_at          INTEGER DEFAULT EXTRACT(EPOCH FROM NOW()) NOT NULL,
    status_changed_at   INTEGER,
    activated_at        INTEGER,
    suspended_at        INTEGER,
    unsuspended_at      INTEGER
);
```

Here, the `status` field tracks the current state of the account (`provisioned`, `active`, or `suspended`), while timestamps like `status_changed_at` and `activated_at` capture important lifecycle events, helping to maintain the `status` field correctly during transitions and ensuring accurate tracking of account states over time.

---

## Tokens table

The `tokens` table tracks actionable tokens, such as those used for activation or password recovery.

```sql
CREATE TYPE token_action AS ENUM (
    'activation',
    'password_recovery'
);

CREATE TABLE tokens (
    id          BIGSERIAL PRIMARY KEY,
    action      token_action NOT NULL,
    secret      BYTEA DEFAULT gen_random_bytes(32) UNIQUE NOT NULL,
    code        VARCHAR(5) DEFAULT LPAD(TO_CHAR(RANDOM() * 100000, 'FM00000'), 5, '0'),
    account     BIGINT NOT NULL,
    expires_at  INTEGER DEFAULT EXTRACT(EPOCH FROM NOW() + INTERVAL '15 minute') NOT NULL,
    consumed_at INTEGER,
    created_at  INTEGER DEFAULT EXTRACT(EPOCH FROM NOW()) NOT NULL,

    FOREIGN KEY (account) REFERENCES accounts (id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
```

##### Key columns:

- `action` – Specifies the token type (`activation` or `password recovery`).
- `secret` – A unique and secure token string.
- `code` – A short, human-readable security code.
- `expires_at` – Defines the expiration time for tokens, defaulting to 15 minutes.

This table complements the `accounts` table by managing token-based actions, with relationships maintained through the foreign key `account`.

---

## Triggers

PostgreSQL triggers allow us to automate processes in response to data changes. Below are the triggers to ensure seamless management of account status transitions, token consumption, and notifications.

### 1. **Before account insert**

- **Event**: Before an account is inserted into the `accounts` table.
- **Purpose**: Automatically creates an activation token when a new account is provisioned.

```plpgsql
CREATE OR REPLACE FUNCTION trg_before_account_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.status = 'provisioned') THEN
        INSERT INTO
        tokens
            (account, action)
        VALUES
            (NEW.id, 'activation');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_account_insert
    BEFORE INSERT ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION trg_before_account_insert ();
```

> ##### Why not an AFTER trigger?
>
> While it may seem logical to create the token _after_ confirming the account's existence (since the token is ultimately tied to the account), this approach has a critical flaw: if the token insertion fails, we could end up with an account that lacks a corresponding activation token, which would break downstream processes.
>
> The `BEFORE` trigger ensures that token creation and account insertion are part of the same transaction, guaranteeing the consistency we need. If token creation fails, the entire transaction will be rolled back, preventing the system from entering an invalid state.
>
> This is why the `DEFERRABLE INITIALLY DEFERRED` constraint is applied to the `tokens` table. It allows a token to be inserted even before the associated account is created, provided both operations occur within the same transaction.

### 2. **Before account status change**

- **Event**: Before an account's `status` is updated.
- **Purpose**: Updates timestamps for key status changes (e.g., activated, suspended, unsuspended).

```plpgsql
CREATE OR REPLACE FUNCTION trg_before_account_status_change ()
    RETURNS TRIGGER
    AS $$
DECLARE
    ts integer := extract(epoch FROM now());
BEGIN
    IF (NEW.status = OLD.status) THEN
        RETURN NEW;
    END IF;

    NEW.status_changed_at = ts;

    IF (NEW.status = 'active') THEN
        IF (OLD.status = 'provisioned') THEN
            NEW.activated_at = ts;
        ELSIF (OLD.status = 'suspended') THEN
            NEW.unsuspended_at = ts;
            NEW.suspended_at = NULL;
            -- Revert status to 'provisioned' if never activated
            IF (OLD.activated_at IS NULL) THEN
              NEW.status = 'provisioned';
            END IF;
        END IF;
    ELSIF (NEW.status = 'suspended') THEN
        NEW.suspended_at = ts;
        NEW.unsuspended_at = NULL;
    END IF;
    RETURN new;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER before_account_status_change
    BEFORE UPDATE OF status ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION trg_before_account_status_change ();
```

### 3. **After token consumed**

- **Event**: After a token's `consumed_at` field in `tokens` is updated.
- **Purpose**: Activates the associated account when an activation token is consumed.

```plpgsql
CREATE OR REPLACE FUNCTION trg_after_token_consumed ()
    RETURNS TRIGGER
    AS $$
BEGIN
    IF (NEW.action != 'activation') THEN
        RETURN NULL;
    END IF;
    -- Activate account
    UPDATE
        accounts
    SET
        status = 'active'
    WHERE
        id = NEW.account
        AND status = 'provisioned';
    RETURN NULL;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER after_token_consumed
    AFTER UPDATE OF consumed_at ON tokens
    FOR EACH ROW
    WHEN (NEW.consumed_at IS NOT NULL AND OLD.consumed_at IS NULL)
    EXECUTE FUNCTION trg_after_token_consumed ();
```

### 4. **After token inserted**

- **Event**: After a token is inserted into the `tokens` table.
- **Purpose**: Notifies external services that a new token has been created.

```plpgsql
CREATE OR REPLACE FUNCTION trg_after_token_inserted()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    NOTIFY token_insert;
    RETURN NULL;
END;
$$;

CREATE TRIGGER after_token_inserted
    AFTER INSERT ON tokens
    FOR EACH ROW
    EXECUTE FUNCTION trg_after_token_inserted ();
```

---

## Let's try it out!

Follow these steps to test the triggers and notifications in action:

### Setting your environment

_(Skip this section if you've already set up the tables and triggers.)_

Clone the [`tetsuo/mailroom`](https://github.com/tetsuo/mailroom) repository:

```sh
git clone https://github.com/tetsuo/mailroom.git
```

Run the following command to create a new database in PostgreSQL:

```sh
createdb mailroom
```

Then, navigate to the `migrations` folder and run:

```sh
psql -d mailroom < 0_init.up.sql
```

Alternatively, you can use [go-migrate](https://github.com/golang-migrate/) which is often my preference.

---

### Inspect the initial state

Before adding any data, let's take a look at the initial state of the `jobs` table:

```sh
psql -d mailroom -c "SELECT * FROM jobs;"
```

You should see one row with `job_type` set to `mailroom` and `last_seq` set to zero:

```
 job_type | last_seq
----------+----------
 mailroom |        0
(1 row)
```

---

### Create a new account

Insert a new account into the `accounts` table. This should automatically generate an activation token.

```sql
INSERT INTO accounts (email, login)
	VALUES ('user@example.com', 'user123');
```

**Tip:** To insert three records with randomized email and login fields, use the following command:

```sh
printf "%.0sINSERT INTO accounts (email, login) VALUES ('user' || md5(random()::text) || '@fake.mail', 'user' || substr(md5(random()::text), 1, 20));\n" {1..3} | \
    psql -d mailroom
```

**Expected outcome**:

- A new account with `status = 'provisioned'` is added to `accounts`.
- An activation token is automatically inserted into the `tokens` table, linked to the account.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
SELECT * FROM tokens WHERE account = 1;
```

Here's an example `account` record:

```
-[ ACCOUNT 1 ]-------------------------------------------------------------------
id                | 1
email             | usere3213152e8cdf722466a011b1eaa3c98@fake.mail
status            | provisioned
login             | user85341405cb33cbe89a5f
created_at        | 1735709763
status_changed_at |
activated_at      |
suspended_at      |
unsuspended_at    |
```

The corresponding `token` record generated by the trigger function:

```
-[ TOKEN 1 ]---------------------------------------------------------------------
id          | 1
action      | activation
secret      | \x144d3ba23d4e60f80d3cb5cf25783539ba267af34aecd71d7cc888643c912fb7
code        | 06435
account     | 1
expires_at  | 1735710663
consumed_at |
created_at  | 1735709763
```

---

### Consume the activation token

Simulate token consumption by updating the `consumed_at` field in the `tokens` table.

```sql
UPDATE
	tokens
SET
	consumed_at = extract(epoch FROM now())
WHERE
	account = 1
	AND action = 'activation';
```

**Expected outcome**:

- The account's `status` in `accounts` should change to `active`.
- The `activated_at` timestamp should be updated in `accounts`.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
SELECT * FROM tokens WHERE account = 1;
```

---

### Suspend the account

Change the account's status to `suspended` to test the suspension flow.

```sql
UPDATE accounts SET status = 'suspended' WHERE id = 1;
```

**Expected outcome**:

- The account's `suspended_at` timestamp is updated.
- The `unsuspended_at` field is cleared.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
```

---

### Unsuspend the account

Restore the account's status to `active`.

```sql
UPDATE accounts SET status = 'active' WHERE id = 1;
```

**Expected outcome**:

- The account's `unsuspended_at` timestamp is updated.
- The `suspended_at` field is cleared.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
```

---

### Observe notifications

Listen for token creation notifications on the `token_insert` channel using `LISTEN`:

```sql
LISTEN token_insert;
```

Next, insert some dummy data into the `accounts` table (or directly into `tokens`).

**Expected outcome**:

The `LISTEN` session should immediately display a notification like:

```
Asynchronous notification "token_insert" with payload "" received.
```

`psql` might need a little nudge (empty `;`) to display notifications:

```
mailroom=# LISTEN token_insert;
LISTEN
mailroom=# ;
Asynchronous notification "token_insert" received from server process with PID 5148.
Asynchronous notification "token_insert" received from server process with PID 5148.
Asynchronous notification "token_insert" received from server process with PID 5148.
```

_These notifications signal that new tokens have arrived—it's time to start processing them._

---

## Jobs table

Now we need to build a mechanism to collect newly added tokens. To do that, we'll define a query that manages their progression through the queue.

We use the jobs table to maintain a cursor that advances through tokens. This table simply tracks the last processed token (`last_seq`) for each job type:

```sql
CREATE TYPE job_type AS ENUM (
    'mailroom'
);

CREATE TABLE jobs (
    job_type job_type PRIMARY KEY,
    last_seq BIGINT
);
```

**Initialize the mailroom queue:**

```sql
INSERT INTO
jobs
    (last_seq, job_type)
VALUES
    (0, 'mailroom');
```

### Retrieving pending jobs

The following query retrieves relevant job data (tokens and account details), ensuring only valid, unexpired, and unprocessed tokens are selected, with accounts in the correct status for the intended action.

```sql
SELECT
    t.account,
    t.secret,
    t.code,
    t.expires_at,
    t.id,
    t.action,
    a.email,
    a.login
FROM
    jobs
    JOIN tokens t
        ON t.id > jobs.last_seq
        AND t.expires_at > EXTRACT(EPOCH FROM NOW())
        AND t.consumed_at IS NULL
        AND t.action IN ('activation', 'password_recovery')
    JOIN accounts a
    ON a.id = t.account
    AND (
      (t.action = 'activation' AND a.status = 'provisioned')
      OR (t.action = 'password_recovery' AND a.status = 'active')
    )
WHERE
    jobs.job_type = 'mailroom'
ORDER BY
    id ASC
LIMIT 10
```

**Joins & filters explained:**

- **Jobs table:** We filter for rows where `job_type` is `mailroom`.
- **Tokens table:**
  - We join tokens with jobs using the condition `tokens.id > jobs.last_seq`, which ensures we only process tokens that haven't been handled yet.
  - We further filter tokens to include only those that are not expired (`expires_at` is in the future), have not been consumed (`consumed_at` is NULL), and have an action of either `activation` or `password_recovery`.
- **Accounts table:**
  - We join accounts on `accounts.id = tokens.account`.
  - For tokens with the `activation` action, the account must be in the `provisioned` state.
  - For tokens with the `password_recovery` action, the account must be `active`.

### Dequeueing and advancing the cursor

Next, we integrate this query into a common table expression:

```sql
WITH token_data AS (
    -- Insert SELECT query here
),
updated_jobs AS (
  UPDATE
    jobs
  SET
    last_seq = (SELECT MAX(id) FROM token_data)
  WHERE
    EXISTS (SELECT 1 FROM token_data)
  RETURNING last_seq
)
SELECT
  td.action,
  td.email,
  td.login,
  td.secret,
  td.code
FROM
  token_data td
```

This accomplishes two key tasks:

1. **Retrieves tokens** generated after the current `last_seq` along with the corresponding user data.
2. **Updates the `last_seq` value** to prevent processing the same tokens again.

**Output example:**

```
-[ RECORD 1 ]--------------------------------------------------------------
action | activation
email  | usere3213152e8cdf722466a011b1eaa3c98@fake.mail
login  | user85341405cb33cbe89a5f
secret | \x144d3ba23d4e60f80d3cb5cf25783539ba267af34aecd71d7cc888643c912fb7
code   | 06435
-[ RECORD 2 ]--------------------------------------------------------------
action | activation
email  | user41e8b6830c76870594161150051f8215@fake.mail
login  | user2491d87beb8950b4abd7
secret | \x27100e07220b62e849e788e6554fede60c96e967c4aa62db7dc45150c51be23f
code   | 80252
-[ RECORD 3 ]--------------------------------------------------------------
action | activation
email  | user7bb11e235c85afe12076884d06910be4@fake.mail
login  | user91ab8536cb05c37ff46a
secret | \xa9763eec727835bd97b79018b308613268d9ea0db70493fd212771c9b7c3bcb2
code   | 31620
```

#### Indexes

To optimize the query performance, the following composite indexes are recommended:

```sql
CREATE INDEX accounts_id_status_idx ON accounts (id, status);

CREATE INDEX tokens_id_expires_consumed_action_idx ON tokens
    (id, expires_at, consumed_at, action);
```

Indexing Strategy:

- **Equality Conditions First**: Since columns used in equality conditions (`=` or `IN`) are typically the most selective, they should come first.
- **Range Conditions Next**: Columns used in range conditions (`>`, `<`, `BETWEEN`) should follow.

---

## Collector behavior

Instead of continuously polling the database for new batches, a lightweight service is set up to subscribe to a notification channel, monitor incoming events, and trigger the previously defined job retrieval query when either a certain **row limit** is reached (based on received notifications) or a **timeout** occurs.

Here's how the job retrieval and batch execution are controlled:

#### Batch limit

> The maximum number of email destinations in a single batch.

A collector queries the database for at most **N** tokens at a time (where **N** is the **batch limit**). Even if 500 tokens are waiting in the database, the collector will only take, say, 10 at a time. This imposes a hard cap on the throughput of tokens that can leave the database at once.

#### Batch timeout

> The time to wait for accumulating enough notifications to fill a batch.

A collector waits up to **X** milliseconds before processing incoming notifications (where **X** is the **batch timeout**). If fewer than the batch limit have arrived during that period, the collector will still dequeue whatever did arrive, but it won't pull more immediately. In effect, this sets an upper limit on how long new tokens can linger before being handed over to the email sender.

##### Example

If you set:

- A batch **timeout** of 30 seconds.
- A **limit** of 10 notifications.

This means:

- If 10 notifications arrive in quick succession, the batch is triggered immediately.
- If fewer than 10 arrive over 30 seconds, the batch is triggered when the timeout ends.

⚠️ **Keep in mind that a collector doesn't impose rate limiting;** it primarily controls database roundtrips and batch size. A large influx of notifications will keep triggering the batch limit, effectively bypassing the timeout, so the overall token throughput downstream remains largely unaffected.

---

## Implementation details

`collector` is written in C and interacts with PostgreSQL via [**libpq**](https://www.postgresql.org/docs/current/libpq.html). It is responsible solely for collecting jobs and writing them to output in a structured format.

### Dequeuing jobs

When the connection is established, `collector` issues a `LISTEN` command on the specified channel and creates the prepared statements for subsequent queries.

As notifications arrive, it fetches tokens **in batches** and writes the results directly to stdout. Processing continues until all queued tokens are exhausted or an error occurs.

> 📄 **See the full implementation in [`db.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/db.c#L234C1-L252C2)**

### Batch output structure

The results are output as **line-delimited batches**, formatted as **comma-separated values** in the following order:

```
action,email,username,secret,code
```

Each batch is represented as a single line, where every row follows this schema:

- `action` – Numeric representation of the email action type (e.g., `1` for activation, `2` for password recovery).
- `email` – Recipient's email address.
- `username` – Recipient's login name.
- `secret` – A base64 URL-encoded string containing the signed token.
- `code` – (Optional) Numeric code (e.g., for password recovery).

##### Example output

In this example, the first line contains a batch of three jobs, including both password recovery and account activation. The second line contains a single activation job:

```
2,john.doe123@fakemail.test,johndoe,0WEKrnjY_sTEqogrR6qsp7r7Vg4SQ_0iM_1La5hHp5p31nbkrHUBS0Cz9T24iBDCk6CFqO7tJTihpsOVuHYgLg,35866,1,jane.smith456@notreal.example,janesmith,BfQXx31qfY2IJFTtzAp21IdeW0dDIxUT1Ejf3tYJDukNsfaxxOfldwL-lEfVy4SEkZ_v18rf-EWsvWXH5qgvIg,24735,1,emma.jones789@madeup.mail,emmajones,jxrR5p72UWTQ8JiU2DrqjZ-K8L4t8i454S9NtPkVn4-1-bin3ediP0zHMDQU2J_iIyzH4XmNtzpXZhjV0n5xcA,25416
1,sarah.connor999@unreal.mail,resistance1234,zwhCIthd12DqpQSGB57S9Ky-OXV_8H0e8aHOv_kWoggIuAZ2sc-aQVpIoQ-M--PjwVfdIIxiXkv_WjRjGI57zA,38022
```

### Signing and validating tokens

During the dequeue operation, the token's secret is signed using HMAC-SHA256 and encoded in URL-safe Base64 format. This enables the frontend to verify the authenticity of a token without performing an immediate database lookup.

The encoded secret consists of:

- A **path name** (e.g., `/activate` or `/recover`).
- The **original secret** (and **code**, in the case of recovery).
- A **cryptographic signature** generated from the secret.

```c
static size_t construct_signature_data(char *output, const char *action,
                                       const unsigned char *secret, const char *code)
{
  size_t offset = 0;

  if (strcmp(action, "activation") == 0)
  {
    memcpy(output, "/activate", 9); // "/activate" is 9 bytes
    offset = 9;
    memcpy(output + offset, secret, 32);
    offset += 32;
  }
  else if (strcmp(action, "password_recovery") == 0)
  {
    memcpy(output, "/recover", 8); // "/recover" is 8 bytes
    offset = 8;
    memcpy(output + offset, secret, 32);
    offset += 32;
    memcpy(output + offset, code, 5); // code is 5 bytes
    offset += 5;
  }

  return offset; // Total length of the constructed data
}
```

ℹ️ _If you'd like to see how verification works on the backend, check out [`verifyHmac.js`](https://github.com/tetsuo/mailroom/blob/master/etc/verifyHmac.js) in the repo._

##### Security considerations

* **Handle expired tokens properly.** One approach is to include `expires_at` in the payload so expiration can be checked without a DB call. For stronger protection, cache consumed tokens until they naturally expire to prevent reuse within their validity window.
* **Regularly rotate your signing key.**

### Main loop logic

<!-- In [`main.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/main.c), you'll find references to environment variables such as `MAILROOM_BATCH_TIMEOUT`, `MAILROOM_BATCH_LIMIT`, and `MAILROOM_SECRET_KEY` (a 32-byte random value, represented as a 64-character hex string). Refer to the [`README`](https://github.com/tetsuo/mailroom/blob/master/README.md#environment-variables) file for the full list. -->

At a high level, the main loop continuously:

- 🔄 **Dequeues and processes** ready batches
- 📩 **Checks for new notifications**
- ⏳ **Waits on** `select()` **for database activity or a timeout**
- 🩺 **Performs periodic health checks**
- 🔌 **Reconnects** to the database if needed

When the **batch limit** is reached or the **timeout expires**, the collector executes the **dequeue query**. If a broken connection is detected, it attempts to **reconnect and resume processing** once stable.

**Pseudo-code representation:**

```
// 🌟 Main processing loop
WHILE the application is running 🔄
    // 🔌 Handle reconnection if needed
    IF the connection is not ready ❌ THEN
        reconnect to the database 🔄
        initialize the connection ✅
        reset counters 🔢
        CONTINUE to the next iteration ⏩
    END IF

    // 📦 Process ready batches
    IF ready for processing ✅ THEN
        dequeue and process a batch of items 📤
        reset state for the next cycle 🔁
        CONTINUE to the next iteration ⏩
    END IF

    // 🛎️ Handle pending notifications
    process all incoming notifications 📥
    IF notifications exceed the batch limit 🚨 THEN
        mark ready for processing ✅
        CONTINUE to the next iteration ⏩
    END IF

    // ⏱️ Wait for new events or timeout
    wait for activity on the connection 📡 or timeout ⌛
    IF interrupted by a signal 🚨 THEN
        handle the signal (e.g., shutdown) ❌
        CONTINUE to the next iteration ⏩
    ELSE IF timeout occurs ⏳ THEN
        IF notifications exist 📋 THEN
            mark ready for processing ✅
            CONTINUE to the next iteration ⏩
        END IF
        perform periodic health checks 🩺
    END IF

    // 🛠️ Consume available data
    consume data from the connection 📶
    prepare for the next cycle 🔁
END WHILE
```

> 📄 **See the full implementation in [`main.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/main.c#L203)**

The [`select()`](https://man7.org/linux/man-pages/man2/select.2.html) system call plays a key role in the program's operation. It is a UNIX mechanism that monitors file descriptors (e.g., sockets) to check if they are ready for I/O operations like reading or writing. In this code, `select()` is used to monitor the socket for new notifications and **enforce a timeout** for batch processing.

Once `select()` signals that data is available, `PQconsumeInput` is called to read incoming data into libpq's internal buffers. Then `PQnotifies` is invoked to retrieve any pending notifications and update the counter.

> 📖 **Learn more about [libpq's async API](https://www.postgresql.org/docs/current/libpq-async.html)**

---

## Compile & run

To compile, verify that you have `openssl@3` and `libpq@5` installed, then use the provided `Makefile`.

### Run the collector

Use the following command to build and run the `collector` executable with example configuration variables:

```sh
make && \
  MAILROOM_BATCH_LIMIT=3 \
  MAILROOM_BATCH_TIMEOUT=5000 \
  MAILROOM_DATABASE_URL="dbname=mailroom" \
  MAILROOM_SECRET_KEY="cafebabecafebabecafebabecafebabecafebabecafebabecafebabecafebabe" \
  ./collector
```

> **Refer to the [`README`](https://github.com/tetsuo/mailroom/blob/master/README.md#environment-variables) file for the full list of environment variables**

Once configured and started, it will log its activity:

```
2024/04/20 13:37:00 [PG] configured; channel=token_insert queue=mailroom limit=3 timeout=5000ms healthcheck-interval=270000ms
2024/04/20 13:37:00 [PG] connecting to host=/tmp port=5432 dbname=mailroom user=ogu sslmode=disable
2024/04/20 13:37:00 [PG] connected
```

---

### Insert accounts and observe batching

In another terminal, insert 5 accounts:

```sh
printf "%.0sINSERT INTO accounts (email, login) VALUES ('user' || md5(random()::text) || '@fake.mail', 'user' || substr(md5(random()::text), 1, 20));\n" {1..5} | \
    psql -d mailroom
```

You'll observe that `collector` immediately process the first batch of three items. After a 5-second delay (as defined by the `MAILROOM_BATCH_TIMEOUT`), it processes the remaining two in a second batch:

```
2024/04/20 13:37:00 [PG] NOTIFY called; waking up
2024/04/20 13:37:00 [PG] processing 3 rows... (max reached)
1,userb183abb7a25d04027061e6b8d8d8e7fa@fake.mail,userb0bf075b82b892f53d97,gVRNesi-opSvs3ntPfr9DzSn_JwbOD04VVIurQSCOFzzd3BOM3WBDL3SOtDjMxKLd6csSn8_p9hemXHIUxIjPg,78092,1,user43b01ba9686c886473e526429dd2c672@fake.mail,userf420078dba4fd5a91de2,--DTy5LsbDeLP_AweXIPSjL3_avQMT5cH_bRxPy1uxQLVhXKaw7Oxd7NYkcJ6MZmnnqWqTcBPHA5z7bqunXEAA,25778,1,user46f81dfd34b91a1904ac4524193575aa@fake.mail,user6d91baab56d2823b326d,ryooWewe3OTxIGF1Gjl5Vvl8BsXoqWVbCAt1t6J--_KX1SM4DbyCes4yn75OWVe60G4MMZdv4byRh1wy-Clvxw,78202
2024/04/20 13:37:00 [PG] NOTIFY called; waking up
2024/04/20 13:37:05 [PG] processing 2 rows... (timeout)
1,user12d2722e1c07b0a531ea69ae125d4697@fake.mail,user853ae29eefc5d44a6bc6,4pmew2o2EOAZBDHWvJBcixJftpRCb8uyXZhzN12EOcrLBmzc4ic9avwd9dla09pIiKIoqW5iIwMfoXLEM3_LGw,38806,1,user9497d0e033019fcf3198eecb053ba40e@fake.mail,userfcde338dba96cc419613,ANLMa-1y37VLCDqK0wnfEFhUVzHsWpaNGV2ttI8m3o6_lbbYOKmp3hP7Q8H8ZQRNMPAj4xsSqC26nesfVZLgzQ,89897
```

---

### Testing reconnect behavior

To simulate a dropped connection, open another terminal, connect to the `mailroom` db via `psql`, and run:

```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE
  datname = 'mailroom'
  AND pid <> pg_backend_pid();
```

After the connection is killed, `select()` wakes up, causing `PQconsumeInput()` to fail with an error. The process logs a reconnect attempt, and once reconnected, it resumes processing without losing track of queued tokens during the downtime.

```
2024/04/20 13:37:42 [PG] WARN: error consuming input: server closed the connection unexpectedly
        This probably means the server terminated abnormally
        before or while processing the request.

2024/04/20 13:37:42 [PG] connecting to host=/tmp port=5432 dbname=mailroom user=ogu sslmode=disable
2024/04/20 13:37:42 [PG] connected
```

---

## Further improvements

Building on this foundation, you can extend your triggers to support more complex workflows and fine-tune the collector to operate under stricter constraints, all while keeping the database at the core of event processing.

Before we conclude, let's explore some potential improvements, starting with support for multiple worker setups.

---

### 1. Multiple workers

When you update `last_seq`, PostgreSQL locks the `jobs` row being updated, preventing other processes from modifying it until the transaction is complete. However, PostgreSQL **does not prevent multiple processes from attempting to read the same cursor** before one updates it. This can lead to duplicate processing if you're not careful.

If there's any chance of concurrent execution, using `FOR UPDATE` is essential:

```sql
...
    FROM
        jobs
        -- Lock the `jobs` record to prevent concurrent access
        FOR UPDATE
        JOIN tokens t ON t.id > jobs.last_seq
...
```

##### Without locking:
   - Consumer A reads `jobs.last_seq = 100`.
   - Consumer B also reads `jobs.last_seq = 100` before A updates it.
   - Both consumers select tokens where `t.id > 100`, potentially processing the same tokens.

##### With FOR UPDATE:
   - Consumer A locks the `jobs` record and reads `last_seq = 100`.
   - Consumer B tries to read `jobs.last_seq` but is blocked until Consumer A's transaction completes.
   - Consumer A updates `last_seq` to, say, `150` and releases the lock.
   - Consumer B then reads the updated `last_seq = 150`, processing the next set of tokens.

---

Alternatively, to efficiently handle **multiple consumers**, you might consider **eliminating the `jobs` table altogether**. Instead, add a new field, such as `processed_at`, to the `tokens` table. This field will indicate when a token has been processed. By updating `processed_at` during token retrieval, you can use `FOR UPDATE SKIP LOCKED` to support a multi-consumer setup in a safe fashion.

However, if you're certain that only a single consumer runs this query at any given time, I recommend sticking with the `jobs` table as a single point of reference. This approach avoids the need for complex locking mechanisms, and you can further enhance the `jobs` table to keep a history of job executions, parameters, and statuses, which can be valuable for auditing purposes.

---

### 2. Priority queues

The current queueing mechanism processes tokens without distinguishing between their types and lacks the ability to prioritize critical ones, such as password recovery, over less urgent emails like account activations. At present, '10 emails per second' could mean 10 emails of the same type or a mix, depending on the batch. While effective, this design leaves room for improvement, such as introducing prioritization or smarter batching strategies.

---

### 3. Adaptive batching

User activity is rarely consistent—there are bursts of high traffic that may far exceed daily or hourly quotas, followed by periods of minimal activity. Rather than using fixed limits and timeouts, batch size and timeout values can be dynamically adjusted based on real-time conditions. During low-traffic periods, the batch size can be increased to improve efficiency. During peak hours, it can be reduced to minimize delays.

---

## What's next?

⏭ While not covered in this post, a **Rust-based** SES email sender is available in the `sender` folder of the [repository](https://github.com/tetsuo/mailroom/tree/master/sender). It consumes the collector's output to send bulk emails.
