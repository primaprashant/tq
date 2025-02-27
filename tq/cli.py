import sys
from typing import Any, Callable, Dict, Optional

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from tq import db
from tq.exceptions import (
    DatabaseError,
    EmptyQueueError,
    QueueNotFoundError,
    TaskAlreadyExistsError,
    TaskNotFoundError,
    TQError,
)

console = Console()

# Consistent styling
STYLES = {
    "success": Style(color="green", bold=True),
    "error": Style(color="red", bold=True),
    "queue": Style(color="blue", bold=True),
    "task": Style(color="yellow"),
    "id": Style(color="cyan"),
    "warning": Style(color="yellow"),
}


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Task Queue CLI application."""
    db.init_db()
    if ctx.invoked_subcommand is None:
        show_queues()


def show_queues() -> None:
    """Display all active queues."""
    try:
        queues = db.list_queues()
        if not queues:
            console.print(Panel("No active queues found.", style="yellow", box=box.ROUNDED))
            return

        table = Table(title="Active Queues", box=box.ROUNDED)
        table.add_column("Queue Name", style="blue")
        table.add_column("Number of Tasks", justify="right", style="cyan")

        for name, count in queues:
            table.add_row(name, f"{count}")

        console.print(table)
    except DatabaseError as e:
        exit_with_error(f"Failed to list queues: {e.message}")


@cli.command()
@click.argument("task_text")
@click.argument("queue", required=False, default="default")
def add(task_text: str, queue: str) -> None:
    """Add a task to the specified queue."""
    try:
        db.add_task(task_text, queue)
        text = Text()
        text.append("Added task to '", style="white")
        text.append(queue, style=STYLES["queue"])
        text.append("' queue: ", style="white")
        text.append(task_text, style=STYLES["task"])
        console.print(text)
    except TaskAlreadyExistsError as e:
        console.print(f"[yellow]{e.message}[/yellow]")
    except TQError as e:
        exit_with_error(e.message)


@cli.command()
@click.argument("queue", required=False, default="default")
def list(queue: str) -> None:
    """List all tasks in the specified queue."""
    try:
        tasks = db.list_tasks(queue)
        if not tasks:
            raise EmptyQueueError(queue)

        table = Table(title=f"Tasks in '{queue}' Queue", box=box.ROUNDED)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Task", style="yellow")

        for task in tasks:
            table.add_row(str(task["id"]), task["task_text"])

        console.print(table)
    except EmptyQueueError as e:
        console.print(Panel(e.message, style="yellow", box=box.ROUNDED))
    except TQError as e:
        exit_with_error(e.message)


def pop_task(queue: str, pop_function: Callable[[str], Dict[str, Any]]) -> None:
    """Remove a task using the provided pop function."""
    try:
        task = pop_function(queue)
        text = Text()
        text.append("Removed from '", style="white")
        text.append(queue, style=STYLES["queue"])
        text.append("' queue: ", style="white")
        text.append(task["task_text"], style=STYLES["task"])
        console.print(text)
    except EmptyQueueError as e:
        console.print(Panel(e.message, style="yellow", box=box.ROUNDED))
    except TQError as e:
        exit_with_error(e.message)


@cli.command()
@click.argument("queue", required=False, default="default")
def pop(queue: str) -> None:
    """Remove the last task from the queue (alias for poplast)."""
    pop_task(queue, db.pop_last)


@cli.command(name="poplast")
@click.argument("queue", required=False, default="default")
def pop_last(queue: str) -> None:
    """Remove the last task from the queue."""
    pop_task(queue, db.pop_last)


@cli.command(name="popfirst")
@click.argument("queue", required=False, default="default")
def pop_first(queue: str) -> None:
    """Remove the first task from the queue."""
    pop_task(queue, db.pop_first)


@cli.command()
@click.argument("id_or_queue", required=False, default="default")
def delete(id_or_queue: str) -> None:
    """Delete a task by ID or an entire queue by name."""
    try:
        is_id, entity_id = db.find_by_id_or_name(id_or_queue)

        if is_id:
            delete_task_by_id(entity_id)
        else:
            delete_queue_by_name(id_or_queue)
    except TQError as e:
        exit_with_error(e.message)


def delete_task_by_id(task_id: Optional[int]) -> None:
    """Delete a specific task by its ID."""
    try:
        if task_id is None:
            raise TaskNotFoundError("unknown")

        result = db.delete_task(task_id)
        queue_name, task_text = result
        text = Text()
        text.append("Deleted task [", style="white")
        text.append(str(task_id), style=STYLES["id"])
        text.append("] from '", style="white")
        text.append(queue_name, style=STYLES["queue"])
        text.append("' queue: ", style="white")
        text.append(task_text, style=STYLES["task"])
        console.print(text)
    except TaskNotFoundError as e:
        console.print(f"[yellow]{e.message}[/yellow]")
    except TQError as e:
        exit_with_error(e.message)


def delete_queue_by_name(queue_name: str) -> None:
    """Delete an entire queue and all its tasks."""
    try:
        tasks = db.delete_queue(queue_name)
        table = Table(title=f"Deleted '{queue_name}' Queue", box=box.ROUNDED)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Task", style="yellow")

        for task in tasks:
            table.add_row(str(task["id"]), task["task_text"])

        console.print(Panel(f"Deleted '{queue_name}' queue with {len(tasks)} tasks:", style="green", box=box.ROUNDED))
        console.print(table)
    except EmptyQueueError as e:
        console.print(Panel(e.message, style="yellow", box=box.ROUNDED))
    except QueueNotFoundError as e:
        exit_with_error(e.message)
    except TQError as e:
        exit_with_error(e.message)


def exit_with_error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit with specified code."""
    console.print(f"[red bold]Error:[/red bold] {message}")
    sys.exit(exit_code)


def main() -> None:
    """Main entry point for the CLI application."""
    try:
        cli()
    except TQError as e:
        exit_with_error(e.message, e.code if e.code is not None else 1)
    except Exception as e:
        exit_with_error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
