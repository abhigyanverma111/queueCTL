from classes.TaskQueue import TaskQueue
from threading import Event
from time import sleep

class Worker:
    def __init__(self):
        self.queue = TaskQueue.instance()

    def pick_and_run(self):
        task = self.queue.getNewTask()
        if not task:
            return
        
        return_state = task.run()

        
        self.queue.recieve_task(task)

    def run(self, stop_event):
        while not stop_event.is_set():

            return_status = self.pick_and_run()
            if return_status is None:
                sleep(2)
        



