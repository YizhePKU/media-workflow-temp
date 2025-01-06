import asyncio
import inspect

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

import media_workflow.workflows
from media_workflow.activities import calibrate, document, font, image, image_detail, utils, video
from media_workflow.client import connect

workflows = []
for _name, fn in inspect.getmembers(media_workflow.workflows):
    if hasattr(fn, "__temporal_workflow_definition"):
        workflows.append(fn)


activities = []
for module in [calibrate, document, font, image, utils, video, image_detail]:
    for _name, fn in inspect.getmembers(module):
        if hasattr(fn, "__temporal_activity_definition"):
            activities.append(fn)


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await connect()
    worker = Worker(
        client,
        task_queue="media",
        workflows=workflows,
        activities=activities,
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    print("starting worker on task_queue media")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
