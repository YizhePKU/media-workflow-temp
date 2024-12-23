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
        tls="TEMPORAL_TLS" in os.environ,
        interceptors=[tracing_interceptor],
    )


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await get_client()

    if value := os.environ.get("MEDIA_WORKFLOW_MAX_CONCURRENT_ACTIVITIES"):
        max_concurrent_activities = int(value)
    else:
        max_concurrent_activities = None

    worker = Worker(
        client,
        task_queue="media",
        workflows=media_workflow.workflows.workflows,
        activities=media_workflow.activities.activities,
        max_concurrent_activities=max_concurrent_activities,
    )
    print(
        f"starting worker on task_queue media, max_concurrent_activities={max_concurrent_activities}"
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
