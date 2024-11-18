import functools
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import requests
    from PIL.Image import Image
    from psd_tools import PSDImage

    from media_workflow.s3 import upload


@workflow.defn(name="adobe-psd-thumbnail")
class PsdThumbnail:
    """Generate a PNG thumbnail from a PSD file.

    Params:
        url: URL for the PSD file
        callback: (optional) URL to post the return values

    Returns:
        url: URL for the generated PNG file
    """

    @workflow.run
    async def run(self, params) -> str:
        timeout = timedelta(seconds=60)
        start = functools.partial(
            workflow.start_activity, start_to_close_timeout=timeout
        )

        png_url = await start("psd2png", params["url"])
        if params["callback"] is not None:
            await start("callback", args=[params["callback"], png_url])
        return png_url


def image2png(image: Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


@activity.defn
async def psd2png(url: str) -> str:
    psd_bytes = requests.get(url).content
    psd = PSDImage.open(BytesIO(psd_bytes))
    image = psd.composite()
    png_bytes = image2png(image)
    key = str(uuid4())
    return upload(key, png_bytes)


@activity.defn
async def callback(url: str, data):
    requests.post(url, data=data)
