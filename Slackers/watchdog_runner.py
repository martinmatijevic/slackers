import subprocess
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class BotReloader(FileSystemEventHandler):
    def __init__(self, bot_script):
        self.bot_script = bot_script
        self.process = None
        self.start_bot()

    def start_bot(self):
        """Start the bot process."""
        if self.process:
            self.process.terminate()  # Kill the old process

        # Run isort, black, and ruff
        subprocess.run(["python", "-m", "isort", "."], check=True)
        subprocess.run(["python", "-m", "black", "."], check=True)
        subprocess.run(["python", "-m", "ruff", "check", ".", "--fix"], check=True)

        self.process = subprocess.Popen(["python", self.bot_script])

    def on_modified(self, event):
        """Restart bot when an existing Python file is modified."""
        if event.src_path.endswith(".py"):
            print(f"Detected modification in {event.src_path}, restarting bot...")
            self.start_bot()

    def on_created(self, event):
        """Restart bot when a new Python file is added."""
        if event.src_path.endswith(".py"):
            print(f"New Python file detected: {event.src_path}, restarting bot...")
            self.start_bot()


if __name__ == "__main__":
    bot_script = "slackers.py"  # Change this to your bot's filename
    event_handler = BotReloader(bot_script)
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
        event_handler.process.terminate()

    observer.join()
