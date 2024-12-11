import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

import media_workflow.activities
import media_workflow.workflows


async def get_client():
    tracing_interceptor = TracingInterceptor()
    return await Client.connect(
        os.environ["TEMPORAL_SERVER_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        interceptors=[tracing_interceptor],
    )


async def main():
    client = await get_client()
    worker = Worker(
        client,
        task_queue="media",
        workflows=media_workflow.workflows.workflows,
        activities=media_workflow.activities.activities,
    )
    print(f"starting worker on task_queue media")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
