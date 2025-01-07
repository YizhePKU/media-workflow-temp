"""Temporal client that supports `pathlib.Path`, pydantic models, and OpenTelemetry tracing.

This module is adapted from the [offical pydantic converter
example](https://github.com/temporalio/samples-python/tree/main/pydantic_converter), with
modifications to support `pathlib.Path`.

This module also adds a `TracingInterceptor` to support OpenTelemetry, but the actual tracing
configurations are defined in `trace.py`.
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel
from pydantic_core import to_jsonable_python
from temporalio.api.common.v1 import Payload
from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.converter import (
    CompositePayloadConverter,
    DataConverter,
    DefaultPayloadConverter,
    JSONPlainPayloadConverter,
    JSONTypeConverter,
)


class _PydanticJSONTypeConverter(JSONTypeConverter):
    def to_typed_value(self, hint, value):
        if isinstance(hint, type) and issubclass(hint, BaseModel):
            return hint.model_validate(value)
        elif isinstance(hint, type) and issubclass(hint, Path):
            return Path(value)
        else:
            return JSONTypeConverter.Unhandled


class _PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    def __init__(self):
        super().__init__(custom_type_converters=[_PydanticJSONTypeConverter()])

    def to_payload(self, value) -> Payload | None:
        return Payload(
            metadata={"encoding": self.encoding.encode()},
            data=json.dumps(value, separators=(",", ":"), sort_keys=True, default=to_jsonable_python).encode(),
        )


class _PydanticPayloadConverter(CompositePayloadConverter):
    def __init__(self) -> None:
        super().__init__(
            *(
                c if not isinstance(c, JSONPlainPayloadConverter) else _PydanticJSONPayloadConverter()
                for c in DefaultPayloadConverter.default_encoding_payload_converters
            )
        )


_pydantic_data_converter = DataConverter(payload_converter_class=_PydanticPayloadConverter)


async def connect():
    """Create a temporal client. Configurations are read from the environment."""
    tracing_interceptor = TracingInterceptor()
    return await Client.connect(
        os.environ["TEMPORAL_SERVER_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        tls="TEMPORAL_TLS" in os.environ,
        interceptors=[tracing_interceptor],
        data_converter=_pydantic_data_converter,
    )
