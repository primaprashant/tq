import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_env():
    """Create a test environment with a dedicated database file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.sqlite"  # changed from os.path.join()
        env = os.environ.copy()
        env["TQU_DB_PATH"] = str(db_path)
        # Disable Rich's color output for testing
        env["NO_COLOR"] = "1"
        # Force terminal width for consistent table formatting
        env["COLUMNS"] = "100"
        yield env


def run_command(cmd, env=None):
    """Run a shell command and return its output and exit code."""
    process = subprocess.run(
        cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=isinstance(cmd, str)
    )
    return process.stdout, process.stderr, process.returncode


def normalize_output(output):
    """Normalize Rich's output for consistent testing."""
    # Replace multiple spaces with single space
    output = " ".join(output.split())
    # Remove box drawing characters
    for char in "╭╮╰╯─│┤├┼":
        output = output.replace(char, "")
    return output


def test_add_and_list_task(test_env):
    """Test adding a task and then listing it."""
    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "add", "test task", "work"], env=test_env)
    assert exit_code == 0
    assert "test task" in normalize_output(stdout)
    assert "work" in normalize_output(stdout)

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "list", "work"], env=test_env)
    assert exit_code == 0
    normalized = normalize_output(stdout)
    assert "work" in normalized
    assert "test task" in normalized
    assert "ID" in normalized  # Check for table header


def test_add_and_pop_task(test_env):
    """Test adding a task and then popping it."""
    run_command(["python", "-m", "tqu", "add", "task to pop", "temp"], env=test_env)

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "pop", "temp"], env=test_env)
    assert exit_code == 0
    assert "task to pop" in normalize_output(stdout)

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "list", "temp"], env=test_env)
    assert exit_code == 0
    assert "No tasks in 'temp' queue" in normalize_output(stdout)


def test_add_and_delete_task_by_id(test_env):
    """Test adding a task and then deleting it by ID."""
    run_command(["python", "-m", "tqu", "add", "task for deletion"], env=test_env)

    # Get task ID from list output
    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "list"], env=test_env)
    normalized = normalize_output(stdout)
    # Find the ID number in the normalized output
    task_id = None
    for word in normalized.split():
        if word.isdigit():
            task_id = word
            break
    assert task_id is not None

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "delete", task_id], env=test_env)
    assert exit_code == 0
    normalized = normalize_output(stdout)
    assert task_id in normalized
    assert "task for deletion" in normalized


def test_add_and_popfirst_task(test_env):
    """Test adding multiple tasks and then popping the first one."""
    run_command(["python", "-m", "tqu", "add", "first task", "fifo"], env=test_env)
    run_command(["python", "-m", "tqu", "add", "second task", "fifo"], env=test_env)

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "popfirst", "fifo"], env=test_env)
    assert exit_code == 0
    assert "first task" in normalize_output(stdout)


def test_delete_queue(test_env):
    """Test adding tasks to a queue and then deleting the entire queue."""
    run_command(["python", "-m", "tqu", "add", "task 1", "project"], env=test_env)
    run_command(["python", "-m", "tqu", "add", "task 2", "project"], env=test_env)

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "delete", "project"], env=test_env)
    assert exit_code == 0
    normalized = normalize_output(stdout)
    assert "project" in normalized
    assert "task 1" in normalized
    assert "task 2" in normalized


def test_list_queues(test_env):
    """Test that the base command lists all queues with tasks."""
    run_command(["python", "-m", "tqu", "add", "default task"], env=test_env)
    run_command(["python", "-m", "tqu", "add", "work task", "work"], env=test_env)
    run_command(["python", "-m", "tqu", "add", "second work task", "work"], env=test_env)

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu"], env=test_env)
    assert exit_code == 0
    normalized = normalize_output(stdout)
    assert "default" in normalized
    assert "1" in normalized
    assert "work" in normalized
    assert "2" in normalized


def test_error_on_numeric_queue(test_env):
    """Test error when using a numeric queue name."""
    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "add", "numeric queue task", "123"], env=test_env)
    assert exit_code != 0
    normalized_output = normalize_output(stdout)
    assert "Error" in normalized_output
    assert "cannot be numeric only" in normalized_output


def test_tasks_with_special_characters(test_env):
    """Test handling tasks with quotes and special characters."""
    special_task = "Task with 'single quotes' and \"double quotes\""

    command = ["python", "-m", "tqu", "add", special_task]
    stdout, stderr, exit_code = run_command(command, env=test_env)
    assert exit_code == 0

    stdout, stderr, exit_code = run_command(["python", "-m", "tqu", "list"], env=test_env)
    assert exit_code == 0
    assert special_task in normalize_output(stdout)


def test_unicode_support(test_env):
    """Test support for Unicode characters in tasks and queues."""
    unicode_task = "こんにちは世界"
    unicode_queue = "日本語"

    command = ["python", "-m", "tqu", "add", unicode_task, unicode_queue]
    stdout, stderr, exit_code = run_command(command, env=test_env)
    assert exit_code == 0

    command = ["python", "-m", "tqu", "list", unicode_queue]
    stdout, stderr, exit_code = run_command(command, env=test_env)
    assert exit_code == 0
    assert unicode_task in normalize_output(stdout)
