# TESTING.md

# Testing Instructions — queueCTL

This document explains how to test the core functionality of the **queueCTL** job queue system.

---
### Demonstration video

https://drive.google.com/file/d/1BDtfBttOlJePJ-2eKspyytyHWlDZDAb0/view?usp=sharing


---

## 1. Setup

1. Clone the repo and navigate to the project directory:

```bash
git clone https://github.com/abhigyanverma111/queueCTL.git
cd queueCTL
```

2. (Optional) Create a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/macOS
```

3. Install the package:

```bash
pip install .
```

4. Verify CLI works:

```bash
queuectl --help
```

---

## 2. Enqueue a Job

### Command:

```bash
queuectl enqueue '{"command":"echo Hello World"}'
```

### Expected Output:

```
Job 'job1' enqueued successfully.
```

---

## 3. Start Worker(s)

### Command:

```bash
queuectl worker start --count 1
```

### Expected Output:

```
Starting 1 worker(s)...
Workers started. Press Ctrl+C to stop.
task job1: Hello World
```

- `task job1: Hello World` should appear once.

---

## 4. Job Status

### Command:

```bash
queuectl status
```

### Expected Output:

```
Job Status Summary:
  pending    0
  running    0
  completed  1
  failed     0
  dead       0
Active workers: 1
```

---

## 5. Enqueue a Job with Delay (sleep)

### Command:

```bash
queuectl enqueue '{"command":"sleep 2"}'
queuectl worker start --count 1
```

### Expected Output:

```
task job2 on sleep for 2 seconds
```

---

## 6. Failed Job and DLQ

### Command:

```bash
queuectl enqueue '{"command":"invalid_command"}'
queuectl worker start --count 1
```

### Expected Output:

```
task job3 encountered exception "unknown command encountered"
 remaining attempts = 2
```

- After `max_retries`, job moves to DLQ:

```
task job3 is dead, moving to dead-letter-queue
```

---

## 7. Dead Letter Queue (DLQ)

### List DLQ Jobs:

```bash
queuectl dlq list
```

### Expected Output:

```
Dead Letter Queue:
  job3       | invalid_command
```

### Retry a DLQ Job:

```bash
queuectl dlq retry job3
```

### Expected Output:

```
Retried job 'job3' successfully.
```

---

## 8. List Jobs by State

```bash
queuectl list --state pending
```

- Shows all jobs currently in the specified state:

```
Jobs in state 'pending':
  job3       | pending     | invalid_command
```

---

## 9. Configuration

### Set Config Value:

```bash
queuectl config set max_retries 5
```

Expected Output:

```
Config 'max_retries' set to 5
```

### Show Config:

```bash
queuectl config show
```

Expected Output:

```
  Current Config:
  max_retries: 5
  backoff_base: 2
```

---

## 10. Stop Workers

Currently, stop workers is handled by **Ctrl+C** in the same terminal.

- Press **Ctrl+C** while workers are running.
- Expected Output:

```
Stop signal received. Stopping workers...
All workers stopped gracefully.
```
