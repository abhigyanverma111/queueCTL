import argparse
import json
import os
import threading
import datetime
from time import sleep
import uuid


from classes.TaskQueue import TaskQueue
from classes.Task import Task
from classes.Worker import Worker

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# active worker threads
active_workers = []
stop_signal = threading.Event()

queue = TaskQueue.instance()
queue._start_retry_monitor()



# config helper functions
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"max_retries": 3}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


# command handlers
def handle_enqueue(args):
    try:
        job_data = json.loads(args.job_json)
        job_id = str(uuid.uuid4())
        command = job_data["command"]

        config = load_config()
        queue = TaskQueue.instance()

        task = Task(
            id=job_id,
            command=command,
            max_retries=config.get("max_retries", 3),
        )

        queue.recieve_task(task)
        print(f"Job '{job_id}' enqueued successfully.")
    except Exception as e:
        print(f"Failed to enqueue job: {e}")


def handle_worker_start(args):
    count = args.count
    print(f"Starting {count} worker(s)")

    def worker_thread():
        worker = Worker()
        worker.run(stop_signal)

    for _ in range(count):
        t = threading.Thread(target=worker_thread)
        active_workers.append(t)
        t.start()

    print("Workers started. Press Ctrl+C to stop.")
    try:
        while not stop_signal.is_set():
            sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stop signal received. Stopping workers...")
        stop_signal.set()
        for t in active_workers:
            t.join()
        print("✅ All workers stopped gracefully.")


def handle_worker_stop(args):
    print(" Stopping all workers gracefully...")
    stop_signal.set()


def handle_status(args):
    queue = TaskQueue.instance()
    cursor = queue.conn.cursor()
    cursor.execute("""
        SELECT state, COUNT(id) FROM task_list GROUP BY state
    """)
    rows = cursor.fetchall()
    print(" Job Status Summary:")
    for state, count in rows:
        print(f"  {state:<10} {count}")
    print(f" Active workers: {len(active_workers)}")


def handle_list(args):
    queue = TaskQueue.instance()
    cursor = queue.conn.cursor()
    cursor.execute("SELECT id, command, state FROM task_list WHERE state = ?", (args.state,))
    rows = cursor.fetchall()
    if not rows:
        print(f"No jobs found in state '{args.state}'.")
        return
    print(f"Jobs in state '{args.state}':")
    for job_id, command, state in rows:
        print(f"  {job_id:<10} | {state:<10} | {command}")


def handle_dlq(args):
    queue = TaskQueue.instance()
    cursor = queue.conn.cursor()

    if args.action == "list":
        cursor.execute("SELECT id, command FROM task_list WHERE state = 'dead'")
        rows = cursor.fetchall()
        if not rows:
            print("No jobs in DLQ.")
        else:
            print("Dead Letter Queue:")
            for job_id, command in rows:
                print(f"  {job_id:<10} | {command}")

    elif args.action == "retry":
        job_id = args.job_id
        cursor.execute("SELECT id, command, max_retries FROM task_list WHERE id = ? AND state = 'dead'", (job_id,))
        row = cursor.fetchone()
        if not row:
            print(f"No DLQ job found with id '{job_id}'.")
            return
        task_id, command, max_retries = row
        task = Task(task_id, command, max_retries)
        queue.recieve_task(task)
        print(f"Retried job '{job_id}' successfully.")


def handle_config(args):
    config = load_config()
    if args.action == "set":
        key, value = args.key, args.value
        if key not in config:
            print(f"⚠️ Unknown config key '{key}'. Adding new one.")
        try:
            value = int(value)
        except:
            pass
        config[key] = value
        save_config(config)
        print(f"✅ Config '{key}' set to {value}")
    else:
        print("⚙️ Current Config:")
        for k, v in config.items():
            print(f"  {k}: {v}")




# CLI Argument Parser

def main():
    parser = argparse.ArgumentParser(prog="queuectl", description="Queue Control CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Enqueue
    enqueue_parser = subparsers.add_parser("enqueue", help="Add a new job to the queue")
    enqueue_parser.add_argument("job_json", help="Job JSON string, e.g. '{\"command\":\"sleep 2\"}'")
    enqueue_parser.set_defaults(func=handle_enqueue)

    # Worker
    worker_parser = subparsers.add_parser("worker", help="Manage workers")
    worker_sub = worker_parser.add_subparsers(dest="worker_command")
    start_parser = worker_sub.add_parser("start", help="Start workers")
    start_parser.add_argument("--count", type=int, default=1, help="Number of workers to start")
    start_parser.set_defaults(func=handle_worker_start)
    stop_parser = worker_sub.add_parser("stop", help="Stop workers")
    stop_parser.set_defaults(func=handle_worker_stop)

    # Status
    status_parser = subparsers.add_parser("status", help="Show job and worker status")
    status_parser.set_defaults(func=handle_status)

    # List
    list_parser = subparsers.add_parser("list", help="List jobs by state")
    list_parser.add_argument("--state", required=True, help="Job state to filter (pending, running, etc.)")
    list_parser.set_defaults(func=handle_list)

    # DLQ
    dlq_parser = subparsers.add_parser("dlq", help="View or retry DLQ jobs")
    dlq_parser.add_argument("action", choices=["list", "retry"], help="Action to perform")
    dlq_parser.add_argument("job_id", nargs="?", help="Job ID for retry")
    dlq_parser.set_defaults(func=handle_dlq)

    # Config
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("action", choices=["set", "show"], help="Set or show config")
    config_parser.add_argument("key", nargs="?", help="Config key (for set)")
    config_parser.add_argument("value", nargs="?", help="Config value (for set)")
    config_parser.set_defaults(func=handle_config)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
