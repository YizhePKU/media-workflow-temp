import asyncio
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import aioboto3
import aiohttp
import c4d
from botocore.config import Config
from temporalio import activity
from temporalio.worker import Worker

from media_workflow.client import get_client
from media_workflow.trace import span_attribute, tracer


def url2ext(url) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


def get_datadir() -> str:
    return tempfile.mkdtemp()


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
            "get_object", Params={"Bucket": os.environ["S3_BUCKET"], "Key": key}
        )
        span_attribute("key", key)
        span_attribute("path", params.path)
        span_attribute("content_type", params.content_type)
        span_attribute("presigned_url", presigned_url)
        return presigned_url


@dataclass
class PreviewParams:
    url: str


@activity.defn(name="c4d-preview")
async def preview(params: PreviewParams):
    gltf = f"{get_datadir()}/{uuid4()}.gltf"
    png = f"{get_datadir()}/{uuid4()}.png"

    with tracer.start_as_current_span("c4d-download"):
        file = await download(DownloadParams(params.url))

    with tracer.start_as_current_span("c4d-load-document"):
        doc = c4d.documents.LoadDocument(file, c4d.SCENEFILTER_OBJECTS)
        assert doc is not None
        print(f"loaded {file}")

    with tracer.start_as_current_span("c4d-export-gltf"):
        c4d.documents.SaveDocument(doc, gltf, 0, c4d.FORMAT_GLTFEXPORT)
        print(f"exported {gltf}")

    with tracer.start_as_current_span("c4d-upload-gltf"):
        gltf_url = await upload(UploadParams(gltf))
        print(f"uploaded {gltf}")

    with tracer.start_as_current_span("c4d-export-png"):
        bitmap = doc.GetDocPreviewBitmap()
        ret = bitmap.Save(png, c4d.FILTER_PNG)
        assert ret == c4d.IMAGERESULT_OK
        print(f"exported {png}")

    with tracer.start_as_current_span("c4d-upload-png"):
        png_url = await upload(UploadParams(png))
        print(f"uploaded {png}")

    return {"gltf": gltf_url, "png": png_url}


async def main():
    client = await get_client()
    worker = Worker(
        client,
        task_queue="media-c4d",
        activities=[preview],
    )
    print("starting worker on task queue media-c4d")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
