import os
from io import BytesIO
from typing import Tuple
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import aiohttp
    import pymupdf
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
async def callback(url: str, json):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json) as response:
            assert response.status == 200


@activity.defn
async def image_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            image = Image.open(BytesIO(await response.read()))
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))


@activity.defn
async def pdf_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            with pymupdf.Document(stream=await response.read()) as doc:
                image = page2image(doc[0])
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))


@activity.defn
async def image_detail(file_url: str, language: str):
    headers = {"Authorization": f"Bearer {os.environ["DIFY_IMAGE_DETAIL_KEY"]}"}
    json = {
        "inputs": {
            "language": language,
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": file_url,
            },
        },
        "user": os.environ["DIFY_USER"],
        "response_mode": "blocking",
    }
    async with aiohttp.ClientSession() as session:
        url = f"{os.environ["DIFY_ENDPOINT_URL"]}/workflows/run"
        async with session.post(url, headers=headers, json=json) as r:
            result = await r.json()
    assert result["data"]["status"] == "succeeded"
    assert isinstance(result["data"]["outputs"]["tags"], str)
    return result["data"]["outputs"]


@activity.defn
async def image_detail_basic(file_url: str, language: str):
    headers = {"Authorization": f"Bearer {os.environ["DIFY_IMAGE_DETAIL_BASIC_KEY"]}"}
    json = {
        "inputs": {
            "language": language,
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": file_url,
            },
            "use_local": "true",
        },
        "user": os.environ["DIFY_USER"],
        "response_mode": "blocking",
    }
    async with aiohttp.ClientSession() as session:
        url = f"{os.environ["DIFY_ENDPOINT_URL"]}/workflows/run"
        async with session.post(url, headers=headers, json=json) as r:
            result = await r.json()
    assert result["data"]["status"] == "succeeded"
    assert isinstance(result["data"]["outputs"]["tags"], str)
    return result["data"]["outputs"]
