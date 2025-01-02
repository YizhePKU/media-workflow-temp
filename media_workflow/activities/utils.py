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

from media_workflow.trace import instrument


def get_datadir() -> Path:
    """Create the data directory for this workflow, shared between workers."""
    datadir = Path(os.environ["MEDIA_WORKFLOW_DATADIR"]) / activity.info().workflow_id
    datadir.mkdir(parents=True, exist_ok=True)
    return datadir


@dataclass
class DownloadParams:
    url: str


@instrument
@activity.defn
async def download(params: DownloadParams) -> str:
    """Download a file from a URL. Return the file path.

    The filename is randomly generated, but if the original URL contains a file extension, it will
    be retained.
    """
    # If MEDIA_WORKFLOW_TEST_DATADIR is set, check that directory for filename matches.
    path = Path(urlparse(params.url).path)
    if datadir := os.environ.get("MEDIA_WORKFLOW_TEST_DATADIR"):
        file = Path(datadir) / path.name
        if file.exists():
            return str(file)

    file = f"{get_datadir()}/{uuid4()}{path.suffix}"
    timeout = aiohttp.ClientTimeout(total=1500, sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(params.url) as response:
            response.raise_for_status()
            with open(file, "wb") as fp:
                async for chunk, _ in response.content.iter_chunks():
                    fp.write(chunk)
                    activity.heartbeat()
    return file


@dataclass
class UploadParams:
    path: str
    content_type: str = "binary/octet-stream"


@instrument
@activity.defn
async def upload(params: UploadParams) -> str:
    """Upload file to S3-compatible storage.

    Return a presigned URL that can be used to download the file.
    """
    # If MEDIA_WORKFLOW_TEST_SKIP_UPLOAD is set, return the path as is.
    if os.environ.get("MEDIA_WORKFLOW_TEST_SKIP_UPLOAD"):
        return params.path

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
            "get_object", Params={"Bucket": os.environ["S3_BUCKET"], "Key": key}
        )
        return presigned_url


@dataclass
class WebhookParams:
    url: str
    msg_id: str
    payload: dict


@instrument
@activity.defn
async def webhook(params: WebhookParams):
    msg_id = params.msg_id
    timestamp = int(time())
    payload = json_dumps(params.payload)

    key = b64decode(os.environ["WEBHOOK_SIGNATURE_KEY"].removeprefix("whsec_"))
    content = f"{msg_id}.{timestamp}.{payload}".encode()
    signature = hmac.digest(key, content, "sha256")

    async with aiohttp.ClientSession() as session:
        headers = {
            "content-type": "application/json",
            "webhook-id": msg_id,
            "webhook-timestamp": str(timestamp),
            "webhook-signature": f"v1,{b64encode(signature).decode()}",
        }
        async with session.post(params.url, headers=headers, data=payload) as response:
            response.raise_for_status()
