# queueCTL

### a simple CLI-based background job queue system

## Features

- Enqueue tasks with simple commands (`sleep`, `echo`)
- Worker threads to process tasks concurrently
- Automatic retries with exponential backoff
- Dead-letter queue (DLQ) for failed tasks
- CLI to manage tasks, workers, and configuration
- SQLite-backed storage (`queuectl.db`)

## Setup Instructions

1.  clone github repository (or download .zip file)

    ```bash
    git clone https://github.com/abhigyanverma111/queueCTL
    cd queuectl
    ```

2.  Install in editable mode:

    ```bash
    pip install -e .
    ```

    - This makes the queuectl command available globally (make sure your Python Scripts folder is in PATH on Windows).

## Usage

### Enqueue a task

    queuectl enqueue '{"command":"sleep 2"}'
    queuectl enqueue '{"command":"echo Hello World"}'

### Start workers

start a number of workers that work in parallel to deal with the current pending queue

    queuectl worker start --count 2

### Stop Workers

When workers are running, echo command outputs as well as sleep calls will be displayed in the terminal running the app.

To stop all running workers press Ctrl+C

    ^C

### Check Task Status

shows the count of pending, completed and dead tasks

    queuectl status

### List tasks by state

```bash
queuectl list --state pending
queuectl list --state completed
queuectl list --state failed
```

### Dead-Letter-Queue

All tasks that have exhausted their maximum retries are marked as dead and moved to the DLQ

We can list all tasks in DLQ

```bash
queuectl dlq list
```

and using task's id, we can put some tasks back into the pending queue, with their attempts reset to 0

```bash
queuectl dlq retry <job_id>
```

### Config

Show current configuration

```bash
queuectl config show
```

Or set configuration values from the CLI itself
(all time values are in seconds)

```bash
queuectl config set max_retries 5
queuectl config set backoff_base 2
```

## Architecture Overview

This document describes the internal architecture of **queueCTL**, including how jobs are managed, persisted, and processed by workers.

---

## Job Lifecycle

1. **Enqueue**

   - A task is added to the queue via the CLI (`queuectl enqueue`).
   - Task properties:
     - `id` – unique identifier (UUID)
     - `command` – string command to execute (`sleep`, `echo`, etc.)
     - `state` – one of `pending`, `running`, `completed`, `failed`, `dead`
     - `attempts` – number of attempts made
     - `max_retries` – maximum allowed retries
     - `next_attempt_at` – timestamp for the next retry
     - `created_at` and `updated_at` – timestamps

2. **Pending**

   - All new tasks start in `pending` state.
   - Workers pick tasks from the `pending` pool in FIFO order.

3. **Running**

   - When a worker picks a task, its state is immediately updated to `running`.
   - This prevents multiple workers from picking the same task.

4. **Completion**

   - On successful execution of the command, the task state is set to `completed`.

5. **Failure & Retry**

   - If a command fails (invalid or unknown command):
     - `attempts` is incremented.
     - If attempts < max_retries → `failed` state, `next_attempt_at` is scheduled using exponential backoff.
     - If attempts ≥ max_retries → task is moved to `dead` state (DLQ).

6. **Dead-Letter Queue**
   - Tasks in the `dead` state cannot be automatically retried.
   - Manual retry is possible via CLI (`queuectl dlq retry <job_id>`).

---

## Data Persistence

- **SQLite Database (`queuectl.db`)**

  - Single table `task_list` stores all tasks.
  - Columns: `id`, `command`, `state`, `attempts`, `max_retries`, `next_attempt_at`, `created_at`, `updated_at`.
  - Ensures persistence even if the system or worker crashes.

- **Concurrency Handling**

  - A `threading.Lock` ensures only one thread can access or modify the database at a time.
  - Prevents race conditions when multiple workers update task states.

- **Retry Monitor**
  - A background thread periodically checks for `failed` tasks whose `next_attempt_at` has passed.
  - Moves them back to `pending` for re-processing.

---

## Worker Logic

1. **Initialization**

   - Each worker is a thread running independently.
   - Workers continuously poll the queue for `pending` tasks.

2. **Task Execution**

   - Worker picks a `pending` task and sets it to `running`.
   - Executes the task command:
     - `sleep <seconds>` – pauses for the specified duration
     - `echo <message>` – prints the message to terminal
   - On success → marks task as `completed`.
   - On failure → handles retry or DLQ logic.

3. **Concurrency**

   - Multiple workers can run concurrently.
   - The lock ensures database integrity and prevents duplicate task execution.

4. **Graceful Shutdown**
   - Workers respond to a stop signal (`Ctrl+C`).
   - Finish current task before terminating to prevent partially processed tasks.

---

## Summary

- Tasks flow through **pending → running → completed/failed → dead (optional retry)**.
- **SQLite + Lock** combination ensures durability and thread safety.
- Retry mechanism with exponential backoff provides resilience for transient failures.
- CLI provides full control over task lifecycle and worker management.
