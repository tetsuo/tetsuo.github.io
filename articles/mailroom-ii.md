---
title: User Lifecycle Management: Part 2 – token collector
cover_title: User Lifecycle Management: Part 2 – token collector
description: See in action how triggers, notifications, and libpq async calls unite for token batching with backpressure
tags: c,mailroom,io,postgres,database
published: 2025-01-10T14:47:00
updated: 2025-01-12T09:14:00
---

> Step two of the trilogy: See in action how triggers, notifications, and libpq async calls unite for token batching with backpressure.

[Previously in this series](/mailroom-i.html), we explored **triggers** and their role in managing a token queue atop PostgreSQL. Although we lightly incorporated **NOTIFY** statements, we haven't fully examined their power yet. In this segment, we'll bring **notification events** into focus and build a **collector** to gather and seamlessly prepare them for downstream processing.

#### Setting Up Your Environment

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

But that's it—your database is ready to go!

#### Inspect the Initial State

Before adding any mock data, let's take a look at the initial state of the `jobs` table:

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

#### Start Listening for Updates

In a separate terminal, connect to the database again:

```sh
psql -d mailroom
```

Then enable listening on the `token_insert` channel:

```sql
LISTEN token_insert;
```

#### Populate with Sample Data

Now, let's insert some dummy data to the `accounts` table. This command will insert 3 records with randomized email and login fields:

```sh
printf "%.0sINSERT INTO accounts (email, login) VALUES ('user' || md5(random()::text) || '@fake.mail', 'user' || substr(md5(random()::text), 1, 20));\n" {1..3} | \
    psql -d mailroom
```

Here's an example of what an inserted `account` record looks like:

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

And here's the corresponding `token` record that was automatically generated via the trigger function:

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

Don't worry if a notification hasn't appeared in the other terminal—`psql` might just need a little nudge (`;`) to display them:

```
mailroom=# LISTEN token_insert;
LISTEN
mailroom=# ;
Asynchronous notification "token_insert" received from server process with PID 5148.
Asynchronous notification "token_insert" received from server process with PID 5148.
Asynchronous notification "token_insert" received from server process with PID 5148.
```

#### Dequeue Pending Jobs

These notifications tell us that it's time to run the query we constructed in [**Part 1**](./mailroom-i.html):

```sql
WITH token_data AS (
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
  ORDER BY id ASC
  LIMIT 10
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

... which accomplishes two things:

1. **Retrieves tokens generated after the `last_seq` along with the corresponding user data**
2. **Updates the `last_seq` value to avoid selecting duplicates later**

In other words, it retrieves _a batch_ and advances the cursor:

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

# Overview

The `collector` bridges the gap between the database and the email sender. Its job is to **buffer and control the flow** of emails by fetching batches of payloads triggered by notification events, then forwarding them to the downstream process responsible for actually sending emails.

Without notifications, we would need to periodically query the database every few seconds to check for pending jobs. While this can be okay for high-traffic scenarios, if token insertions are rare, continuous polling just eats up resources. By listening for database notifications and counting them instead, the `collector` can respond in near real-time, know exactly how many rows to dequeue, and only query when there's actual work to do.

### Staying Within Budget

On the flip side, the limits imposed by our email provider—and, by extension, our budget—become critical constraints to consider. For example, with Amazon SES charging **$0.10 per 1,000 emails**, a monthly budget of **$100** translates to:

- **1,000,000 emails per month,**
- **33,333 emails per day,**
- **1,389 emails per hour,**
- **23 emails per minute, and**
- **0.38 emails per second.**

At this rate, we would need to buffer for approximately **27 seconds** for batches containing **10 destinations** each:

```
10 emails / 0.38 emails per second ≈ 26.32 seconds
```

... which is based on the assumption that we are operating at full capacity within the financial budget.

## Pull-based Flow-control

The system does implement a form of **backpressure**. It doesn't do so in a "push-back to the producer" sense that some streaming frameworks (like Kafka) might use, but rather by _pulling_ tokens from the database in controlled batches and only fetching more when the collector is ready. In other words, the `collector` imposes a flow-control mechanism on itself to avoid overwhelming the downstream (email-sending) component.

Here's how it works in practice:

### Batch Limit

> The maximum number of email destinations in a single batch.

The `collector` queries the database for at most **N** tokens at a time (where **N** is the **batch limit**). Even if 500 tokens are waiting in the database, the `collector` will only take, say, 10 at a time. This imposes a hard cap on the throughput of tokens that can leave the database and head downstream.

### Batch Timeout

> The time to wait for accumulating enough notifications to fill a batch.

Instead of hammering the database every millisecond or immediately after a few notifications arrive, the `collector` also waits up to **X** milliseconds before processing tokens (where **X** is the **batch timeout**). If fewer than the batch limit have arrived during that window, the `collector` will still dequeue whatever did arrive—but it won't keep pulling more immediately. In effect, this ensures that surges of tokens are smoothed out over time (i.e., "batched").

#### Example

If you set:

- A batch **timeout** of 30 seconds.
- A **limit** of 10 notifications.

This means:

- If 10 notifications arrive in quick succession, the batch is triggered immediately.
- If fewer than 10 arrive over 30 seconds, the batch is triggered when the timeout ends.

# Implementation

The `collector` is written in C and primarily uses [libpq](https://www.postgresql.org/docs/current/libpq.html). It listens for database notifications, keeps track of how many have arrived, executes the query, and prints the results to stdout.

## Connecting to PostgreSQL

The query from [Part 1](./mailroom-i.html) lives in [`db.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/db.c#L20), along with other DB-related functions. When the collector first connects, it issues a `LISTEN` command on the specified channel and creates the prepared statements for subsequent queries.

[`db.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/db.c#L299)

```c
// Creates a prepared statement to be reused for efficient database queries.
static bool db_prepare_statement(PGconn *conn, const char *stmt_name, const char *query)
{
  PGresult *res = PQprepare(conn, stmt_name, query, 2, NULL);
  if (PQresultStatus(res) != PGRES_COMMAND_OK)
  {
    PQclear(res);
    return false;
  }
  PQclear(res);
  return true;
}

// Executes a LISTEN command on a specified channel to receive database
// notifications in real time.
static bool db_listen(PGconn *conn, const char *channel)
{
  char *escaped_channel = PQescapeIdentifier(conn, channel, strlen(channel));
  if (!escaped_channel)
  {
    return false;
  }

  size_t command_len = strlen("LISTEN ") + strlen(escaped_channel) + 1;
  char listen_command[command_len];
  snprintf(listen_command, command_len, "LISTEN %s", escaped_channel);
  PQfreemem(escaped_channel);

  PGresult *res = PQexec(conn, listen_command);
  if (PQresultStatus(res) != PGRES_COMMAND_OK)
  {
    PQclear(res);
    return false;
  }
  PQclear(res);

  return true;
}

// Establishes a connection to the database, listens for notifications, and
// creates prepared statements.
bool db_connect(PGconn **conn, const char *conninfo, const char *channel)
{
  *conn = PQconnectdb(conninfo);

  return PQstatus(*conn) == CONNECTION_OK &&
         db_listen(*conn, channel) &&
         db_prepare_statement(*conn, POSTGRES_HEALTHCHECK_PREPARED_STMT_NAME, "SELECT 1") &&
         db_prepare_statement(*conn, POSTGRES_DATA_PREPARED_STMT_NAME, token_data);
}
```

## Fetching & Serializing Email Payloads

When notifications arrive, the `collector` executes the query to fetch tokens in batches. Then it writes the results directly to stdout. Processing continues until it has exhausted the queued notifications or an error occurs. Between queries, it sleeps briefly (10ms) to avoid hammering the database.

[`db.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/db.c#L105C1-L224C1)

```c
// Fetches and processes email payloads from the database.
static int _db_dequeue(PGconn *conn, const char *queue, int limit)
{
  static const char *params[2];
  static char limitstr[12];

  PGresult *res = NULL;
  int action_col, email_col, login_col, code_col, secret_col;
  char *action, *email, *login, *code, *secret_text;
  unsigned char *secret = NULL;
  size_t secret_len;
  int nrows;

  static char signature_buffer[SIGNATURE_MAX_INPUT_SIZE];  // Input to sign
  static unsigned char hmac_result[HMAC_RESULT_SIZE];      // HMAC output
  static unsigned char combined_buffer[CONCATENATED_SIZE]; // secret + HMAC
  static char base64_encoded[BASE64_ENCODED_SIZE];         // Base64-encoded output

  size_t hmac_len = 0;

  snprintf(limitstr, sizeof(limitstr), "%d", limit);
  params[0] = queue;
  params[1] = limitstr;

  res = PQexecPrepared(conn, POSTGRES_DATA_PREPARED_STMT_NAME, 2, params, NULL, NULL, 0);
  if (PQresultStatus(res) != PGRES_TUPLES_OK)
  {
    log_printf("ERROR: query execution failed: %s", PQerrorMessage(conn));
    PQclear(res);
    return -1;
  }

  nrows = PQntuples(res);
  if (nrows == 0)
  {
    PQclear(res);
    return 0;
  }

  action_col = PQfnumber(res, "action");
  email_col = PQfnumber(res, "email");
  login_col = PQfnumber(res, "login");
  code_col = PQfnumber(res, "code");
  secret_col = PQfnumber(res, "secret");

  if (action_col == -1 || email_col == -1 || login_col == -1 ||
      code_col == -1 || secret_col == -1)
  {
    log_printf("FATAL: missing columns in the result set");
    PQclear(res);
    return -2;
  }

  size_t signature_len;

  for (int i = 0; i < nrows; i++)
  {
    action = PQgetvalue(res, i, action_col);
    email = PQgetvalue(res, i, email_col);
    login = PQgetvalue(res, i, login_col);
    code = PQgetvalue(res, i, code_col);
    secret_text = PQgetvalue(res, i, secret_col);

    secret = PQunescapeBytea((unsigned char *)secret_text, &secret_len);
    if (!secret || secret_len != 32)
    {
      log_printf("WARN: skipping row; PQunescapeBytea failed or invalid secret length");
      continue;
    }

    if (strcmp(action, "activation") == 0)
    {
      printf("%d", 1);
    }
    else if (strcmp(action, "password_recovery") == 0)
    {
      printf("%d", 2);
    }
    else
    {
      printf("%d", 0);
    }

    printf(",%s,%s,", email, login);

    signature_len = construct_signature_data(signature_buffer, action, secret, code);

    hmac_len = HMAC_RESULT_SIZE;
    if (!hmac_sign(signature_buffer, signature_len, hmac_result, &hmac_len))
    {
      log_printf("WARN: skipping row; HMAC signing failed");
      PQfreemem(secret);
      continue;
    }

    memcpy(combined_buffer, secret, 32);
    memcpy(combined_buffer + 32, hmac_result, hmac_len);

    if (!base64_urlencode(base64_encoded, sizeof(base64_encoded), combined_buffer, 32 + hmac_len))
    {
      log_printf("WARN: skipping row; base64 encoding failed");
      PQfreemem(secret);
      continue;
    }

    printf("%s,%s", base64_encoded, code);

    PQfreemem(secret);

    if (i < nrows - 1)
    {
      printf(",");
    }
  }

  printf("\n");
  fflush(stdout);
  PQclear(res);

  return nrows;
}

// Ensure no more than the batch limit is dequeued.
int db_dequeue(PGconn *conn, const char *queue, int remaining, int max_chunk_size)
{
  int result = 0;
  int chunk_size = 0;
  int total = 0;
  while (remaining > 0)
  {
    chunk_size = remaining > max_chunk_size ? max_chunk_size : remaining;
    result = _db_dequeue(conn, queue, chunk_size);
    if (result < 0)
    {
      return result;
    }
    total += result;
    remaining -= chunk_size;
    sleep_microseconds(10000); // 10ms
  }
  return total;
}
```

### Signing & Verifying Tokens

One key transformation during dequeue operation involves signing the token's `secret` with HMAC-SHA256 and encoding it in Base64 URL-safe format.

The encoded output contains:

- A path name (e.g., `/activate` or `/recover`)
- The original secret (and code, in the case of recovery)
- And the resulting cryptographic signature

[`db.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/db.c#L80C1-L103C2)

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

This step ensures authenticity checks can happen on the frontend without needing an immediate database call. If you'd like to see how the backend verifies these secrets, there is a [`verifyHmac.js`](https://github.com/tetsuo/mailroom/blob/master/etc/verifyHmac.js) script in the repo for reference.

> **Remember to handle expired tokens.** One method is to include the `expires_at` value so you can check validity without a DB lookup. But if tokens remain valid for 15 minutes, a more thorough approach is to **cache consumed tokens** until they naturally expire, preventing reuse during their validity period.

> **Also, remember to rotate your signing key often.**

## Putting It All Together

#### Environment Variables

In [`main.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/main.c), you'll see references to environment variables like `MAILROOM_BATCH_TIMEOUT`, `MAILROOM_BATCH_LIMIT`, and `MAILROOM_SECRET_KEY` (a 64-character hex string). Consult the [`README`](https://github.com/tetsuo/mailroom/blob/master/README.md#environment-variables) file for the full list.

### The Loop

At a high level, the main loop repeatedly:

- Dequeues and processes ready batches
- Checks for new notifications
- Waits on `select()` for either database activity or a timeout
- Performs periodic health checks
- Reconnects to the database if needed

When the batch limit is reached or the timeout occurs, the `collector` executes the dequeue query. If it detects a broken connection, it attempts to reconnect and resumes once stable.

Here's the pseudo-code representation:

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

And here's the actual implementation:

[`main.c`](https://github.com/tetsuo/mailroom/blob/master/collector/src/main.c#L203)

```c
int result;

PGconn *conn = NULL;

fd_set active_fds, read_fds;
int sock;

struct timeval tv;
int seen = 0;

PGnotify *notify = NULL;
int rc = 0;

long start = get_current_time_ms();
long now, elapsed, remaining_ms;

long last_healthcheck = start;

int ready = -1;

while (running)
{
  if (ready < 0)
  {
    if (conn)
    {
      PQfinish(conn);
    }

    if (!db_connect(&conn, conninfo, channel_name))
    {
      log_printf("ERROR: connection failed: %s", PQerrorMessage(conn));
      return exit_code(conn, EXIT_FAILURE);
    }

    log_printf("connected");

    while (running && (result = db_dequeue(conn, queue_name, batch_limit, batch_limit)) == batch_limit)
      ;

    if (result < 0)
    {
      return exit_code(conn, EXIT_FAILURE);
    }

    FD_ZERO(&active_fds);
    sock = PQsocket(conn);
    FD_SET(sock, &active_fds);

    seen = 0;
    ready = 0;
    last_healthcheck = get_current_time_ms();

    continue;
  }
  else if (ready > 0)
  {
    result = db_dequeue(conn, queue_name, seen, batch_limit);
    if (result == -2)
    {
      return exit_code(conn, EXIT_FAILURE);
    }
    else if (result == -1)
    {
      log_printf("WARN: forcing reconnect...");
      ready = -1;
      continue;
    }
    else if (result != seen)
    {
      log_printf("WARN: expected %d items to be processed, got %d", seen, result);
    }

    seen = 0;
    ready = 0;
    last_healthcheck = get_current_time_ms();
  }

  // Process any pending notifications before select()
  while (running && (notify = PQnotifies(conn)) != NULL)
  {
    PQfreemem(notify);
    if (seen == 0)
    {
      log_printf("NOTIFY called; waking up");
      start = get_current_time_ms(); // Received first notification; reset timer
    }
    seen++;
    PQconsumeInput(conn);
  }

  if (seen >= batch_limit)
  {
    log_printf("processing %d rows... (max reached)", seen);

    ready = 1;
    continue; // Skip select() and process immediately
  }

  now = get_current_time_ms();
  elapsed = now - start;
  remaining_ms = timeout_ms - elapsed;

  if (remaining_ms < 0)
  {
    remaining_ms = 0;
  }

  tv.tv_sec = remaining_ms / 1000;
  tv.tv_usec = (remaining_ms % 1000) * 1000;

  read_fds = active_fds;

  rc = select(sock + 1, &read_fds, NULL, NULL, &tv);

  if (rc < 0)
  {
    if (errno == EINTR)
    {
      if (!running)
      {
        break;
      }
      log_printf("WARN: select interrupted by signal");
      continue;
    }
    log_printf("ERROR: select failed: %s (socket=%d)", strerror(errno), sock);
    break;
  }
  else if (rc == 0)
  {                                // Timeout occurred;
    start = get_current_time_ms(); // Reset the timer

    if (seen > 0)
    {
      log_printf("processing %d rows... (timeout)", seen);

      ready = 1;
      continue;
    }

    if ((sock = PQsocket(conn)) < 0)
    {
      log_printf("WARN: socket closed; %s", PQerrorMessage(conn));
      ready = -1;
      continue;
    }

    if (now - last_healthcheck >= healthcheck_ms)
    {
      if (!db_healthcheck(conn))
      {
        ready = -1;
        continue;
      }
      else
      {
        last_healthcheck = start;
      }
    }
  }

  if (!FD_ISSET(sock, &read_fds))
  {
    continue;
  }

  do
  {
    if (!PQconsumeInput(conn))
    {
      log_printf("WARN: error consuming input: %s", PQerrorMessage(conn));
      if (PQstatus(conn) != CONNECTION_OK)
      {
        ready = -1;
        break;
      }
    }
  } while (running && PQisBusy(conn));
}
```

#### `select()` in a Nutshell

The [`select()`](https://man7.org/linux/man-pages/man2/select.2.html) system call is central to how the program operates. It's a UNIX mechanism that monitors file descriptors (like sockets) to determine if they're ready for I/O operations (e.g., reading or writing).

In this code, `select()` is used to:

- Monitor the socket for new notifications
- Enforce a timeout for batch processing

#### **`PQconsumeInput` and `PQnotifies`**

After `select()` signals that data is ready, the `collector` calls `PQconsumeInput`, which reads data into libpq's internal buffers. It then calls `PQnotifies` to retrieve any pending notifications and increment the counter.

> Read more about [libpq's async API](https://www.postgresql.org/docs/current/libpq-async.html).

# Compile & Run

To compile, verify that you have `openssl@3` and `libpq@5` installed, then use the provided `Makefile`.

### Run the Collector

Use the following command to build and run the `collector` with example configuration variables:

```sh
make && \
  MAILROOM_BATCH_LIMIT=3 \
  MAILROOM_BATCH_TIMEOUT=5000 \
  MAILROOM_DATABASE_URL="dbname=mailroom" \
  MAILROOM_SECRET_KEY="cafebabecafebabecafebabecafebabecafebabecafebabecafebabecafebabe" \
  ./collector
```

Once configured and started, it will log its activity:

```
2024/04/20 13:37:00 [PG] configured; channel=token_insert queue=mailroom limit=3 timeout=5000ms healthcheck-interval=270000ms
2024/04/20 13:37:00 [PG] connecting to host=/tmp port=5432 dbname=mailroom user=ogu sslmode=disable
2024/04/20 13:37:00 [PG] connected
```

---

### Insert Accounts and Observe Batching

In another terminal, insert 5 accounts:

```sh
printf "%.0sINSERT INTO accounts (email, login) VALUES ('user' || md5(random()::text) || '@fake.mail', 'user' || substr(md5(random()::text), 1, 20));\n" {1..5} | \
    psql -d mailroom
```

You'll observe the `collector` immediately process the first batch of three items. After a 5-second delay (as defined by the `MAILROOM_BATCH_TIMEOUT`), it processes the remaining two in a second batch:

```
2024/04/20 13:37:00 [PG] NOTIFY called; waking up
2024/04/20 13:37:00 [PG] processing 3 rows... (max reached)
1,userb183abb7a25d04027061e6b8d8d8e7fa@fake.mail,userb0bf075b82b892f53d97,gVRNesi-opSvs3ntPfr9DzSn_JwbOD04VVIurQSCOFzzd3BOM3WBDL3SOtDjMxKLd6csSn8_p9hemXHIUxIjPg,78092,1,user43b01ba9686c886473e526429dd2c672@fake.mail,userf420078dba4fd5a91de2,--DTy5LsbDeLP_AweXIPSjL3_avQMT5cH_bRxPy1uxQLVhXKaw7Oxd7NYkcJ6MZmnnqWqTcBPHA5z7bqunXEAA,25778,1,user46f81dfd34b91a1904ac4524193575aa@fake.mail,user6d91baab56d2823b326d,ryooWewe3OTxIGF1Gjl5Vvl8BsXoqWVbCAt1t6J--_KX1SM4DbyCes4yn75OWVe60G4MMZdv4byRh1wy-Clvxw,78202
2024/04/20 13:37:00 [PG] NOTIFY called; waking up
2024/04/20 13:37:05 [PG] processing 2 rows... (timeout)
1,user12d2722e1c07b0a531ea69ae125d4697@fake.mail,user853ae29eefc5d44a6bc6,4pmew2o2EOAZBDHWvJBcixJftpRCb8uyXZhzN12EOcrLBmzc4ic9avwd9dla09pIiKIoqW5iIwMfoXLEM3_LGw,38806,1,user9497d0e033019fcf3198eecb053ba40e@fake.mail,userfcde338dba96cc419613,ANLMa-1y37VLCDqK0wnfEFhUVzHsWpaNGV2ttI8m3o6_lbbYOKmp3hP7Q8H8ZQRNMPAj4xsSqC26nesfVZLgzQ,89897
```

---

### Testing Reconnect Behavior

To simulate a dropped connection, open another terminal, connect to `mailroom` via `psql`, and run:

```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE
  datname = 'mailroom'
  AND pid <> pg_backend_pid();
```

After the connection is killed, `select()` wakes up, causing `PQconsumeInput()` to fail with an error. The collector logs a reconnect attempt, and once reconnected, it resumes processing without losing track of queued tokens during the downtime.

```
2024/04/20 13:37:42 [PG] WARN: error consuming input: server closed the connection unexpectedly
        This probably means the server terminated abnormally
        before or while processing the request.

2024/04/20 13:37:42 [PG] connecting to host=/tmp port=5432 dbname=mailroom user=ogu sslmode=disable
2024/04/20 13:37:42 [PG] connected
```

# Next

In the upcoming **Part 3**, we'll build the **sender** component to handle email delivery.
