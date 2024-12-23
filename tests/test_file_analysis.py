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
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/flowers.exr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/golden-gate.exr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/hackson.heic",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.psd",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.svg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/water-girl.jpeg",
]
videos = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.mp4",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/dream.mkv",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/dream.webm",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/ocean.rm",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.avi",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/surfing.ts",
]
audios = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/reflection.mp3",
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
]
models = []
fonts = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/NotoSansCJK-Regular.ttc",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/comic-sans.ttf",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/noto-condensed-extrabold-italic.ttf",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/yahei.ttf",
]

if os.environ.get("MEDIA_WORKFLOW_TEST_LARGE", False):
    images += [
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/float.tiff",
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.jpeg",
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.psd",
    ]
    videos += [
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/MuseDam.mp4",
    ]
    documents += [
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.pptx",
    ]
    audios += [
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/resurrections.flac",
    ]

if os.environ.get("MEDIA_WORKFLOW_TEST_C4D", False):
    models += [
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/chart.c4d",
        "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/tree.c4d",
    ]
    if os.environ.get("MEDIA_WORKFLOW_TEST_LARGE", False):
        models += [
            "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/moist.c4d",
            "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/megapolis.c4d"
            "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/suitcase.c4d",
        ]

if os.environ.get("MEDIA_WORKFLOW_TEST_SMALL", False):
    images = [images[0]]
    videos = [videos[0]]
    audios = [audios[0]]
    documents = [documents[0]]
    fonts = [fonts[0]]
    if models:
        models = [models[0]]


async def test_streaming_via_update():
    client = await get_client()
    params = {
        "file": images[0],
        "activities": ["image-thumbnail"],
        "params": {
            "image-thumbnail": {
                "size": [400, 400],
            },
        },
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
        "params": {
            "image-thumbnail": {
                "size": [400, 400],
            },
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    image = imread(await download(result["result"]["image-thumbnail"]))
    assert image.mode == "RGB"
    assert image.size[0] <= 400
    assert image.size[1] <= 400


@pytest.mark.parametrize("file", images)
async def test_image_detail(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["image-detail"],
        "params": {
            "image-detail": {
                "language": "zh-CN",
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert "image-detail" in result["result"]


@pytest.mark.parametrize("file", images)
async def test_image_detail_basic(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["image-detail-basic"],
        "params": {
            "image-detail-basic": {
                "language": "zh-CN",
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert "image-detail-basic" in result["result"]


@pytest.mark.parametrize("file", images)
async def test_image_color_palette(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["image-color-palette"],
        "params": {
            "image-color-palette": {
                "count": 5,
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert len(result["result"]["image-color-palette"]) == 5


@pytest.mark.parametrize("file", documents)
async def test_document_thumbnail(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["document-thumbnail"],
        "params": {
            "document-thumbnail": {
                "size": [800, 600],
                "pages": [0],
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert len(result["result"]["document-thumbnail"]) == 1


@pytest.mark.parametrize("file", fonts)
async def test_font_thumbnail(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["font-thumbnail"],
        "params": {
            "font-thumbnail": {
                "size": [400, 400],
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    image = imread(await download(result["result"]["font-thumbnail"]))
    assert image.mode == "RGB"
    assert image.size[0] <= 400
    assert image.size[1] <= 400


@pytest.mark.parametrize("file", fonts)
async def test_font_metadata(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["font-metadata"],
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert "font_family" in result["result"]["font-metadata"]


@pytest.mark.parametrize("file", fonts)
async def test_font_detail(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["font-detail"],
        "params": {
            "font-detail": {
                "language": "zh-CN",
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    description = result["result"]["font-detail"]["description"]
    assert not description.isascii()


@pytest.mark.parametrize("file", videos)
async def test_video_metadata(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["video-metadata"],
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert isinstance(result["result"]["video-metadata"]["fps"], float)


@pytest.mark.parametrize("file", videos)
async def test_video_sprite(file):
    client = await get_client()
    params = {
        "file": file,
        "activities": ["video-sprite"],
        "params": {
            "video-sprite": {
                "count": 2,
                "layout": [5, 4],
                "width": 200,
            },
        },
    }
    result = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    assert len(result["result"]["video-sprite"]["files"]) == 2
    assert result["result"]["video-sprite"]["width"] == 200
    image = imread(await download(result["result"]["video-sprite"]["files"][0]))
    assert image.size[0] <= 1000


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
    await download(result["result"]["video-transcode"])


@pytest.mark.parametrize("file", audios)
async def test_audio_waveform(file):
    client = await get_client()
    arg = {
        "file": file,
        "activities": ["audio-waveform"],
        "params": {
            "audio-waveform": {
                "num_samples": 1000,
            }
        },
    }
    result = await client.execute_workflow(
        "file-analysis", arg, id=f"{uuid4()}", task_queue="media"
    )
    waveform = result["result"]["audio-waveform"]
    assert len(waveform) == 1000
    assert max(waveform) == 1.0


@pytest.mark.parametrize("model", models)
async def test_c4d_preview(model):
    client = await get_client()
    arg = {
        "file": model,
        "activities": ["c4d-preview"],
    }
    result = await client.execute_workflow(
        "file-analysis", arg, id=f"{uuid4()}", task_queue="media"
    )
    assert "gltf" in result["result"]["c4d-preview"]
    imread(await download(result["result"]["c4d-preview"]["png"]))
