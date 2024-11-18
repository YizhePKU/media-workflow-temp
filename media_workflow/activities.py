from io import BytesIO
from typing import Tuple
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import requests
    from PIL import Image
    from psd_tools import PSDImage

    from media_workflow.s3 import upload


def image2png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


@activity.defn
async def image_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    image = Image.open(BytesIO(requests.get(url).content))
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))


@activity.defn
async def adobe_photoshop_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    psd = PSDImage.open(BytesIO(requests.get(url).content))
    image = psd.thumbnail() if psd.has_thumbnail() else psd.composite()
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))
