import os
from io import BytesIO
from uuid import uuid4

import aiohttp
from aiohttp import web
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


async def test_image_thumbnail_with_callback():
    async def handler(request: web.Request):
        json = await request.json()
        async with aiohttp.ClientSession() as client:
            async with client.get(json["file"]) as response:
                image = Image.open(BytesIO(await response.read()))
                assert image.size[0] <= 200
                assert image.size[1] <= 200
        return web.Response()

    app = web.Application()
    app.add_routes([web.post("/", handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", "8000")
    await site.start()

    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/cat.jpg",
        "size": (200, 200),
        "callback_url": "http://localhost:8000",
    }
    output = await client.execute_workflow(
        "image-thumbnail", arg, id=f"{uuid4()}", task_queue="default"
    )
    assert "file" in output


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


async def test_image_detail_basic():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/cat.jpg",
        "language": "Simplified Chinese",
    }
    output = await client.execute_workflow(
        "image-detail-basic", arg, id=f"{uuid4()}", task_queue="default"
    )
    assert "title" in output


async def test_video_sprite():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/SampleVideo_720x480_10mb.mp4",
        "interval": 1.5,
        "layout": [6, 5],
        "width": 1000,
    }
    output = await client.execute_workflow(
        "video-sprite", arg, id=f"{uuid4()}", task_queue="default"
    )
    assert len(output["files"]) == 2


async def test_video_transcode():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/SampleVideo_720x480_10mb.mp4",
        "video-codec": "hevc",
        "audio-codec": "aac",
        "container": "mkv",
    }
    output = await client.execute_workflow(
        "video-transcode", arg, id=f"{uuid4()}", task_queue="default"
    )
    assert "file" in output


async def test_audio_waveform():
    client = await Client.connect(os.environ["TEMPORAL_SERVER_HOST"])
    arg = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/SampleVideo_720x480_10mb.mp4",
        "num_samples": 1000,
    }
    output = await client.execute_workflow(
        "audio-waveform", arg, id=f"{uuid4()}", task_queue="default"
    )
    assert len(output["waveform"]) == 1000
    assert max(output["waveform"]) == 1.0
