import asyncio

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from media_workflow.activities.webhook import webhook
from media_workflow.client import connect
from media_workflow.workflows import Webhook


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await connect()
    worker = Worker(
        client,
        task_queue="webhook",
        workflows=[Webhook],
        activities=[webhook],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    print("starting worker on task_queue webhook")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
