import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

import media_workflow.workflows.adobe_psd_thumbnail as adobe_psd_thumbnail
import media_workflow.workflows.image_thumbnail as image_thumbnail


async def main():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    worker = Worker(
        client,
        task_queue="default",
        workflows=[adobe_psd_thumbnail.Workflow, image_thumbnail.Workflow],
        activities=[adobe_psd_thumbnail.psd_thumbnail, image_thumbnail.image_thumbnail],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
