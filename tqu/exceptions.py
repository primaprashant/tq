from typing import Any, Optional


class TQUError(Exception):
    """Base exception for all TQU errors."""

    def __init__(self, message: str = "", code: Optional[int] = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class QueueError(TQUError):
    """Errors related to queue operations."""

    pass


class QueueNotFoundError(QueueError):
    """Raised when a queue is not found."""

    def __init__(self, queue_name: str) -> None:
        super().__init__(f"Queue '{queue_name}' not found.")


class EmptyQueueError(QueueError):
    """Raised when trying to perform operations on an empty queue."""

    def __init__(self, queue_name: str) -> None:
        super().__init__(f"No tasks in '{queue_name}' queue.")


class TaskError(TQUError):
    """Errors related to task operations."""

    pass


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""

    def __init__(self, task_id: Any) -> None:
        super().__init__(f"Task with ID {task_id} not found or already completed.")


class TaskAlreadyExistsError(TaskError):
    """Raised when trying to add a task that already exists."""

    def __init__(self, task_text: str, queue_name: str) -> None:
        super().__init__(f"Task already exists in '{queue_name}' queue: {task_text}")


class DatabaseError(TQUError):
    """Errors related to database operations."""

    def __init__(self, message: str = "Database error occurred", original_error: Optional[Exception] = None) -> None:
        self.original_error = original_error
        super().__init__(message)


class ConfigError(TQUError):
    """Errors related to configuration."""

    pass
