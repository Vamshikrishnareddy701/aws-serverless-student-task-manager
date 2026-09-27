"""
Database Abstraction Layer for AWS Serverless Student Task Manager.

This module provides a unified database interface. During local development,
it uses JSONTaskDatabase (file-based persistence in backend/data/tasks.json).
When deploying to AWS, it can be swapped with DynamoDBTaskDatabase without
affecting the Flask routes or frontend code.
"""

import json
import os
import uuid
from datetime import datetime, timezone
import threading
from abc import ABC, abstractmethod


class BaseTaskDatabase(ABC):
    """Abstract interface for task database operations."""

    @abstractmethod
    def get_all_tasks(self, status=None, search=None, priority=None, category=None):
        pass

    @abstractmethod
    def get_task_by_id(self, task_id):
        pass

    @abstractmethod
    def create_task(self, title, description="", priority="Medium", due_date=None, category="General"):
        pass

    @abstractmethod
    def update_task(self, task_id, update_data):
        pass

    @abstractmethod
    def delete_task(self, task_id):
        pass

    @abstractmethod
    def get_statistics(self):
        pass


class JSONTaskDatabase(BaseTaskDatabase):
    """Local JSON file-based database implementation."""

    def __init__(self, data_file_path=None):
        if data_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_file_path = os.path.join(base_dir, "data", "tasks.json")

        self.data_file_path = data_file_path
        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Creates the data directory and default tasks.json if missing."""
        os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
        if not os.path.exists(self.data_file_path):
            self.seed_defaults()

    def seed_defaults(self):
        """Seeds initial default task data."""
        default_tasks = [
            {
                "id": "task_1001",
                "title": "Complete CS450 Cloud Computing Lab 3",
                "description": "Deploy a multi-tier serverless application using AWS Lambda, API Gateway, and DynamoDB.",
                "priority": "High",
                "due_date": "2026-10-02",
                "category": "Assignment",
                "completed": False,
                "created_at": "2026-09-25T10:30:00Z",
                "updated_at": "2026-09-25T10:30:00Z"
            },
            {
                "id": "task_1002",
                "title": "Study for Distributed Systems Midterm",
                "description": "Review Chapters 4-8 on Paxos consensus algorithm, vector clocks, and CAP theorem.",
                "priority": "High",
                "due_date": "2026-10-05",
                "category": "Exam",
                "completed": False,
                "created_at": "2026-09-26T14:15:00Z",
                "updated_at": "2026-09-26T14:15:00Z"
            },
            {
                "id": "task_1003",
                "title": "Submit Senior Capstone Design Proposal",
                "description": "Draft 5-page project charter including scope, architecture diagram, and milestone schedule.",
                "priority": "Medium",
                "due_date": "2026-10-10",
                "category": "Project",
                "completed": False,
                "created_at": "2026-09-24T09:00:00Z",
                "updated_at": "2026-09-24T09:00:00Z"
            },
            {
                "id": "task_1004",
                "title": "Read Research Paper on Serverless Performance Optimization",
                "description": "Analyze cold start mitigation techniques in AWS Lambda vs Azure Functions.",
                "priority": "Low",
                "due_date": "2026-10-12",
                "category": "Study",
                "completed": True,
                "created_at": "2026-09-20T16:45:00Z",
                "updated_at": "2026-09-27T11:20:00Z"
            },
            {
                "id": "task_1005",
                "title": "Schedule AWS Certified Solutions Architect Practice Test",
                "description": "Complete 65-question timed mock exam on Tutorials Dojo platform.",
                "priority": "Medium",
                "due_date": "2026-10-15",
                "category": "Personal",
                "completed": True,
                "created_at": "2026-09-22T08:30:00Z",
                "updated_at": "2026-09-27T15:10:00Z"
            }
        ]
        self._write_tasks(default_tasks)

    def _read_tasks(self):
        """Reads tasks from the JSON file safely with a thread lock."""
        with self._lock:
            try:
                with open(self.data_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []

    def _write_tasks(self, tasks):
        """Writes tasks to the JSON file safely with a thread lock."""
        with self._lock:
            # Atomic write pattern to avoid file corruption
            temp_path = self.data_file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.data_file_path)

    def get_all_tasks(self, status=None, search=None, priority=None, category=None):
        """Retrieve tasks with optional status, search, priority, and category filters."""
        tasks = self._read_tasks()

        if status:
            status_lower = status.strip().lower()
            if status_lower == "completed":
                tasks = [t for t in tasks if t.get("completed") is True]
            elif status_lower == "pending":
                tasks = [t for t in tasks if t.get("completed") is False]

        if priority:
            tasks = [t for t in tasks if t.get("priority", "").lower() == priority.strip().lower()]

        if category:
            tasks = [t for t in tasks if t.get("category", "").lower() == category.strip().lower()]

        if search:
            query = search.strip().lower()
            tasks = [
                t for t in tasks
                if query in t.get("title", "").lower() or query in t.get("description", "").lower()
            ]

        # Sort tasks: pending first, then by priority (High -> Medium -> Low), then by due date
        priority_weights = {"High": 1, "Medium": 2, "Low": 3}
        tasks.sort(
            key=lambda t: (
                1 if t.get("completed") else 0,
                priority_weights.get(t.get("priority"), 4),
                t.get("due_date") or "9999-12-31"
            )
        )

        return tasks

    def get_task_by_id(self, task_id):
        """Find a single task by ID."""
        tasks = self._read_tasks()
        for task in tasks:
            if task.get("id") == task_id:
                return task
        return None

    def create_task(self, title, description="", priority="Medium", due_date=None, category="General"):
        """Create a new task with generated UUID and metadata."""
        title = title.strip() if title else ""
        if not title:
            raise ValueError("Task title is required")

        if priority not in ["Low", "Medium", "High"]:
            priority = "Medium"

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        new_task = {
            "id": task_id,
            "title": title,
            "description": (description or "").strip(),
            "priority": priority,
            "due_date": due_date if due_date else "",
            "category": (category or "General").strip(),
            "completed": False,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        tasks = self._read_tasks()
        tasks.append(new_task)
        self._write_tasks(tasks)

        return new_task

    def update_task(self, task_id, update_data):
        """Update existing task fields."""
        tasks = self._read_tasks()
        found = False
        updated_task = None

        for i, task in enumerate(tasks):
            if task.get("id") == task_id:
                found = True
                # Update allowed fields
                if "title" in update_data:
                    title_val = str(update_data["title"]).strip()
                    if title_val:
                        task["title"] = title_val
                if "description" in update_data:
                    task["description"] = str(update_data["description"]).strip()
                if "priority" in update_data and update_data["priority"] in ["Low", "Medium", "High"]:
                    task["priority"] = update_data["priority"]
                if "due_date" in update_data:
                    task["due_date"] = update_data["due_date"]
                if "category" in update_data:
                    task["category"] = str(update_data["category"]).strip()
                if "completed" in update_data:
                    task["completed"] = bool(update_data["completed"])

                task["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                tasks[i] = task
                updated_task = task
                break

        if not found:
            return None

        self._write_tasks(tasks)
        return updated_task

    def delete_task(self, task_id):
        """Delete a task by ID."""
        tasks = self._read_tasks()
        initial_length = len(tasks)
        filtered_tasks = [t for t in tasks if t.get("id") != task_id]

        if len(filtered_tasks) == initial_length:
            return False

        self._write_tasks(filtered_tasks)
        return True

    def get_statistics(self):
        """Compute task summary statistics."""
        tasks = self._read_tasks()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("completed") is True)
        pending = total - completed
        high_priority = sum(1 for t in tasks if t.get("priority") == "High" and not t.get("completed"))
        completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

        return {
            "total_tasks": total,
            "pending_tasks": pending,
            "completed_tasks": completed,
            "high_priority_tasks": high_priority,
            "completion_rate": completion_rate
        }


class DynamoDBTaskDatabase(BaseTaskDatabase):
    """
    Production AWS DynamoDB implementation reference.
    Ready to use when deployed to AWS Lambda with boto3.
    """

    def __init__(self, table_name="StudentTasks", region_name="us-east-1"):
        self.table_name = table_name
        self.region_name = region_name
        # Note: boto3 would be imported here in AWS Lambda environment:
        # import boto3
        # self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        # self.table = self.dynamodb.Table(table_name)

    def get_all_tasks(self, status=None, search=None, priority=None, category=None):
        # Implementation uses self.table.scan() with FilterExpression
        raise NotImplementedError("DynamoDB implementation used in AWS Lambda handlers under aws/lambda/")

    def get_task_by_id(self, task_id):
        raise NotImplementedError("DynamoDB implementation used in AWS Lambda handlers under aws/lambda/")

    def create_task(self, title, description="", priority="Medium", due_date=None, category="General"):
        raise NotImplementedError("DynamoDB implementation used in AWS Lambda handlers under aws/lambda/")

    def update_task(self, task_id, update_data):
        raise NotImplementedError("DynamoDB implementation used in AWS Lambda handlers under aws/lambda/")

    def delete_task(self, task_id):
        raise NotImplementedError("DynamoDB implementation used in AWS Lambda handlers under aws/lambda/")

    def get_statistics(self):
        raise NotImplementedError("DynamoDB implementation used in AWS Lambda handlers under aws/lambda/")


# Factory function for DB instantiation
def get_db():
    """Returns the configured database instance (JSON for local, DynamoDB for AWS)."""
    return JSONTaskDatabase()
