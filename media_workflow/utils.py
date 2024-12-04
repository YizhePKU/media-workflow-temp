import os

import aiohttp
import boto3
from botocore.config import Config

from media_workflow.trace import span_attribute, tracer


@tracer.start_as_current_span("fetch")
async def fetch(uri) -> bytes:
    """Fetch bytes from a URI or a local path."""
    span_attribute("uri", uri)
    assert not isinstance(uri, bytes)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(uri) as response:
                return await response.read()
    except aiohttp.client_exceptions.InvalidUrlClientError:
        with open(uri, "rb") as file:
            return file.read()


@tracer.start_as_current_span("upload")
def upload(key: str, data: bytes, content_type: str = "binary/octet-stream"):
    """Upload data to S3-compatible storage. Return a presigned URL that downloads the file."""
    span_attribute("key", key)
    span_attribute("content_type", content_type)

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(region_name=os.environ["S3_REGION"], signature_version="v4"),
    )
    s3.put_object(
        Bucket=os.environ["S3_BUCKET"], Key=key, Body=data, ContentType=content_type
    )
    presigned_url = s3.generate_presigned_url(
        "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
    )

    span_attribute("presigned_url", presigned_url)
    return presigned_url
