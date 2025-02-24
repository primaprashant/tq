import os
import sqlite3
import tempfile
from unittest import mock

import pytest
from click.testing import CliRunner
from rich.console import Console

from tq import cli, db


# Mock Rich console to capture output without styling
@pytest.fixture
def mock_console(monkeypatch):
    console = Console(force_terminal=False)
    monkeypatch.setattr("tq.cli.console", console)
    return console


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_db():
    """Create a temporary database for testing."""
    temp_db_file = tempfile.NamedTemporaryFile(delete=False)
    temp_db_path = temp_db_file.name
    temp_db_file.close()

    with mock.patch.dict(os.environ, {"TQ_DB_PATH": temp_db_path}):
        db.init_db()
        yield

    os.unlink(temp_db_path)


def test_init_db_creates_tables(mock_db):
    """Test that init_db creates the expected tables."""
    with sqlite3.connect(db.get_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        assert cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_queue_completed'")
        assert cursor.fetchone() is not None


def test_cli_no_args_empty_db(runner, mock_db, mock_console):
    """Test CLI with no arguments on an empty database."""
    result = runner.invoke(cli.cli)
    assert result.exit_code == 0
    # Check for the panel content without styling
    assert "No active queues found" in result.output.strip()


def test_cli_no_args_with_tasks(runner, mock_db, mock_console):
    """Test CLI with no arguments when tasks exist."""
    db.add_task("Task 1", "queue1")
    db.add_task("Task 2", "queue1")
    db.add_task("Task 3", "queue2")

    result = runner.invoke(cli.cli)
    assert result.exit_code == 0
    # Check for table content without styling
    assert "Active Queues" in result.output
    assert "queue1" in result.output
    assert "2 tasks" in result.output
    assert "queue2" in result.output
    assert "1 task" in result.output


def test_add_task(runner, mock_db, mock_console):
    """Test adding a task to a queue."""
    result = runner.invoke(cli.cli, ["add", "Test task"])
    assert result.exit_code == 0
    # Check for styled text content
    assert "Test task" in result.output
    assert "default" in result.output

    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Test task"


def test_add_task_custom_queue(runner, mock_db, mock_console):
    """Test adding a task to a custom queue."""
    result = runner.invoke(cli.cli, ["add", "Test task", "custom"])
    assert result.exit_code == 0
    assert "Test task" in result.output
    assert "custom" in result.output

    tasks = db.list_tasks("custom")
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Test task"


def test_add_duplicate_task(runner, mock_db, mock_console):
    """Test adding a duplicate task to a queue."""
    runner.invoke(cli.cli, ["add", "Test task"])
    result = runner.invoke(cli.cli, ["add", "Test task"])
    assert result.exit_code == 0
    assert "Task already exists" in result.output

    tasks = db.list_tasks()
    assert len(tasks) == 1


def test_add_task_with_invalid_queue_name(runner, mock_db, mock_console):
    """Test adding a task with a numeric queue name."""
    result = runner.invoke(cli.cli, ["add", "Test task", "123"])
    assert result.exit_code == 1
    assert "Error" in result.output
    assert "cannot be numeric only" in result.output


def test_list_empty_queue(runner, mock_db, mock_console):
    """Test listing tasks from an empty queue."""
    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0
    assert "No tasks in 'default' queue" in result.output


def test_list_tasks(runner, mock_db, mock_console):
    """Test listing tasks from a queue with items."""
    db.add_task("Task 1")
    db.add_task("Task 2")

    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0

    # Check individual components instead of the exact formatted string
    assert "Tasks in" in result.output
    assert "'default'" in result.output
    assert "Queue" in result.output
    assert "Task 1" in result.output
    assert "Task 2" in result.output
    # Verify table structure
    assert "ID" in result.output
    assert "Task" in result.output

    # Verify table boundaries are present
    assert "╭" in result.output  # top left corner
    assert "╰" in result.output  # bottom left corner


def test_pop_empty_queue(runner, mock_db, mock_console):
    """Test popping from an empty queue."""
    result = runner.invoke(cli.cli, ["pop"])
    assert result.exit_code == 0
    assert "No tasks in 'default' queue" in result.output


def test_pop_task(runner, mock_db, mock_console):
    """Test popping the most recent task from a queue."""
    db.add_task("Task 1")
    db.add_task("Task 2")

    result = runner.invoke(cli.cli, ["pop"])
    assert result.exit_code == 0
    assert "Task 2" in result.output

    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Task 1"


def test_delete_task_by_id(runner, mock_db, mock_console):
    """Test deleting a task by ID."""
    db.add_task("Test task")
    tasks = db.list_tasks()
    task_id = tasks[0]["id"]

    result = runner.invoke(cli.cli, ["delete", str(task_id)])
    assert result.exit_code == 0
    assert str(task_id) in result.output
    assert "Test task" in result.output

    tasks = db.list_tasks()
    assert len(tasks) == 0


def test_delete_queue(runner, mock_db, mock_console):
    """Test deleting an entire queue."""
    db.add_task("Task 1", "test_queue")
    db.add_task("Task 2", "test_queue")

    result = runner.invoke(cli.cli, ["delete", "test_queue"])
    assert result.exit_code == 0
    assert "test_queue" in result.output
    assert "Task 1" in result.output
    assert "Task 2" in result.output

    tasks = db.list_tasks("test_queue")
    assert len(tasks) == 0


def test_unicode_characters(runner, mock_db, mock_console):
    """Test handling of Unicode characters in task and queue names."""
    unicode_task = "こんにちは世界"
    unicode_queue = "日本語"

    result = runner.invoke(cli.cli, ["add", unicode_task, unicode_queue])
    assert result.exit_code == 0

    result = runner.invoke(cli.cli, ["list", unicode_queue])
    assert result.exit_code == 0
    assert unicode_task in result.output

    result = runner.invoke(cli.cli, ["pop", unicode_queue])
    assert result.exit_code == 0
    assert unicode_task in result.output    


def test_special_characters_in_task(runner, mock_db, mock_console):
    """Test handling of special characters in task text."""
    special_task = "task with 'quotes', \"double quotes\", and → arrows"

    result = runner.invoke(cli.cli, ["add", special_task])
    assert result.exit_code == 0

    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0
    assert special_task in result.output


def test_error_handling(runner, mock_db, mock_console):
    """Test general error handling."""
    with mock.patch("tq.cli.cli", side_effect=Exception("Test error")):
        with mock.patch("sys.exit") as mock_exit:
            cli.main()
            mock_exit.assert_called_once_with(1)
