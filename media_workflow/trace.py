"""OpenTelemetry tracing.

This module exposes a global `tracer` that can be used to create spans. The `instrument` decorator
can be used to trace a function and record its arguments and return value.

Currently, only [Honeycomb](https://www.honeycomb.io) is supported as the tracing backend.
"""

import functools
import inspect
import os

import pydantic_core
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Create a trace provider that sends traces to Honeycomb.
_provider = TracerProvider(resource=Resource(attributes={SERVICE_NAME: "media-workflow"}))
if honeycomb_key := os.environ.get("HONEYCOMB_KEY"):
    _processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="https://api.honeycomb.io/v1/traces",
            headers={"x-honeycomb-team": honeycomb_key},
        )
    )
    _provider.add_span_processor(_processor)

trace.set_tracer_provider(_provider)

# Use this global tracer to create spans.
tracer = trace.get_tracer("media-workflow")


def _is_valid_attribute(obj):
    types = [str, bool, int, float]
    return any(isinstance(obj, t) for t in types)


def _to_attribute(obj):
    if _is_valid_attribute(obj):
        return obj
    else:
        return pydantic_core.to_json(obj).decode()


def instrument(func=None, skip=["self"], return_value=True):  # noqa: B006
    """Decorator that creates a span with function arguments and return value as span attributes.

    Both sync and async functions are supported. Attribute names are prefixed with `func.` to avoid
    collision. Primitive types (str, bool, int, float) are saved as is, while other types are
    encoded in JSON.

    Args:
        skip: arguments that should not be saved return_value: whether to save the return value
    """  # noqa: D401
    if func is None:
        return lambda func: instrument(func, skip, return_value)

    signature = inspect.signature(func)

    @functools.wraps(func)
    async def _with_span_async(*args, **kwargs):
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        attributes = {f"func.{k}": _to_attribute(v) for k, v in bound_arguments.arguments.items() if k not in skip}
        with tracer.start_as_current_span(func.__name__, attributes=attributes) as span:
            result = await func(*args, **kwargs)
            if return_value:
                span.set_attribute("func.return_value", _to_attribute(result))
            return result

    @functools.wraps(func)
    def _with_span_sync(*args, **kwargs):
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()
        attributes = {f"func.{k}": _to_attribute(v) for k, v in bound_arguments.arguments.items() if k not in skip}
        with tracer.start_as_current_span(func.__name__, attributes=attributes) as span:
            result = func(*args, **kwargs)
            if return_value:
                span.set_attribute("func.return_value", _to_attribute(result))
            return result

    if inspect.iscoroutinefunction(func):
        return _with_span_async
    else:
        return _with_span_sync
