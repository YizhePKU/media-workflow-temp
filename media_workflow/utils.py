import os
from io import BytesIO
from typing import BinaryIO

import boto3
import pillow_avif
from botocore.config import Config
from cairosvg import svg2png
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
from psd_tools import PSDImage

register_heif_opener()

# Remove image file size limit
Image.MAX_IMAGE_PIXELS = None

# Monkey patch PIL.Image.open with our own version that supports SVG
original_image_open = Image.open


def _image_open(file: BinaryIO) -> Image:
    try:
        return original_image_open(file)
    except UnidentifiedImageError:
        # Use cargosvg to open SVG.
        try:
            file.seek(0)
            return original_image_open(BytesIO(svg2png(file_obj=file)))
        except:
            pass
        # Use PsdTools to open PSD and PSB.
        try:
            file.seek(0)
            return PSDImage.open(file).composite()
        except:
            pass
        raise


Image.open = _image_open


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
