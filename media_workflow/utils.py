import os
from io import BytesIO
from typing import BinaryIO

import boto3
import pillow_avif
from cairosvg import svg2png
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()


def image_open(file: BinaryIO) -> Image:
    """Open an image as an PIL.Image instance.

    In addition to formats natively supported by PIL.Image (see [1] for the full list), this
    function also supports the following formats:

    HEIC: High Efficiency Image File
    AVIF: AV1 Image File Format
    SVG: Scalable Vector Graphics

    [1]: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
    """
    try:
        return Image.open(file)
    except UnidentifiedImageError:
        try:
            file.seek(0)
            return Image.open(BytesIO(svg2png(file_obj=file)))
        except:
            pass
        raise


def upload(key: str, data: bytes):
    """Upload data to S3-compatible storage. Return a presigned URL that downloads the file."""
    s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT_URL"])
    s3.put_object(Bucket=os.environ["S3_BUCKET"], Key=key, Body=data)
    return s3.generate_presigned_url(
        "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
    )
