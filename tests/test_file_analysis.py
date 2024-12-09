import os
import tempfile
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
import pytest

from media_workflow.utils import imread
from media_workflow.worker import get_client


def url2ext(url) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


async def download(url):
    dir = tempfile.gettempdir()
    filename = str(uuid4()) + url2ext(url)
    path = os.path.join(dir, filename)
    with open(path, "wb") as file:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                async for chunk, _ in response.content.iter_chunks():
                    file.write(chunk)
    return path


images = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/apartment.hdr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/cmyk.jpeg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/cocktail.svg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/fei.psb",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/float.tiff",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/flowers.exr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/golden-gate.exr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/hackson.heic",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.psd",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.svg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/water-girl.jpeg",
    # "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.jpeg",
    # "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.psd",
]
videos = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.mp4",
    # "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/MuseDam.mp4",
]
audios = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/reflection.mp3",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/resurrections.flac",
]
documents = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/bill.cdr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/MuseDam.key",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/dam.docx",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/materials.xlsx",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/multipage.ai",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/nova.key",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.ai",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.eps",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.pdf",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.pptx",
    # "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.pptx",
]
models = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/chart.c4d",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/megapolis.c4d",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/moist.c4d",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/suitcase.c4d",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/tree.c4d",
]
fonts = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/NotoSansCJK-Regular.ttc",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/comic-sans.ttf",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/noto-condensed-extrabold-italic.ttf",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/yahei.ttf",
]


async def test_streaming_via_update():
    client = await get_client()
    params = {
        "file": images[0],
        "activities": ["image-thumbnail"],
        "params": {"image-thumbnail": {"size": [400, 400]}},
    }
    handle = await client.start_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    result = await handle.execute_update("get", "image-thumbnail")
    image = imread(await download(result))
    assert image.mode == "RGB"
    assert image.size[0] <= 400
    assert image.size[1] <= 400


@pytest.mark.parametrize("file", images)
async def test_image_thumbnail(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["image-thumbnail"],
        "params": {"image-thumbnail": {"size": [400, 400]}},
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    image = imread(await download(result["result"]["image-thumbnail"]))
    assert image.mode == "RGB"
    assert image.size[0] <= 400
    assert image.size[1] <= 400


@pytest.mark.skip
@pytest.mark.parametrize("file", images)
async def test_image_detail(file, language):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["image-detail"],
        "params": {
            "image-detail": {
                "language": "Simplified Chinese",
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    title = result["result"]["image-detail"]["title"]
    if language != "English":
        assert not title.isascii()


@pytest.mark.parametrize("file", videos)
async def test_video_transcode(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["video-transcode"],
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    _path = await download(result["result"]["video-transcode"])
