import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from tqu import db
from tqu.exceptions import (
    ConfigError,
    DatabaseError,
    EmptyQueueError,
    TaskAlreadyExistsError,
    TaskError,
    TaskNotFoundError,
)


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.sqlite"
    with patch.dict(os.environ, {"TQU_DB_PATH": str(db_path)}):
        db.init_db()
        yield db_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_db(temp_db):
    db.add_task("Task 1", "default")
    db.add_task("Task 2", "default")
    db.add_task("Project task", "project")
    db.add_task("Another project task", "project")
    return temp_db


def test_get_db_path_default():
    with patch.dict(os.environ, {}, clear=True):
        assert str(db.get_db_path()) == str(Path("~/.tqu.sqlite").expanduser())


def test_get_db_path_custom():
    custom_path = "/tmp/custom.sqlite"
    with patch.dict(os.environ, {"TQU_DB_PATH": custom_path}):
        assert str(db.get_db_path()) == custom_path


def test_get_db_path_error():
    with patch("pathlib.Path.expanduser", side_effect=Exception("Access denied")):
        with pytest.raises(ConfigError, match="Failed to determine database path"):
            db.get_db_path()


def test_init_db(temp_db):
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_queue_completed'")
        assert cursor.fetchone() is not None


def test_init_db_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to initialize database"):
            db.init_db()


def test_add_task(temp_db):
    assert db.add_task("Test task")
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_text FROM tasks WHERE queue_name = 'default'")
        result = cursor.fetchone()
    assert result and result[0] == "Test task"


def test_add_task_to_custom_queue(temp_db):
    assert db.add_task("Custom queue task", "custom")
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_text FROM tasks WHERE queue_name = 'custom'")
        result = cursor.fetchone()
    assert result and result[0] == "Custom queue task"


def test_add_duplicate_task(temp_db):
    db.add_task("Duplicate task")
    with pytest.raises(TaskAlreadyExistsError, match="Task already exists"):
        db.add_task("Duplicate task")


def test_add_task_numeric_queue():
    with pytest.raises(TaskError, match="cannot be numeric only"):
        db.add_task("Task", "123")


def test_add_task_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Failed to connect")):
        with pytest.raises(DatabaseError, match="Failed to add task"):
            db.add_task("Task with DB error")


def test_list_tasks_empty(temp_db):
    assert db.list_tasks() == []


def test_list_tasks(populated_db):
    tasks = db.list_tasks()
    assert len(tasks) == 2
    assert tasks[0]["task_text"] == "Task 1"
    assert tasks[1]["task_text"] == "Task 2"


def test_list_tasks_custom_queue(populated_db):
    tasks = db.list_tasks("project")
    assert len(tasks) == 2
    assert tasks[0]["task_text"] == "Project task"
    assert tasks[1]["task_text"] == "Another project task"


def test_list_tasks_nonexistent_queue(temp_db):
    assert db.list_tasks("nonexistent") == []


def test_list_tasks_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to list tasks"):
            db.list_tasks()


def test_pop_last_empty(temp_db):
    with pytest.raises(EmptyQueueError, match="No tasks in 'default' queue"):
        db.pop_last()


def test_pop_last(populated_db):
    task = db.pop_last()
    assert task is not None and task["task_text"] == "Task 2"
    tasks = db.list_tasks()
    assert len(tasks) == 1 and tasks[0]["task_text"] == "Task 1"


def test_pop_last_custom_queue(populated_db):
    task = db.pop_last("project")
    assert task is not None and task["task_text"] == "Another project task"
    tasks = db.list_tasks("project")
    assert len(tasks) == 1 and tasks[0]["task_text"] == "Project task"


def test_pop_last_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to pop last task"):
            db.pop_last()


def test_pop_first_empty(temp_db):
    with pytest.raises(EmptyQueueError, match="No tasks in 'default' queue"):
        db.pop_first()


def test_pop_first(populated_db):
    task = db.pop_first()
    assert task is not None and task["task_text"] == "Task 1"
    tasks = db.list_tasks()
    assert len(tasks) == 1 and tasks[0]["task_text"] == "Task 2"


def test_pop_first_custom_queue(populated_db):
    task = db.pop_first("project")
    assert task is not None and task["task_text"] == "Project task"
    tasks = db.list_tasks("project")
    assert len(tasks) == 1 and tasks[0]["task_text"] == "Another project task"


def test_pop_first_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to pop first task"):
            db.pop_first()


def test_delete_task_nonexistent(temp_db):
    with pytest.raises(TaskNotFoundError, match="Task with ID 999 not found"):
        db.delete_task(999)


def test_delete_task(populated_db):
    with sqlite3.connect(populated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE task_text = 'Task 1'")
        task_id = cursor.fetchone()[0]
    result = db.delete_task(task_id)
    assert result is not None and result[0] == "default" and result[1] == "Task 1"
    tasks = db.list_tasks()
    assert len(tasks) == 1 and tasks[0]["task_text"] == "Task 2"


def test_delete_task_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to delete task"):
            db.delete_task(1)


def test_delete_queue_empty(temp_db):
    with pytest.raises(EmptyQueueError, match="No tasks in 'default' queue"):
        db.delete_queue()


def test_delete_queue(populated_db):
    tasks = db.delete_queue()
    assert len(tasks) == 2
    assert not db.list_tasks()


def test_delete_custom_queue(populated_db):
    tasks = db.delete_queue("project")
    assert len(tasks) == 2
    default_tasks = db.list_tasks("default")
    assert len(default_tasks) == 2


def test_delete_queue_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to delete queue"):
            db.delete_queue()


def test_list_queues_empty(temp_db):
    assert db.list_queues() == []


def test_list_queues(populated_db):
    queues = db.list_queues()
    queue_dict = {name: count for name, count in queues}
    assert "default" in queue_dict and "project" in queue_dict
    assert queue_dict["default"] == 2 and queue_dict["project"] == 2


def test_list_queues_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to list queues"):
            db.list_queues()


def test_list_queues_after_deletion(populated_db):
    try:
        db.delete_queue("project")
    except EmptyQueueError:
        pass  # We're not testing this here
    queues = db.list_queues()
    assert len(queues) == 1 and queues[0][0] == "default"


def test_find_by_id_or_name_with_name(temp_db):
    is_id, task_id = db.find_by_id_or_name("not_an_id")
    assert not is_id and task_id is None


def test_find_by_id_or_name_with_nonexistent_id(temp_db):
    is_id, task_id = db.find_by_id_or_name("999")
    assert is_id and task_id is None


def test_find_by_id_or_name_with_valid_id(populated_db):
    with sqlite3.connect(populated_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks LIMIT 1")
        existing_id = cursor.fetchone()[0]
    is_id, task_id = db.find_by_id_or_name(str(existing_id))
    assert is_id and task_id == existing_id


def test_find_by_id_or_name_database_error():
    with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
        with pytest.raises(DatabaseError, match="Failed to find task"):
            db.find_by_id_or_name("1")


def test_completed_tasks_are_excluded(temp_db):
    db.add_task("Task to complete")
    assert len(db.list_tasks()) == 1

    try:
        db.pop_first()
    except EmptyQueueError:
        pytest.fail("Should not raise EmptyQueueError")

    assert len(db.list_tasks()) == 0
    assert db.add_task("Task to complete")


def test_task_timestamps(temp_db):
    start = int(time.time())
    db.add_task("Timestamped task")
    with sqlite3.connect(temp_db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        row = dict(cursor.execute("SELECT created_at, updated_at, completed_at FROM tasks").fetchone())
    assert row["created_at"] >= start
    assert row["updated_at"] >= start
    assert row["completed_at"] is None


def test_unicode_support(temp_db):
    text = "测试任务 ✓ öäü 😊"
    db.add_task(text)
    tasks = db.list_tasks()
    assert tasks and tasks[0]["task_text"] == text


def test_concurrent_operations(temp_db):
    for i in range(100):
        db.add_task(f"Task {i}")
    assert len(db.list_tasks()) == 100

    popped = 0
    for _ in range(50):
        try:
            db.pop_first()
            popped += 1
        except EmptyQueueError:
            break

    assert popped == 50
    assert len(db.list_tasks()) == 50
