import sys
import click
from tq import db


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    db.init_db()
    if ctx.invoked_subcommand is None:
        queues = db.list_queues()
        if not queues:
            click.echo("No active queues found.")
            return
        click.echo("Active queues:")
        for name, count in queues:
            plural = 's' if count != 1 else ''
            click.echo(f"{name}: {count} task{plural}")

@cli.command()
@click.argument('task_text')
@click.argument('queue', required=False, default="default")
def add(task_text, queue):
    try:
        if db.add_task(task_text, queue):
            click.echo(f"Added task to '{queue}' queue: {task_text}")
        else:
            click.echo(f"Task already exists in '{queue}' queue: {task_text}")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('queue', required=False, default="default")
def list(queue):
    tasks = db.list_tasks(queue)
    if not tasks:
        click.echo(f"No tasks in '{queue}' queue.")
        return
    click.echo(f"Tasks in '{queue}' queue:")
    for task in tasks:
        click.echo(f"  [{task['id']}] {task['task_text']}")

def pop_task(queue, func):
    task = func(queue)
    if task:
        click.echo(f"Removed from '{queue}' queue: {task['task_text']}")
    else:
        click.echo(f"No tasks in '{queue}' queue.")

@cli.command()
@click.argument('queue', required=False, default="default")
def pop(queue):
    pop_task(queue, db.pop_last)

@cli.command(name="poplast")
@click.argument('queue', required=False, default="default")
def pop_last(queue):
    pop_task(queue, db.pop_last)

@cli.command(name="popfirst")
@click.argument('queue', required=False, default="default")
def pop_first(queue):
    pop_task(queue, db.pop_first)

@cli.command()
@click.argument('id_or_queue', required=False, default="default")
def delete(id_or_queue):
    is_id, task_id = db.find_by_id_or_name(id_or_queue)
    if is_id:
        if task_id is not None:
            result = db.delete_task(task_id)
            if result:
                queue_name, task_text = result
                click.echo(f"Deleted task [{task_id}] from '{queue_name}' queue: {task_text}")
            else:
                click.echo(f"Task with ID {task_id} not found or already completed.")
        else:
            click.echo(f"Task with ID {id_or_queue} not found or already completed.")
    else:
        tasks = db.delete_queue(id_or_queue)
        if tasks:
            click.echo(f"Deleted '{id_or_queue}' queue with {len(tasks)} tasks:")
            for task in tasks:
                click.echo(f"  [{task['id']}] {task['task_text']}")
        else:
            click.echo(f"No tasks in '{id_or_queue}' queue.")

def main():
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()