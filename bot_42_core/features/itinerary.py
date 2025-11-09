# ============================================================
# Itinerary + Scheduler for 42
# ============================================================

from datetime import datetime, timedelta
import logging


# ------------------------------------------------------------
# Task Definition
# ------------------------------------------------------------
class Task:
    def __init__(self, name: str, start_time: datetime, duration_minutes: int,
                 action, permissions: dict):
        self.name = name
        self.start_time = start_time
        self.end_time = start_time + timedelta(minutes=duration_minutes)
        self.action = action
        self.permissions = permissions

    def run(self):
        """Execute the task's action."""
        logging.info(f"Running task: {self.name}")
        try:
            self.action(self.permissions)
            logging.info(f"Task completed: {self.name}")
        except Exception as e:
            logging.error(f"Task failed: {self.name} — {e}")


# ------------------------------------------------------------
# Task Runner
# ------------------------------------------------------------
class TaskRunner:
    def __init__(self):
        self.tasks = []

    def add(self, task: Task):
        """Add a task to the queue."""
        self.tasks.append(task)

    def run_due(self):
        """Run all tasks that are due or past due."""
        now = datetime.now()
        count = 0
        for t in self.tasks:
            if t.start_time <= now:
                t.run()
                count += 1
        return count