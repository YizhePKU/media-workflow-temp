import os
import tempfile
from io import BytesIO
from uuid import uuid4

import aiohttp
import boto3
import imageio.v3 as iio
import numpy as np
from botocore.config import Config
from cairosvg import svg2png
from PIL import Image
from psd_tools import PSDImage

from media_workflow.trace import span_attribute, tracer


def get_worker_specific_task_queue() -> str:
    """Get the task queue uniquely associated with this worker.

    The return value persists between calls, but not between worker restart."""
    if not hasattr(get_worker_specific_task_queue, "value"):
        get_worker_specific_task_queue.value = f"task-queue-{uuid4()}"
    return get_worker_specific_task_queue.value


# remove image size limit
Image.MAX_IMAGE_PIXELS = None


@tracer.start_as_current_span("imread")
def imread(path: str) -> Image:
    """Read an image from a local path."""
    # open the image with imageio
    try:
        return Image.fromarray(iio.imread(path))
    except:
        pass

    # open the image with psd-tools
    try:
        return PSDImage.open(path).composite()
    except:
        pass

    # open the image with cairosvg
    try:
        return Image.open(BytesIO(svg2png(url=path)))
    except:
        pass

    # give up
    raise ValueError(f"failed to open image {path}")


@tracer.start_as_current_span("imwrite")
def imwrite(image: Image) -> str:
    """Write an image to a temporary file in PNG format. Return the file path."""
    # If the image is in floating point mode, scale the value by 255
    # See https://github.com/python-pillow/Pillow/issues/3159
    if image.mode == "F":
        image = Image.fromarray((np.array(image) * 255).astype(np.uint8), mode="L")

    path = os.path.join(tempfile.gettempdir(), f"{uuid4()}.png")
    image.convert("RGB").save(path)
    span_attribute("path", path)
    return path


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
