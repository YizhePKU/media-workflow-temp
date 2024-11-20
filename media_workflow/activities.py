import math
import os
import subprocess
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import aiohttp
    import ffmpeg
    import numpy as np
    import pymupdf
    from PIL import Image
    from pydub import AudioSegment

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
    async with aiohttp.ClientSession() as session:
        async with session.get(params["file"]) as response:
            image = Image.open(BytesIO(await response.read()))
    if size := params.get("size"):
        image.thumbnail(size)
    return upload(f"{uuid4()}.png", image2png(image))


@activity.defn
async def pdf_thumbnail(params) -> list[str]:
    images = []
    async with aiohttp.ClientSession() as session:
        async with session.get(params["file"]) as response:
            with pymupdf.Document(stream=await response.read()) as doc:
                if pages := params.get("pages"):
                    for i in pages:
                        images.append(page2image(doc[i]))
                else:
                    for page in doc.pages():
                        images.append(page2image(page))
    if size := params.get("size"):
        for image in images:
            image.thumbnail(size)
    return [upload(f"{uuid4()}.png", image2png(image)) for image in images]


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
                result.append(upload(f"{uuid4()}.png", file.read()))
        return result


@activity.defn
async def video_transcode(params) -> str:
    with TemporaryDirectory() as dir:
        stream = ffmpeg.input(params["file"])

        path = Path(f"{dir}/{uuid4()}.{params.get("container", "mp4")}")
        kwargs = {
            "codec:v": params.get("video-codec", "h264"),
            "codec:a": params.get("audio-codec", "libopus"),
        }
        stream = stream.output(str(path), **kwargs)
        stream.run()

        with open(path, "rb") as file:
            return upload(path.name, file.read())


@activity.defn
async def audio_waveform(params) -> list[float]:
    async with aiohttp.ClientSession() as client:
        async with client.get(params["file"]) as r:
            payload = await r.read()
    audio = AudioSegment.from_file(BytesIO(payload))
    data = np.array(audio.get_array_of_samples())

    samples = np.zeros(params["num_samples"])
    step = math.ceil(len(data) / params["num_samples"])
    for i in range(0, len(data), step):
        samples[i // step] = np.max(np.abs(data[i : i + step]))

    # Normalize the data
    samples = samples / np.max(samples)
    return samples.tolist()


@activity.defn
async def convert_to_pdf(params) -> str:
    with TemporaryDirectory() as dir:
        stem = str(uuid4())
        input = f"{dir}/{stem}"
        async with aiohttp.ClientSession() as client:
            async with client.get(params["file"]) as r:
                with open(input, "wb") as file:
                    file.write(await r.read())
        subprocess.run(["soffice", "--convert-to", "pdf", "--outdir", dir, input])
        output = f"{input}.pdf"
        with open(output, "rb") as file:
            return upload(f"{stem}.pdf", file.read())
