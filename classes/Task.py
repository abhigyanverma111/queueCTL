import datetime
import time
import json
import os

def load_config():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../config.json"))
    with open(config_path, "r") as f:
        return json.load(f)



class Task:

    def __init__(self, id, command, max_retries):
        self.id = id
        self.command = command
        self.state = "pending"
        self.max_retries = max_retries
        self.attempts = 0
        self.next_attempt_at = None
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()

    

    def run(self):
        if self.state != "pending":
            return "invalid task encountered"
        

        try:
            words = self.command.strip().split()

            if not words:
                raise ValueError("Empty command")
            

            if words[0] == 'echo':
                line = " ".join(words[1:]) if len(words) > 1 else ""
                print(f"task {self.id}:", line)
            elif words[0] == 'sleep':

                if len(words) != 2:
                    raise ValueError("invalid commmand encountered")
                
                seconds = int(words[1])
                print(f"task {self.id} on sleep for {seconds} seconds")
                time.sleep(seconds)
            else:
                raise ValueError("unknown command encountered")
            
            self.state = "completed"

        except ValueError as e:
            self.attempts+=1

            if self.attempts >= self.max_retries:
                self.state = "dead"

            else:
                self.state = "failed"

            
            print(f"task {self.id} encountered exception \"{e}\"\n remaining attempts = {self.max_retries - self.attempts}")

            if self.attempts >= self.max_retries:
                print(f"task {self.id} is dead, moving to dead-letter-queue")

        finally:
            self.updated_at = datetime.datetime.now()
            if self.state == "failed":
                CONFIG = load_config()
                base = CONFIG["backoff_base"]
                self.next_attempt_at = datetime.datetime.now() + datetime.timedelta(seconds=(base ** self.attempts))

        
        return self.state
            



            
            


    


        
    

    

# if __name__ == "__main__":
#     task = Task(id="job1", command="sleep 2", max_retries=3)

