import asyncio

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

import media_workflow.activities.utils
import media_workflow.workflows
from media_workflow.client import get_client


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await get_client()
    worker = Worker(
        client,
        task_queue="webhook",
        workflows=[media_workflow.workflows.Webhook],
        activities=[media_workflow.activities.utils.webhook],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    print("starting worker on task_queue webhook")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
