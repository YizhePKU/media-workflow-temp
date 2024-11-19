import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import aiohttp
    import ffmpeg
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
async def image_thumbnail(params) -> str:
    key = f"{uuid4()}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(params["file"]) as response:
            image = Image.open(BytesIO(await response.read()))
    if size := params.get("size"):
        image.thumbnail(size)
    return upload(key, image2png(image))


@activity.defn
async def pdf_thumbnail(params) -> str:
    key = f"{uuid4()}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(params["file"]) as response:
            with pymupdf.Document(stream=await response.read()) as doc:
                image = page2image(doc[0])
    if size := params.get("size"):
        image.thumbnail(size)
    return upload(key, image2png(image))


@activity.defn
async def image_detail(params) -> dict:
    headers = {"Authorization": f"Bearer {os.environ["DIFY_IMAGE_DETAIL_KEY"]}"}
    json = {
        "inputs": {
            "language": params["language"],
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": params["file"],
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
async def image_detail_basic(params) -> dict:
    headers = {"Authorization": f"Bearer {os.environ["DIFY_IMAGE_DETAIL_BASIC_KEY"]}"}
    json = {
        "inputs": {
            "language": params["language"],
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": params["file"],
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


@activity.defn
async def video_sprite(params) -> list[str]:
    with TemporaryDirectory() as dir:
        stream = ffmpeg.input(params["file"])

        if interval := params.get("interval"):
            expr = f"floor((t - prev_selected_t) / {interval})"
            stream = stream.filter("select", expr=expr)

        if layout := params.get("layout"):
            stream = stream.filter("tile", layout=f"{layout[0]}x{layout[1]}")

        stream = stream.filter(
            "scale", width=params.get("width", -1), height=params.get("height", -1)
        )

        filename = f"{dir}/%03d.png"
        if count := params.get("count"):
            stream = stream.output(filename, fps_mode="passthrough", vframes=count)
        else:
            stream = stream.output(filename, fps_mode="passthrough")

        stream.run()

        paths = list(Path(dir).iterdir())
        paths.sort(key=lambda p: int(p.stem))
        result = []
        for path in paths:
            with open(path, "rb") as file:
                result.append(upload(path.name, file.read()))
        return result
