import functools
from datetime import timedelta
from io import BytesIO
from typing import Tuple
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import requests
    from PIL.Image import Image
    from psd_tools import PSDImage

    from media_workflow.s3 import upload


@workflow.defn(name="adobe-photoshop-thumbnail")
class Workflow:
    @workflow.run
    async def run(self, params) -> str:
        timeout = timedelta(seconds=60)
        start = functools.partial(
            workflow.start_activity, start_to_close_timeout=timeout
        )
        url = await start("psd_thumbnail", args=[params["file"], params.get("size")])
        return {"file": url}


def image2png(image: Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


@activity.defn
async def psd_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    psd = PSDImage.open(BytesIO(requests.get(url).content))
    image = psd.thumbnail() if psd.has_thumbnail() else psd.composite()
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))
