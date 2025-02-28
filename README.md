# tqu – A Minimal CLI for Queue-Based Task Tracking

`tqu` is a lightweight command-line tool designed for queue-based task tracking with minimal overhead. Instead of complicated features like priorities or due dates, `tqu` uses a simple push/pop workflow across one or multiple queues. Whether you're managing everyday chores, bills, or side projects, `tqu` keeps task tracking fast, intuitive, and distraction-free.

## Highlights

- **Minimalist approach**: Focuses solely on adding and removing tasks in a queue. No complicated features like priorities, due dates, or attachments.
- **Queue-Based**: Default queue for simple use, but supports multiple queues for different contexts (e.g., “daily,” “bills,” “my_project”).
- **CLI-centric**: Fast interaction entirely through the command line
- **Low Friction**: Short commands with sensible defaults, and queues are auto-created without extra steps.

## Installation

1. Install (recommended via [pipx](https://pypa.github.io/pipx/)):

   ```
   pipx install tqu
   ```

   or

   ```
   pip install --user tqu
   ```

2. (Optional) By default, `tqu` stores its database at `~/.tqu.sqlite`. You can customize the location by setting the `TQU_DB_PATH` environment variable:

   ```bash
   export TQU_DB_PATH="/path/to/your/custom/database.sqlite"
   ```

## Usage

Below are the commands you can run with tqu. In all cases, if you omit the queue name, `default` is used.

### Basic: Single Queue Mode

For simple task management, you can use the default queue without specifying a queue name:

1. Add a task to the default queue:

   ```
   tqu add "Pay electricity bill"
   ```

2. List tasks in the default queue:

   ```
   tqu list
   ```

   This shows active tasks along with their IDs, oldest added task first.

3. Remove the most recent (last) task from the default queue:

   ```
   tqu pop
   ```

   or

   ```
   tqu poplast
   ```

   This prints the removed task.

4. Remove the least recent (first) task from the default queue:

   ```
   tqu popfirst
   ```

   This prints the removed task.

5. Delete a task by its unique integer ID (no queue needed):

   ```
   tqu delete <task_id>
   ```

6. Delete the default queue (and all tasks in it):
   ```
   tqu delete
   ```
   This prints all removed tasks from that queue.

### Advanced: Multiple Queue Mode

Organize tasks into separate queues for different contexts. For multiple queues, simply add `<queue>` as the last argument.

1. Add a task to a specific queue:

   ```
   tqu add "Buy groceries" errands
   ```

   If the queue “errands” does not exist, tqu creates it automatically. Note that, queue name can not be only numeric.

2. List tasks in a specific queue:

   ```
   tqu list errands
   ```

3. Pop the most recent task from a specific queue:

   ```
   tqu pop errands
   ```

   (or “poplast”)

4. Pop the least recent task from a specific queue:

   ```
   tqu popfirst errands
   ```

5. Delete an entire queue (and all tasks in it):

   ```
   tqu delete errands
   ```

6. Delete a single task by ID (no need for queue name):

   ```
   tqu delete <task_id>
   ```

7. List all queues that have at least one active task:
   ```
   tqu
   ```

## Everyday Use Cases

Here are some everyday scenarios in which tqu can keep you organized:

1. Daily Planning: Keep track of things you need to do today or this month in queues like `today`, `month`, `feb2025`, or `biils`.
2. Reimbursements: Keep track of reimbursements you need to file at the end of the month in a queue named `reimbursements`.
3. Reading / Watch / Listen Lists: Keep track of books, papers, blogs, movies, podcasts, or music you want to consume in queues like `books`, `papers`, `movies`, `podcasts`, or `music`.
4. Side Projects: Keep track of tasks for side projects in queues like `project1`, `project2`, or `project3`.
5. Travel Planning: Keep track of things you need to do before your next trip in a queue named `travel` or `taiwan-trip`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
