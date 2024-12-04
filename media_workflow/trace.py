from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_provider = TracerProvider(
    resource=Resource(attributes={SERVICE_NAME: "media-workflow"})
)
_processor = BatchSpanProcessor(
    OTLPSpanExporter(
        endpoint=f"https://api.honeycomb.io/v1/traces",
        headers={"x-honeycomb-team": "rBVMZEaZzB10Ako9n0iP1C"},
    )
)
_provider.add_span_processor(_processor)

trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("media-workflow")


def span_attribute(key, value):
    span = trace.get_current_span()
    span.set_attribute(key, value)
