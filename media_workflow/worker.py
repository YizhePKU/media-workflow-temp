import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

import media_workflow.activities
import media_workflow.workflows
from media_workflow.utils import get_worker_specific_task_queue


async def get_client():
    tracing_interceptor = TracingInterceptor()
    return await Client.connect(
        os.environ["TEMPORAL_SERVER_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        interceptors=[tracing_interceptor],
    )


async def main():
    client = await get_client()
    worker_specific_task_queue = get_worker_specific_task_queue()

    scheduler = Worker(
        client,
        task_queue="media",
        workflows=media_workflow.workflows.workflows,
    )
    worker = Worker(
        client,
        task_queue=worker_specific_task_queue,
        activities=media_workflow.activities.activities,
    )
    print(f"starting worker with task queue: {worker_specific_task_queue}")
    await asyncio.gather(scheduler.run(), worker.run())


if __name__ == "__main__":
    asyncio.run(main())
