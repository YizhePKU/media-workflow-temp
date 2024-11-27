import asyncio
import inspect
import os

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

import media_workflow.activities
import media_workflow.workflows

workflows = []
for _name, cls in inspect.getmembers(media_workflow.workflows):
    if hasattr(cls, "__temporal_workflow_definition"):
        workflows.append(cls)

activities = []
for _name, fn in inspect.getmembers(media_workflow.activities):
    if hasattr(fn, "__temporal_activity_definition"):
        activities.append(fn)


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
        workflows=workflows,
        activities=activities,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
