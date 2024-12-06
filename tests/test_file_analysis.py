from uuid import uuid4

import pytest

from media_workflow.activities import download
from media_workflow.utils import imread
from media_workflow.worker import get_client

images = ["https://f002.backblazeb2.com/file/sunyizhe/water-girl.jpg"]


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
