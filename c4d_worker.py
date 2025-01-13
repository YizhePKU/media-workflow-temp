import asyncio

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from media_workflow.activities.c4d_preview import c4d_preview
from media_workflow.client import connect


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await connect()
    worker = Worker(
        client,
        task_queue="media-c4d",
        activities=[c4d_preview],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    print("starting C4D worker on task queue media-c4d")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
