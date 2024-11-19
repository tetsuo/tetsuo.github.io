---
title: End-to-End Workflow Automation with PostgreSQL and Go: Part 1
cover_title: End-to-End Workflow Automation with PostgreSQL and Go: Part 1
description: Building a reactive account management system with PostgreSQL triggers and real-time notifications
tags: sql,reactive,database
published: 2024-11-17T00:00:00
updated: 2024-11-17T00:00:00
---

> Build a reactive account management system with PostgreSQL, using triggers, tokens, and real-time notifications to automate user workflows like activation and status changes.

>> In this two-part series, we'll build a cost-effective email notification system for token-based user actions. The first part focuses on implementing the foundational workflows using **PostgreSQL**, while the second part will extend the solution with **Go** to enable batch processing, parallelism, and other optimizations.

Did you know that PostgreSQL can automate complex workflows, react to data changes, and even send notifications—all without relying on any third-party extension or complicated application logic.

In this article, we'll demonstrate these capabilities by building a simple account management system that leverages **triggers** and **real-time notifications** to handle tasks like account activation, password recovery, and status changes, laying the groundwork for a database-driven email notification system that efficiently responds to user actions.

# Overview

The system comprises two main actors:

- **User**: Responsible for creating and activating accounts.
- **Admin**: Has the ability to suspend accounts.

Key components include:

- **Accounts**: A table for storing users and their lifecycle states.
- **Tokens**: A table for managing activation and recovery tokens.
- **Triggers**: Automate processes like status updates, notifications, and timestamp modifications.

Here's the sequence diagram outlining the workflows:

![Workflows](./images/mercury-postgresql-workflows.svg)

# Accounts

We start by defining the `accounts` table, which manages user data and tracks the lifecycle states of accounts.

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

# Tokens

The `tokens` table tracks actionable tokens, such as those used for activation or password recovery.

```sql
CREATE TYPE token_action AS ENUM (
    'activation',
    'password_recovery'
);

CREATE TABLE tokens (
    id          BIGSERIAL PRIMARY KEY,
    action      token_action NOT NULL,
    secret      VARCHAR(64) DEFAULT encode(gen_random_bytes(32), 'hex') UNIQUE NOT NULL,
    code        VARCHAR(5) DEFAULT LPAD(TO_CHAR(RANDOM() * 100000, 'FM00000'), 5, '0'),
    account     BIGINT NOT NULL,
    expires_at  INTEGER DEFAULT EXTRACT(EPOCH FROM NOW() + INTERVAL '15 minute') NOT NULL,
    consumed_at INTEGER,
    created_at  INTEGER DEFAULT EXTRACT(EPOCH FROM NOW()) NOT NULL,

    FOREIGN KEY (account) REFERENCES accounts (id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
```

### Key Columns:

- **`action`**: Specifies the token type (`activation` or `password recovery`).
- **`secret`**: A unique and secure token string.
- **`code`**: A short, human-readable security code.
- **`expires_at`**: Defines the expiration time for tokens, defaulting to 15 minutes.

This table complements the `accounts` table by managing token-based actions, with relationships maintained through the foreign key `account`.

# Trigger Definitions

PostgreSQL triggers allow us to automate processes in response to data changes. Below are the triggers to ensure seamless management of account status transitions, token consumption, and notifications.

## 1. **Before Account Insert**

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

#### Why not an `AFTER` trigger?

While it may seem logical to create the token _after_ confirming the account's existence (since the token depends on the account), this approach has a critical flaw: if the token insertion fails, you could end up with an account that lacks a corresponding activation token, breaking downstream processes. To ensure **atomicity**, we use a `BEFORE` trigger, which rolls back the **entire transaction** if any part of it fails.

This is why the `DEFERRABLE INITIALLY DEFERRED` constraint is applied to the `tokens` table. It allows a token to be inserted even before the associated account is created, provided both operations occur within the same transaction.

## 2. **Before Account Status Change**

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

## 3. **After Token Consumed**

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

## 4. **After Token Inserted**

- **Event**: After a token is inserted into the `tokens` table.
- **Purpose**: Notifies external services that a new token has been created.

```plpgsql
CREATE OR REPLACE FUNCTION trg_after_token_inserted()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    NOTIFY token_inserted;
    RETURN NULL;
END;
$$;

CREATE TRIGGER after_token_inserted
    AFTER INSERT ON tokens
    FOR EACH ROW
    EXECUTE FUNCTION trg_after_token_inserted ();
```

# Let's Try It Out!

To see the triggers in action, we'll walk through a simple end-to-end example. Follow these steps to test the functionality:

---

### Step 1: Create a New Account

Insert a new account into the `accounts` table. This should automatically generate an activation token.

```sql
INSERT INTO accounts (email, login)
	VALUES ('user@example.com', 'user123');
```

**Expected Outcome**:

- A new account with `status = 'provisioned'` is added to `accounts`.
- An activation token is automatically inserted into the `tokens` table, linked to the account.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
SELECT * FROM tokens WHERE account = 1;
```

---

### Step 2: Consume the Activation Token

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

**Expected Outcome**:

- The account's `status` in `accounts` should change to `active`.
- The `activated_at` timestamp should be updated in `accounts`.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
SELECT * FROM tokens WHERE account = 1;
```

---

### Step 3: Suspend the Account

Change the account's status to `suspended` to test the suspension flow.

```sql
UPDATE accounts SET status = 'suspended' WHERE id = 1;
```

**Expected Outcome**:

- The account's `suspended_at` timestamp is updated.
- The `unsuspended_at` field is cleared.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
```

---

### Step 4: Unsuspend the Account

Restore the account's status to `active`.

```sql
UPDATE accounts SET status = 'active' WHERE id = 1;
```

**Expected Outcome**:

- The account's `unsuspended_at` timestamp is updated.
- The `suspended_at` field is cleared.

Verify:

```sql
SELECT * FROM accounts WHERE id = 1;
```

---

### Step 5: Observe Notifications

Listen for token creation notifications using `LISTEN`.

In one session:

```sql
LISTEN token_inserted;
```

In another session, create a new token:

```sql
INSERT INTO tokens (account, action)
	VALUES (1, 'activation');
```

**Expected Outcome**:

- The `LISTEN` session should immediately display a notification like:
  ```
  Asynchronous notification "token_inserted" with payload "" received.
  ```

# Roll-Your-Own Email Queue

Before wrapping up, we'll create a mechanism to retrieve pending user actions and establish a query to manage their progression through a database-driven queue for processing.

We use the `jobs` table to maintain a cursor for advancing through pending tokens. This table tracks the last processed token (`last_seq`) for each job type, allowing us to pick up where we left off.

```sql
CREATE TYPE job_type AS ENUM (
    'user_action_queue'
);

CREATE TABLE jobs (
    job_type job_type PRIMARY KEY,
    last_seq BIGINT
);
```

Initialize the user action queue:

```sql
INSERT INTO
jobs
    (last_seq, job_type)
VALUES
    (0, 'user_action_queue');
```

## Retrieving Pending Tokens

The following query fetches all relevant tokens and account details, ensuring that only valid, unexpired, and unprocessed tokens are retrieved, and that the associated accounts are in the correct status for the intended action:

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
    ON
        t.id > jobs.last_seq
        AND t.expires_at > EXTRACT(EPOCH FROM NOW())
        AND t.consumed_at IS NULL
        AND t.action IN ('activation', 'password_recovery')
    JOIN accounts a
    ON
        a.id = t.account
        AND ((t.action = 'activation'
                AND a.status = 'provisioned')
            OR (t.action = 'password_recovery'
                AND a.status = 'active'))
WHERE
    jobs.job_type = 'user_action_queue'
```

**Joins & Filters:**

- `jobs`: Filtering by `job_type = 'user_action_queue'`
- `tokens`: Joining on `tokens.id > jobs.last_seq` with conditions:
    - `t.expires_at` (not expired)
    - `t.consumed_at` is NULL (unused)
    - `t.action` is either `activation` or `password_recovery`
- `accounts`: Joining on `accounts.id = tokens.account` with conditions:
    - If `t.action = 'activation'`, the account must be `provisioned`
    - If `t.action = 'password_recovery'`, the account must be `active`


## Advancing the User Action Queue Cursor

Finally, we integrate the pending actions query into a CTE that simultaneously updates the job cursor and retrieves data for the mailer.

```sql
WITH token_data AS (
    -- Query logic here
)
UPDATE
    jobs
SET
    last_seq = (SELECT MAX(id) FROM token_data)
WHERE
    job_type = 'user_action_queue'
    AND EXISTS (SELECT 1 FROM token_data)
RETURNING
    (SELECT json_agg(token_data) FROM token_data);
```

By combining the data retrieval and cursor update in a single transaction, we ensure that either both actions succeed or neither does.

- The `UPDATE` statement advances the `last_seq` in the `jobs` table to the maximum id of the tokens we just retrieved. This ensures that in subsequent runs, these tokens won't be processed again.
- The `WHERE` clause includes an `EXISTS` condition to ensure that we only update the `last_seq` if there are tokens to process.
- The `RETURNING` clause outputs the token data as a JSON array, which can be consumed by the mailer system to send out emails.

## Index Recommendations

To optimize query performance, the following composite indexes are recommended:

```sql
CREATE INDEX accounts_id_status_idx ON accounts (id, status);

CREATE INDEX tokens_id_expires_consumed_action_idx ON tokens
    (id, expires_at, consumed_at, action);
```

Indexing Strategy:

- **Equality Conditions First**: Since columns used in equality conditions (`=` or `IN`) are typically the most selective, they should come first.
- **Range Conditions Next**: Columns used in range conditions (`>`, `<`, `BETWEEN`) should follow.

# Limitations and Considerations

While this system is robust for small- to medium-scale use cases, it's important to acknowledge its limitations:

## Polling-Based Processing

The notification system relies on periodic polling of the database (`tokens.id > last_seq`) to retrieve new tasks. This approach can be inefficient when there are no new tokens to process, as it consumes resources without any real work.

_We'll address this further in the second part._

## Single-Consumer Queue

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

#### Without Locking:
   - Consumer A reads `jobs.last_seq = 100`.
   - Consumer B also reads `jobs.last_seq = 100` before A updates it.
   - Both consumers select tokens where `t.id > 100`, potentially processing the same tokens.

#### With `FOR UPDATE`:
   - Consumer A locks the `jobs` record and reads `last_seq = 100`.
   - Consumer B tries to read `jobs.last_seq` but is blocked until Consumer A's transaction completes.
   - Consumer A updates `last_seq` to, say, `150` and releases the lock.
   - Consumer B then reads the updated `last_seq = 150`, processing the next set of tokens.

Alternatively, if the concern is to handle **multiple consumers** efficiently, you can consider **eliminating the `jobs` table altogether**. Instead, add a new field, such as `processed_at`, to the `tokens` table. This field will indicate when a token has been processed. By updating `processed_at` during token retrieval, you can use `FOR UPDATE SKIP LOCKED` to support a multi-consumer setup in a safe fashion.

However, if you're certain that only a single consumer runs this query at any given time, I recommend sticking with the `jobs` table as a single point of reference. This approach avoids the need for complex locking mechanisms, and you can further enhance the `jobs` table to keep a history of job executions, parameters, and statuses, which can be valuable for auditing purposes.

> #### When to Switch to a Dedicated Queue?
>
> If there are hundreds of jobs per second, dedicated queues will be more efficient. However, processing hundreds of emails per second also implies significant costs—likely tens of thousands of euros paid to a cloud provider. At that scale, it might be more cost-effective to hire a few engineers to optimize your system and address these challenges directly 🤓

# What's Next?

In Part 2, we'll use Go to integrate batch processing and parallelism into the system, transforming this reactive SQL-driven pipeline into a scalable, production-ready solution.
