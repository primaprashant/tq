import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from tqu.exceptions import (
    ConfigError,
    DatabaseError,
    EmptyQueueError,
    TaskAlreadyExistsError,
    TaskError,
    TaskNotFoundError,
)


def get_db_path() -> str:
    try:
        path = os.environ.get("TQU_DB_PATH", Path("~/.tqu.sqlite").expanduser())
        return str(path)
    except Exception as e:
        raise ConfigError(f"Failed to determine database path: {str(e)}")


def init_db() -> None:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_name TEXT NOT NULL,
                    task_text TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    completed_at INTEGER
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_completed
                ON tasks(queue_name, completed_at)
            """)
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to initialize database: {str(e)}", e)


def add_task(task_text: str, queue_name: str = "default") -> bool:
    if queue_name.isdigit():
        raise TaskError(f"Queue name '{queue_name}' cannot be numeric only")

    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM tasks
                WHERE queue_name = ? AND task_text = ? AND completed_at IS NULL
            """,
                (queue_name, task_text),
            )
            if cursor.fetchone():
                raise TaskAlreadyExistsError(task_text, queue_name)

            ts = int(time.time())
            cursor.execute(
                """
                INSERT INTO tasks (queue_name, task_text, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, NULL)
            """,
                (queue_name, task_text, ts, ts),
            )
        return True
    except TaskAlreadyExistsError:
        # Re-raise the specific exception to be caught by the caller
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to add task: {str(e)}", e)


def list_tasks(queue_name: str = "default") -> List[Dict[str, Any]]:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, task_text, created_at
                FROM tasks
                WHERE queue_name = ? AND completed_at IS NULL
                ORDER BY created_at ASC
            """,
                (queue_name,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to list tasks: {str(e)}", e)


def pop_last(queue_name: str = "default") -> Dict[str, Any]:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, task_text
                FROM tasks
                WHERE queue_name = ? AND completed_at IS NULL
                ORDER BY id DESC
                LIMIT 1
            """,
                (queue_name,),
            )
            row = cursor.fetchone()
            if not row:
                raise EmptyQueueError(queue_name)

            task_id = row["id"]
            ts = int(time.time())
            cursor.execute(
                """
                UPDATE tasks
                SET completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (ts, ts, task_id),
            )
            return dict(row)
    except EmptyQueueError:
        # Re-raise to be caught by the caller
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to pop last task: {str(e)}", e)


def pop_first(queue_name: str = "default") -> Dict[str, Any]:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, task_text
                FROM tasks
                WHERE queue_name = ? AND completed_at IS NULL
                ORDER BY created_at ASC
                LIMIT 1
            """,
                (queue_name,),
            )
            row = cursor.fetchone()
            if not row:
                raise EmptyQueueError(queue_name)

            task_id = row["id"]
            ts = int(time.time())
            cursor.execute(
                """
                UPDATE tasks
                SET completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (ts, ts, task_id),
            )
            return dict(row)
    except EmptyQueueError:
        # Re-raise to be caught by the caller
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to pop first task: {str(e)}", e)


def delete_task(task_id: int) -> Optional[Tuple[str, str]]:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT queue_name, task_text
                FROM tasks
                WHERE id = ? AND completed_at IS NULL
            """,
                (task_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise TaskNotFoundError(task_id)

            ts = int(time.time())
            cursor.execute(
                """
                UPDATE tasks
                SET completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (ts, ts, task_id),
            )
            return row
    except TaskNotFoundError:
        # Re-raise to be caught by the caller
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to delete task: {str(e)}", e)


def delete_queue(queue_name: str = "default") -> List[Dict[str, Any]]:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, task_text
                FROM tasks
                WHERE queue_name = ? AND completed_at IS NULL
                ORDER BY created_at ASC
            """,
                (queue_name,),
            )
            tasks = [dict(row) for row in cursor.fetchall()]

            if not tasks:
                raise EmptyQueueError(queue_name)

            ts = int(time.time())
            cursor.execute(
                """
                UPDATE tasks
                SET completed_at = ?, updated_at = ?
                WHERE queue_name = ? AND completed_at IS NULL
            """,
                (ts, ts, queue_name),
            )
            return tasks
    except EmptyQueueError:
        # Re-raise to be caught by the caller
        raise
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to delete queue: {str(e)}", e)


def list_queues() -> List[Tuple[str, int]]:
    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT queue_name, COUNT(*) as task_count
                FROM tasks
                WHERE completed_at IS NULL
                GROUP BY queue_name
                ORDER BY queue_name
            """)
            return cursor.fetchall()
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to list queues: {str(e)}", e)


def find_by_id_or_name(id_or_name: Union[str, int]) -> Tuple[bool, Optional[int]]:
    try:
        task_id = int(id_or_name)
    except ValueError:
        return False, None

    try:
        with sqlite3.connect(get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM tasks
                WHERE id = ? AND completed_at IS NULL
            """,
                (task_id,),
            )
            exists = cursor.fetchone() is not None
        return True, task_id if exists else None
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to find task: {str(e)}", e)
