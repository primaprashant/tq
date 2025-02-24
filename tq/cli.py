import sys

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from tq import db

console = Console()

SUCCESS_STYLE = Style(color="green", bold=True)
ERROR_STYLE = Style(color="red", bold=True)
QUEUE_STYLE = Style(color="blue", bold=True)
TASK_STYLE = Style(color="yellow")
ID_STYLE = Style(color="cyan")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    db.init_db()
    if ctx.invoked_subcommand is None:
        queues = db.list_queues()
        if not queues:
            console.print(Panel("No active queues found.", style="yellow", box=box.ROUNDED))
            return

        table = Table(title="Active Queues", box=box.ROUNDED)
        table.add_column("Queue Name", style="blue")
        table.add_column("Tasks", justify="right", style="cyan")

        for name, count in queues:
            plural = "s" if count != 1 else ""
            table.add_row(name, f"{count} task{plural}")

        console.print(table)


@cli.command()
@click.argument("task_text")
@click.argument("queue", required=False, default="default")
def add(task_text, queue):
    try:
        if db.add_task(task_text, queue):
            text = Text()
            text.append("Added task to '", style="white")
            text.append(queue, style=QUEUE_STYLE)
            text.append("' queue: ", style="white")
            text.append(task_text, style=TASK_STYLE)
            console.print(text)
        else:
            console.print(f"[yellow]Task already exists in '[blue]{queue}[/blue]' queue: {task_text}[/yellow]")
    except ValueError as e:
        console.print(f"[red bold]Error:[/red bold] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument("queue", required=False, default="default")
def list(queue):
    tasks = db.list_tasks(queue)
    if not tasks:
        console.print(Panel(f"No tasks in '{queue}' queue.", style="yellow", box=box.ROUNDED))
        return

    table = Table(title=f"Tasks in '{queue}' Queue", box=box.ROUNDED)
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Task", style="yellow")

    for task in tasks:
        table.add_row(str(task["id"]), task["task_text"])

    console.print(table)


def pop_task(queue, func):
    task = func(queue)
    if task:
        text = Text()
        text.append("Removed from '", style="white")
        text.append(queue, style=QUEUE_STYLE)
        text.append("' queue: ", style="white")
        text.append(task["task_text"], style=TASK_STYLE)
        console.print(text)
    else:
        console.print(Panel(f"No tasks in '{queue}' queue.", style="yellow", box=box.ROUNDED))


@cli.command()
@click.argument("queue", required=False, default="default")
def pop(queue):
    pop_task(queue, db.pop_last)


@cli.command(name="poplast")
@click.argument("queue", required=False, default="default")
def pop_last(queue):
    pop_task(queue, db.pop_last)


@cli.command(name="popfirst")
@click.argument("queue", required=False, default="default")
def pop_first(queue):
    pop_task(queue, db.pop_first)


@cli.command()
@click.argument("id_or_queue", required=False, default="default")
def delete(id_or_queue):
    is_id, task_id = db.find_by_id_or_name(id_or_queue)
    if is_id:
        if task_id is not None:
            result = db.delete_task(task_id)
            if result:
                queue_name, task_text = result
                text = Text()
                text.append("Deleted task [", style="white")
                text.append(str(task_id), style=ID_STYLE)
                text.append("] from '", style="white")
                text.append(queue_name, style=QUEUE_STYLE)
                text.append("' queue: ", style="white")
                text.append(task_text, style=TASK_STYLE)
                console.print(text)
            else:
                console.print(
                    "[yellow]Task with ID [cyan]{}[/cyan] not found or already completed.[/yellow]".format(task_id)
                )
        else:
            console.print(
                "[yellow]Task with ID [cyan]{}[/cyan] not found or already completed.[/yellow]".format(id_or_queue)
            )
    else:
        tasks = db.delete_queue(id_or_queue)
        if tasks:
            table = Table(title=f"Deleted '{id_or_queue}' Queue", box=box.ROUNDED)
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("Task", style="yellow")

            for task in tasks:
                table.add_row(str(task["id"]), task["task_text"])

            console.print(
                Panel(f"Deleted '{id_or_queue}' queue with {len(tasks)} tasks:", style="green", box=box.ROUNDED)
            )
            console.print(table)
        else:
            console.print(Panel(f"No tasks in '{id_or_queue}' queue.", style="yellow", box=box.ROUNDED))


def main():
    try:
        cli()
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
