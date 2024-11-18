from io import BytesIO

import requests
from PIL import Image

from media_workflow.workflows.adobe_psd_thumbnail import psd2png


async def test_psd2png():
    url = "https://sunyizhe.s3.us-west-002.backblazeb2.com/%E5%BC%B9%E6%A1%8612.psd"
    png_url = await psd2png(url, size=(200, 200))
    png_bytes = requests.get(png_url).content
    _image = Image.open(BytesIO(png_bytes))
