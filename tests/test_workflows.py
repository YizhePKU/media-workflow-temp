import os
from io import BytesIO
from uuid import uuid4

import aiohttp
from PIL import Image
from temporalio.client import Client


async def test_image_thumbnail():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/%E5%BC%B9%E6%A1%8612.psd",
        "size": (200, 200),
    }
    output = await client.execute_workflow(
        "image-thumbnail", arg, id=f"{uuid4()}", task_queue="default"
    )
    async with aiohttp.ClientSession() as client:
        async with client.get(output["file"]) as response:
            image = Image.open(BytesIO(await response.read()))
    assert image.size[0] <= 200
    assert image.size[1] <= 200


async def test_pdf_thumbnail():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/sample-3.pdf",
        "size": (200, 200),
    }
    output = await client.execute_workflow(
        "pdf-thumbnail", arg, id=f"{uuid4()}", task_queue="default"
    )
    async with aiohttp.ClientSession() as client:
        async with client.get(output["file"]) as response:
            image = Image.open(BytesIO(await response.read()))
    assert image.size[0] <= 200
    assert image.size[1] <= 200


async def test_image_detail():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/cat.jpg",
        "language": "Simplified Chinese",
    }
    output = await client.execute_workflow(
        "image-detail", arg, id=f"{uuid4()}", task_queue="default"
    )
    assert "title" in output
