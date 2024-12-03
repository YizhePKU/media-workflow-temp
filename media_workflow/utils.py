import os
from io import BytesIO

import aiohttp
import boto3
import imageio.v3 as iio
from botocore.config import Config
from cairosvg import svg2png
from PIL import Image
from psd_tools import PSDImage

# remove image size limit
Image.MAX_IMAGE_PIXELS = None


async def fetch(uri) -> bytes:
    """Fetch bytes from a URI or a local path."""
    assert not isinstance(uri, bytes)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(uri) as response:
                return await response.read()
    except aiohttp.client_exceptions.InvalidUrlClientError:
        with open(uri, "rb") as file:
            return file.read()


async def imread(uri: str, **kwargs) -> Image:
    """Read an image from a URI or a local path."""
    bytes = await fetch(uri)

    # open the image with imageio
    try:
        return Image.fromarray(iio.imread(bytes, **kwargs))
    except:
        pass

    # open the image with psd-tools
    try:
        return PSDImage.open(BytesIO(bytes)).composite()
    except:
        pass

    # open the image with cairosvg
    try:
        return Image.open(BytesIO(svg2png(file_obj=BytesIO(bytes))))
    except:
        pass

    # give up
    raise ValueError(f"Failed to open image {uri}")


def upload(key: str, data: bytes, content_type: str = "binary/octet-stream"):
    """Upload data to S3-compatible storage. Return a presigned URL that downloads the file."""
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(region_name=os.environ["S3_REGION"], signature_version="v4"),
    )
    s3.put_object(
        Bucket=os.environ["S3_BUCKET"], Key=key, Body=data, ContentType=content_type
    )
    return s3.generate_presigned_url(
        "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
    )
