import sqlite3
from datetime import datetime
import threading
import time
from classes.Task import Task

class TaskQueue:
    _instance = None

    #this class has to commit to the sql only
    conn = sqlite3.connect('queuectl.db', check_same_thread=False)

    cursor = conn.cursor()

    lock = threading.Lock()


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_list (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT CHECK(state IN ('pending', 'running', 'completed', 'failed', 'dead')) NOT NULL,
            attempts INTEGER DEFAULT 0,
            max_retries INTEGER NOT NULL,
            next_attempt_at TEXT ,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    conn.commit()

    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def instance(cls):
        return cls()
    
    def getNewTask(self):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, command, max_retries, attempts, next_attempt_at FROM task_list
                WHERE state = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if not row:
                return None
            
            task_id, command, max_retries, attempts, next_attempt_at = row
            cursor.execute('''
                UPDATE task_list
                SET state = 'running', updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), task_id))
            self.conn.commit()
        
        task = Task(task_id, command, max_retries)
        task.attempts = attempts                  
        task.next_attempt_at = next_attempt_at    
        return task

    
    def recieve_task(self, task):

        with self.lock:
            self.cursor.execute(
                """
                INSERT INTO task_list (id, command, state, attempts, max_retries, next_attempt_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    attempts = excluded.attempts,
                    updated_at = excluded.updated_at
                """,
                (
                    task.id,
                    task.command,
                    task.state,
                    task.attempts,
                    task.max_retries,
                    task.next_attempt_at,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ),
            )

            self.conn.commit()
    
    def _retry_monitor(self):
        while True:
            time.sleep(1)
            with self.lock:
                now = datetime.now().isoformat()
                self.cursor.execute('''
                        SELECT id FROM task_list
                        WHERE state = 'failed'
                        AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                    ''', (now,))
                rows = self.cursor.fetchall()
                if rows:
                    ids = [r[0] for r in rows]
                    self.cursor.executemany('''
                            UPDATE task_list
                            SET state = 'pending', updated_at = ?
                            WHERE id = ?
                        ''', [(datetime.now().isoformat(), tid) for tid in ids])
                    self.conn.commit()
                    print(f"Retried {len(rows)} failed task(s).")

    
    
    def _start_retry_monitor(self):
        thread = threading.Thread(target=self._retry_monitor, daemon=True)
        thread.start()
    

    

        



    
TaskQueue._instance = TaskQueue()


