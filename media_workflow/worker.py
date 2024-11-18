import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from media_workflow.workflows import adobe_psd_thumbnail as psd


async def main():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    worker = Worker(
        client,
        task_queue="default",
        workflows=[psd.Workflow],
        activities=[psd.psd2png, psd.callback],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
