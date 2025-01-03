"""Temporal client that supports pydentic models and OpenTelemetry tracing."""

import json
import os

from pydantic_core import to_jsonable_python
from temporalio.api.common.v1 import Payload
from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.converter import (
    CompositePayloadConverter,
    DataConverter,
    DefaultPayloadConverter,
    JSONPlainPayloadConverter,
)


class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    def to_payload(self, value) -> Payload | None:
        return Payload(
            metadata={"encoding": self.encoding.encode()},
            data=json.dumps(value, separators=(",", ":"), sort_keys=True, default=to_jsonable_python).encode(),
        )


class PydanticPayloadConverter(CompositePayloadConverter):
    def __init__(self) -> None:
        super().__init__(
            *(
                c if not isinstance(c, JSONPlainPayloadConverter) else PydanticJSONPayloadConverter()
                for c in DefaultPayloadConverter.default_encoding_payload_converters
            )
        )


pydantic_data_converter = DataConverter(payload_converter_class=PydanticPayloadConverter)


async def get_client():
    tracing_interceptor = TracingInterceptor()
    return await Client.connect(
        os.environ["TEMPORAL_SERVER_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        tls="TEMPORAL_TLS" in os.environ,
        interceptors=[tracing_interceptor],
        data_converter=pydantic_data_converter,
    )
