import os

from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor


async def get_client():
    tracing_interceptor = TracingInterceptor()
    return await Client.connect(
        os.environ["TEMPORAL_SERVER_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        tls="TEMPORAL_TLS" in os.environ,
        interceptors=[tracing_interceptor],
    )
