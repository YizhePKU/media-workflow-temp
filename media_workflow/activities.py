from io import BytesIO
from typing import Tuple
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import pymupdf
    import requests
    from PIL import Image

    from media_workflow.s3 import upload


def image2png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


def page2image(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


@activity.defn
async def image_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    image = Image.open(BytesIO(requests.get(url).content))
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))


@activity.defn
async def pdf_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    with pymupdf.Document(stream=requests.get(url).content) as doc:
        image = page2image(doc[0])
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))
