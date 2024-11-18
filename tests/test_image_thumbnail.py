from io import BytesIO

import requests
from PIL import Image

from media_workflow.activities import image_thumbnail


async def test_image_thumbnail():
    input = "https://sunyizhe.s3.us-west-002.backblazeb2.com/%E5%BC%B9%E6%A1%8612.psd"
    output = await image_thumbnail(input, size=(200, 200))
    image = Image.open(BytesIO(requests.get(output).content))
    assert image.size[0] <= 200
    assert image.size[1] <= 200
