import os
import sqlite3
import tempfile
from unittest import mock
import pytest
from click.testing import CliRunner

from tq import cli, db


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_db():
    """Create a temporary database for testing."""
    # Create a temporary file for the test database
    temp_db_file = tempfile.NamedTemporaryFile(delete=False)
    temp_db_path = temp_db_file.name
    temp_db_file.close()
    
    # Set the environment variable to use our test database
    with mock.patch.dict(os.environ, {"TQ_DB_PATH": temp_db_path}):
        # Initialize the test database
        db.init_db()
        yield
    
    # Clean up the temporary file
    os.unlink(temp_db_path)


def test_init_db_creates_tables(mock_db):
    """Test that init_db creates the expected tables."""
    # Connect to the database and check if the tables exist
    with sqlite3.connect(db.get_db_path()) as conn:
        cursor = conn.cursor()
        # Check if tasks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        assert cursor.fetchone() is not None
        # Check if index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_queue_completed'")
        assert cursor.fetchone() is not None


def test_cli_no_args_empty_db(runner, mock_db):
    """Test CLI with no arguments on an empty database."""
    result = runner.invoke(cli.cli)
    assert result.exit_code == 0
    assert "No active queues found." in result.output


def test_cli_no_args_with_tasks(runner, mock_db):
    """Test CLI with no arguments when tasks exist."""
    # Add tasks to different queues
    db.add_task("Task 1", "queue1")
    db.add_task("Task 2", "queue1")
    db.add_task("Task 3", "queue2")
    
    result = runner.invoke(cli.cli)
    assert result.exit_code == 0
    assert "Active queues:" in result.output
    assert "queue1: 2 tasks" in result.output
    assert "queue2: 1 task" in result.output


def test_add_task(runner, mock_db):
    """Test adding a task to a queue."""
    result = runner.invoke(cli.cli, ["add", "Test task"])
    assert result.exit_code == 0
    assert "Added task to 'default' queue: Test task" in result.output
    
    # Verify the task was added to the database
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Test task"


def test_add_task_custom_queue(runner, mock_db):
    """Test adding a task to a custom queue."""
    result = runner.invoke(cli.cli, ["add", "Test task", "custom"])
    assert result.exit_code == 0
    assert "Added task to 'custom' queue: Test task" in result.output
    
    # Verify the task was added to the custom queue
    tasks = db.list_tasks("custom")
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Test task"


def test_add_duplicate_task(runner, mock_db):
    """Test adding a duplicate task to a queue."""
    # Add the first task
    runner.invoke(cli.cli, ["add", "Test task"])
    
    # Try to add the same task again
    result = runner.invoke(cli.cli, ["add", "Test task"])
    assert result.exit_code == 0
    assert "Task already exists" in result.output
    
    # Verify only one task exists
    tasks = db.list_tasks()
    assert len(tasks) == 1


def test_add_task_with_invalid_queue_name(runner, mock_db):
    """Test adding a task with a numeric queue name."""
    result = runner.invoke(cli.cli, ["add", "Test task", "123"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "cannot be numeric only" in result.output


def test_add_reserved_task_name(runner, mock_db):
    """Test adding a task with a reserved name."""
    result = runner.invoke(cli.cli, ["add", "pop"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "is reserved" in result.output


def test_list_empty_queue(runner, mock_db):
    """Test listing tasks from an empty queue."""
    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0
    assert "No tasks in 'default' queue." in result.output


def test_list_tasks(runner, mock_db):
    """Test listing tasks from a queue with items."""
    # Add tasks
    db.add_task("Task 1")
    db.add_task("Task 2")
    
    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0
    assert "Tasks in 'default' queue:" in result.output
    assert "Task 1" in result.output
    assert "Task 2" in result.output


def test_list_custom_queue(runner, mock_db):
    """Test listing tasks from a custom queue."""
    # Add task to custom queue
    db.add_task("Custom task", "custom")
    
    result = runner.invoke(cli.cli, ["list", "custom"])
    assert result.exit_code == 0
    assert "Tasks in 'custom' queue:" in result.output
    assert "Custom task" in result.output


def test_pop_empty_queue(runner, mock_db):
    """Test popping from an empty queue."""
    result = runner.invoke(cli.cli, ["pop"])
    assert result.exit_code == 0
    assert "No tasks in 'default' queue." in result.output


def test_pop_task(runner, mock_db):
    """Test popping the most recent task from a queue."""
    # Add tasks
    db.add_task("Task 1")
    db.add_task("Task 2")
    
    result = runner.invoke(cli.cli, ["pop"])
    assert result.exit_code == 0
    assert "Removed from 'default' queue: Task 2" in result.output
    
    # Verify Task 2 was removed
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Task 1"


def test_poplast_task(runner, mock_db):
    """Test using the poplast alias."""
    # Add tasks
    db.add_task("Task 1")
    db.add_task("Task 2")
    
    result = runner.invoke(cli.cli, ["poplast"])
    assert result.exit_code == 0
    assert "Removed from 'default' queue: Task 2" in result.output
    
    # Verify Task 2 was removed
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Task 1"


def test_popfirst_task(runner, mock_db):
    """Test popping the oldest task from a queue."""
    # Add tasks
    db.add_task("Task 1")
    db.add_task("Task 2")
    
    result = runner.invoke(cli.cli, ["popfirst"])
    assert result.exit_code == 0
    assert "Removed from 'default' queue: Task 1" in result.output
    
    # Verify Task 1 was removed
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_text"] == "Task 2"


def test_delete_task_by_id(runner, mock_db):
    """Test deleting a task by ID."""
    # Add a task and get its ID
    db.add_task("Test task")
    tasks = db.list_tasks()
    task_id = tasks[0]["id"]
    
    result = runner.invoke(cli.cli, ["delete", str(task_id)])
    assert result.exit_code == 0
    assert f"Deleted task [{task_id}]" in result.output
    assert "Test task" in result.output
    
    # Verify the task was deleted
    tasks = db.list_tasks()
    assert len(tasks) == 0


def test_delete_nonexistent_task_id(runner, mock_db):
    """Test deleting a nonexistent task ID."""
    result = runner.invoke(cli.cli, ["delete", "999"])
    assert result.exit_code == 0
    assert "not found or already completed" in result.output


def test_delete_queue(runner, mock_db):
    """Test deleting an entire queue."""
    # Add tasks
    db.add_task("Task 1", "test_queue")
    db.add_task("Task 2", "test_queue")
    
    result = runner.invoke(cli.cli, ["delete", "test_queue"])
    assert result.exit_code == 0
    assert "Deleted 'test_queue' queue with 2 tasks:" in result.output
    assert "Task 1" in result.output
    assert "Task 2" in result.output
    
    # Verify the queue is empty
    tasks = db.list_tasks("test_queue")
    assert len(tasks) == 0


def test_delete_empty_queue(runner, mock_db):
    """Test deleting an empty queue."""
    result = runner.invoke(cli.cli, ["delete", "nonexistent"])
    assert result.exit_code == 0
    assert "No tasks in 'nonexistent' queue." in result.output


def test_delete_default_queue(runner, mock_db):
    """Test deleting the default queue."""
    # Add tasks to default queue
    db.add_task("Task 1")
    db.add_task("Task 2")
    
    result = runner.invoke(cli.cli, ["delete"])
    assert result.exit_code == 0
    assert "Deleted 'default' queue with 2 tasks:" in result.output
    
    # Verify the default queue is empty
    tasks = db.list_tasks()
    assert len(tasks) == 0


def test_unicode_characters(runner, mock_db):
    """Test handling of Unicode characters in task and queue names."""
    # Add tasks with Unicode characters
    unicode_task = "こんにちは世界"
    unicode_queue = "日本語"
    
    # Add task with Unicode text to Unicode queue
    result = runner.invoke(cli.cli, ["add", unicode_task, unicode_queue])
    assert result.exit_code == 0
    
    # List the Unicode queue
    result = runner.invoke(cli.cli, ["list", unicode_queue])
    assert result.exit_code == 0
    assert unicode_task in result.output
    
    # Pop from Unicode queue
    result = runner.invoke(cli.cli, ["pop", unicode_queue])
    assert result.exit_code == 0
    assert unicode_task in result.output


def test_special_characters_in_task(runner, mock_db):
    """Test handling of special characters in task text."""
    special_task = "task with 'quotes', \"double quotes\", and → arrows"
    
    # Add task with special characters
    result = runner.invoke(cli.cli, ["add", special_task])
    assert result.exit_code == 0
    
    # List tasks
    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0
    assert special_task in result.output


def test_error_handling(runner, mock_db):
    """Test general error handling."""
    # Mock a database error
    with mock.patch('tq.cli.cli', side_effect=Exception("Test error")):
        # Test that main() properly catches and handles exceptions
        with mock.patch('sys.exit') as mock_exit:
            with mock.patch('click.echo') as mock_echo:
                cli.main()
                # Verify sys.exit was called with code 1
                mock_exit.assert_called_once_with(1)
                # Verify the error message was echoed
                mock_echo.assert_any_call("Error: Test error", err=True)
