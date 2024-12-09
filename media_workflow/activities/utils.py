import mimetypes
import os
import tempfile
from pathlib import Path
from uuid import uuid4

import aiohttp
import boto3
from botocore.config import Config
from temporalio import activity

from media_workflow.trace import span_attribute


@activity.defn
async def download(url) -> str:
    """Download a file from a URL. Return the file path.

    The filename is randomly generated. If the server returns a Content-Type header, it will be
    used to attach a file extension."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            mimetype = response.headers.get("Content-Type")
            data = await response.read()

    dir = tempfile.gettempdir()
    filename = str(uuid4())
    if mimetype and (ext := mimetypes.guess_extension(mimetype)):
        filename += ext
    path = os.path.join(dir, filename)

    with open(path, "wb") as file:
        file.write(data)

    span_attribute("url", url)
    span_attribute("path", path)
    return path


@activity.defn
async def upload(path: str, content_type: str = "binary/octet-stream"):
    """Upload file to S3-compatible storage. Return a presigned URL that can be used to download
    the file."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(region_name=os.environ["S3_REGION"], signature_version="v4"),
    )
    with open(path, "rb") as file:
        key = Path(path).name
        data = file.read()
        s3.put_object(
            Bucket=os.environ["S3_BUCKET"],
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    presigned_url = s3.generate_presigned_url(
        "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
    )
    span_attribute("key", key)
    span_attribute("path", path)
    span_attribute("content_type", content_type)
    span_attribute("presigned_url", presigned_url)
    return presigned_url


@activity.defn
async def callback(url: str, data: dict):
    span_attribute("url", url)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status != 200:
                raise Exception(f"callback failed: {await response.text()}")
