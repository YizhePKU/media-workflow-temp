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
class Workflow:
    """Generate a PNG thumbnail from a PSD file.

    Params:
        file: URL for the PSD file

    Returns:
        file: URL for the generated PNG file
    """

    @workflow.run
    async def run(self, params) -> str:
        timeout = timedelta(seconds=60)
        start = functools.partial(
            workflow.start_activity, start_to_close_timeout=timeout
        )
        url = await start("psd2png", params["file"])
        return {"file": url}


def image2png(image: Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


@activity.defn
async def psd2png(url: str) -> str:
    key = f"{uuid4()}.png"
    psd = PSDImage.open(BytesIO(requests.get(url).content))
    if psd.has_thumbnail():
        return upload(key, image2png(psd.thumbnail()))
    else:
        return upload(key, image2png(psd.composite()))
