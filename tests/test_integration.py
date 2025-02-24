import os
import subprocess
import tempfile
import shlex
import pytest


@pytest.fixture
def test_env():
    """Create a test environment with a dedicated database file."""
    # Create a temporary directory for our test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a database file path in the temp directory
        db_path = os.path.join(temp_dir, "test.sqlite")
        
        # Create an environment dict with our test DB path
        env = os.environ.copy()
        env["TQ_DB_PATH"] = db_path
        
        yield env


def run_command(cmd, env=None):
    """Run a shell command and return its output and exit code."""
    process = subprocess.run(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=isinstance(cmd, str)
    )
    return process.stdout, process.stderr, process.returncode


def test_add_and_list_task(test_env):
    """Test adding a task and then listing it."""
    # Add a task
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "add", "test task", "work"],
        env=test_env
    )
    assert exit_code == 0
    assert "Added task to 'work' queue: test task" in stdout
    
    # List tasks in the work queue
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "list", "work"],
        env=test_env
    )
    assert exit_code == 0
    assert "Tasks in 'work' queue:" in stdout
    assert "test task" in stdout


def test_add_and_pop_task(test_env):
    """Test adding a task and then popping it."""
    # Add a task
    run_command(
        ["python", "-m", "tq", "add", "task to pop", "temp"],
        env=test_env
    )
    
    # Pop the task
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "pop", "temp"],
        env=test_env
    )
    assert exit_code == 0
    assert "Removed from 'temp' queue: task to pop" in stdout
    
    # List should show empty queue
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "list", "temp"],
        env=test_env
    )
    assert exit_code == 0
    assert "No tasks in 'temp' queue." in stdout


def test_add_and_delete_task_by_id(test_env):
    """Test adding a task and then deleting it by ID."""
    # Add a task
    run_command(
        ["python", "-m", "tq", "add", "task for deletion"],
        env=test_env
    )
    
    # List to get the task ID
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "list"],
        env=test_env
    )
    # Extract task ID from output - assumes format like "  [1] task for deletion"
    task_id = stdout.split("[")[1].split("]")[0]
    
    # Delete the task by ID
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "delete", task_id],
        env=test_env
    )
    assert exit_code == 0
    assert f"Deleted task [{task_id}]" in stdout
    assert "task for deletion" in stdout


def test_add_and_popfirst_task(test_env):
    """Test adding multiple tasks and then popping the first one."""
    # Add two tasks
    run_command(
        ["python", "-m", "tq", "add", "first task", "fifo"],
        env=test_env
    )
    run_command(
        ["python", "-m", "tq", "add", "second task", "fifo"],
        env=test_env
    )
    
    # Pop the first task (oldest)
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "popfirst", "fifo"],
        env=test_env
    )
    assert exit_code == 0
    assert "Removed from 'fifo' queue: first task" in stdout


def test_delete_queue(test_env):
    """Test adding tasks to a queue and then deleting the entire queue."""
    # Add multiple tasks
    run_command(
        ["python", "-m", "tq", "add", "task 1", "project"],
        env=test_env
    )
    run_command(
        ["python", "-m", "tq", "add", "task 2", "project"],
        env=test_env
    )
    
    # Delete the queue
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "delete", "project"],
        env=test_env
    )
    assert exit_code == 0
    assert "Deleted 'project' queue with 2 tasks:" in stdout
    assert "task 1" in stdout
    assert "task 2" in stdout


def test_list_queues(test_env):
    """Test that the base command lists all queues with tasks."""
    # Add tasks to multiple queues
    run_command(
        ["python", "-m", "tq", "add", "default task"],
        env=test_env
    )
    run_command(
        ["python", "-m", "tq", "add", "work task", "work"],
        env=test_env
    )
    
    # Run tq with no arguments to list queues
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq"],
        env=test_env
    )
    assert exit_code == 0
    assert "Active queues:" in stdout
    assert "default: 1 task" in stdout
    assert "work: 1 task" in stdout


def test_error_on_numeric_queue(test_env):
    """Test error when using a numeric queue name."""
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "add", "numeric queue task", "123"],
        env=test_env
    )
    assert exit_code != 0
    assert "cannot be numeric only" in stderr


def test_error_on_reserved_task_name(test_env):
    """Test error when using a reserved name as task text."""
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "add", "list"],
        env=test_env
    )
    assert exit_code != 0
    assert "is reserved" in stderr


def test_tasks_with_special_characters(test_env):
    """Test handling tasks with quotes and special characters."""
    # Task with special characters
    special_task = "Task with 'single quotes' and \"double quotes\""
    
    # Need to be careful with shell quoting - use shlex.join
    command = ["python", "-m", "tq", "add", special_task]
    stdout, stderr, exit_code = run_command(command, env=test_env)
    assert exit_code == 0
    
    # List and check the task text is preserved
    stdout, stderr, exit_code = run_command(
        ["python", "-m", "tq", "list"],
        env=test_env
    )
    assert exit_code == 0
    assert "Task with 'single quotes' and \"double quotes\"" in stdout


def test_unicode_support(test_env):
    """Test support for Unicode characters in tasks and queues."""
    # Add task with Unicode characters
    unicode_task = "こんにちは世界"
    unicode_queue = "日本語"
    
    command = ["python", "-m", "tq", "add", unicode_task, unicode_queue]
    stdout, stderr, exit_code = run_command(command, env=test_env)
    assert exit_code == 0
    
    # List tasks in Unicode queue
    command = ["python", "-m", "tq", "list", unicode_queue]
    stdout, stderr, exit_code = run_command(command, env=test_env)
    assert exit_code == 0
    assert unicode_task in stdout
