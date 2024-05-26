import os
import signal
import subprocess
import platform
from watchfiles import watch


class Watcher:
    def __init__(self, command):
        self.command = command
        self.process = None

    def run(self):
        print("Current directory:", os.getcwd())
        self.start_process()
        try:
            for changes in watch('.', recursive=True):
                print(f"Changes detected: {changes}")
                self.restart()
        except KeyboardInterrupt:
            self.stop_process()
            print("Shutting down gracefully...")

    def start_process(self):
        print("Starting process...")
        if platform.system() == 'Windows':
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            self.process = subprocess.Popen(
                self.command, shell=True, preexec_fn=os.setsid
            )

    def stop_process(self):
        print("Stopping process...")
        if self.process:
            if platform.system() == 'Windows':
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()

    def restart(self):
        print("File change detected. Restarting process...")
        self.stop_process()
        self.start_process()


if __name__ == "__main__":
    command = "python src/consumer.py"
    watcher = Watcher(command)
    watcher.run()
