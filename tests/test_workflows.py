import os
from io import BytesIO
from uuid import uuid4

import requests
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
    image = Image.open(BytesIO(requests.get(output["file"]).content))
    assert image.size[0] <= 200
    assert image.size[1] <= 200
