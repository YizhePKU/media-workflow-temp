import asyncio

from temporalio.worker import Worker

import media_workflow.activities
import media_workflow.workflows
from media_workflow.client import get_client


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await get_client()
    worker = Worker(
        client,
        task_queue="media",
        workflows=media_workflow.workflows.workflows,
        activities=media_workflow.activities.activities,
    )
    print("starting worker on task_queue media")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
