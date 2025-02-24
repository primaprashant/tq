import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union


def get_db_path() -> str:
    return os.environ.get("TQ_DB_PATH", os.path.expanduser("~/.tq.sqlite"))


def init_db() -> None:
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


def add_task(task_text: str, queue_name: str = "default") -> bool:
    if task_text in {"pop", "poplast", "popfirst", "delete", "list"}:
        raise ValueError(f"Task text '{task_text}' is reserved")
    if queue_name.isdigit():
        raise ValueError(f"Queue name '{queue_name}' cannot be numeric only")

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
            return False
        ts = int(time.time())
        cursor.execute(
            """
            INSERT INTO tasks (queue_name, task_text, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, NULL)
        """,
            (queue_name, task_text, ts, ts),
        )
    return True


def list_tasks(queue_name: str = "default") -> List[Dict[str, Any]]:
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


def pop_last(queue_name: str = "default") -> Optional[Dict[str, Any]]:
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
        if row:
            ts = int(time.time())
            cursor.execute(
                """
                UPDATE tasks
                SET completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (ts, ts, row["id"]),
            )
            return dict(row)
    return None


def pop_first(queue_name: str = "default") -> Optional[Dict[str, Any]]:
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
        if row:
            ts = int(time.time())
            cursor.execute(
                """
                UPDATE tasks
                SET completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (ts, ts, row["id"]),
            )
            return dict(row)
    return None


def delete_task(task_id: int) -> Optional[Tuple[str, str]]:
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
        if row:
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
    return None


def delete_queue(queue_name: str = "default") -> List[Dict[str, Any]]:
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


def list_queues() -> List[Tuple[str, int]]:
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


def find_by_id_or_name(id_or_name: Union[str, int]) -> Tuple[bool, Optional[int]]:
    try:
        task_id = int(id_or_name)
    except ValueError:
        return False, None

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
