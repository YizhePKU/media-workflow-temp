from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
import boto3
from botocore.config import Config
from temporalio import activity

from media_workflow.trace import span_attribute
from media_workflow.utils import ensure_exists


def url2ext(url) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


def get_datadir() -> str:
    """Create the data directory for this workflow, shared between workers."""
    dir = os.path.join(
        os.environ["MEDIA_WORKFLOW_DATADIR"], activity.info().workflow_id
    )
    os.makedirs(dir, exist_ok=True)
    return dir


@dataclass
class DownloadParams:
    url: str


@activity.defn
async def download(params: DownloadParams) -> str:
    """Download a file from a URL. Return the file path.

    The filename is randomly generated, but if the original URL contains a file extension, it will
    be retained."""
    filename = str(uuid4()) + url2ext(params.url)
    path = os.path.join(get_datadir(), filename)

    with open(path, "wb") as file:
        async with aiohttp.ClientSession() as session:
            async with session.get(params.url) as response:
                response.raise_for_status()
                async for chunk, _ in response.content.iter_chunks():
                    file.write(chunk)
                    activity.heartbeat()

    span_attribute("url", params.url)
    span_attribute("path", path)
    return path


@dataclass
class UploadParams:
    path: str
    content_type: str = "binary/octet-stream"


@activity.defn
async def upload(params: UploadParams) -> str:
    """Upload file to S3-compatible storage. Return a presigned URL that can be used to download
    the file."""
    ensure_exists(params.path)
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(region_name=os.environ["S3_REGION"], signature_version="v4"),
    )
    with open(params.path, "rb") as file:
        key = Path(params.path).name
        data = file.read()
        s3.put_object(
            Bucket=os.environ["S3_BUCKET"],
            Key=key,
            Body=data,
            ContentType=params.content_type,
        )
    presigned_url = s3.generate_presigned_url(
        "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
    )
    span_attribute("key", key)
    span_attribute("path", params.path)
    span_attribute("content_type", params.content_type)
    span_attribute("presigned_url", presigned_url)
    return presigned_url


@activity.defn
async def callback(url: str, data: dict):
    span_attribute("url", url)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status != 200:
                raise Exception(f"callback failed: {await response.text()}")
