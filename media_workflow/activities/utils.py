import hmac
import os
from base64 import b64decode, b64encode
from dataclasses import dataclass
from json import dumps as json_dumps
from pathlib import Path
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import aioboto3
import aiohttp
from botocore.config import Config
from temporalio import activity

from media_workflow.trace import span_attribute


def url2ext(url) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


def get_datadir() -> str:
    """Create the data directory for this workflow, shared between workers."""
    dir = os.path.join(os.environ["MEDIA_WORKFLOW_DATADIR"], activity.info().workflow_id)
    os.makedirs(dir, exist_ok=True)
    return dir


@dataclass
class DownloadParams:
    url: str


@activity.defn
async def download(params: DownloadParams) -> str:
    """Download a file from a URL. Return the file path.

    The filename is randomly generated, but if the original URL contains a file extension, it will
    be retained.
    """
    filename = str(uuid4()) + url2ext(params.url)
    path = os.path.join(get_datadir(), filename)

    timeout = aiohttp.ClientTimeout(total=1500, sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(params.url) as response:
            response.raise_for_status()
            with open(path, "wb") as file:
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
    """Upload file to S3-compatible storage.

    Return a presigned URL that can be used to download the file.
    """
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(region_name=os.environ["S3_REGION"], signature_version="v4"),
    ) as s3:
        with open(params.path, "rb") as file:
            key = Path(params.path).name
            data = file.read()
            await s3.put_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=key,
                Body=data,
                ContentType=params.content_type,
            )
        presigned_url = await s3.generate_presigned_url(
            "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
        )
        span_attribute("key", key)
        span_attribute("path", params.path)
        span_attribute("content_type", params.content_type)
        span_attribute("presigned_url", presigned_url)
        return presigned_url


@dataclass
class CallbackParams:
    url: str
    msg_id: str
    payload: dict


@activity.defn
async def callback(params: CallbackParams):
    span_attribute("msg_id", params.msg_id)
    span_attribute("url", params.url)

    msg_id = params.msg_id
    timestamp = int(time())
    payload = json_dumps(params.payload)

    key = b64decode(os.environ["WEBHOOK_SIGNATURE_KEY"].removeprefix("whsec_"))
    content = f"{msg_id}.{timestamp}.{payload}".encode()
    signature = hmac.digest(key, content, "sha256")

    async with aiohttp.ClientSession() as session:
        headers = {
            "webhook-id": msg_id,
            "webhook-timestamp": str(timestamp),
            "webhook-signature": f"v1,{b64encode(signature).decode()}",
        }
        async with session.post(params.url, headers=headers, data=payload) as response:
            response.raise_for_status()
