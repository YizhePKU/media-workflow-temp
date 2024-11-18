import functools
from datetime import timedelta
from io import BytesIO
from typing import Tuple
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import requests
    from PIL import Image

    from media_workflow.s3 import upload


@workflow.defn(name="image-thumbnail")
class ImageThumbnail:
    """Generate a PNG thumbnail from an image.

    If `size` is given, the image will be resized to be no larger than `size`, preserving the
    aspect of the image.

    Params:
        file: URL for the PSD file
        size: (optional) the requested size in pixels, as a 2-tuple: (width, height)

    Returns:
        file: URL for the generated PNG file
    """

    @workflow.run
    async def run(self, params):
        timeout = timedelta(seconds=60)
        start = functools.partial(
            workflow.start_activity, start_to_close_timeout=timeout
        )
        url = await start("image_thumbnail", args=[params["file"], params.get("size")])
        return {"file": url}


def image2png(image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


@activity.defn
async def image_thumbnail(url: str, size: Tuple[int, int] | None) -> str:
    key = f"{uuid4()}.png"
    image = Image.open(requests.get(url).content)
    if size:
        image.thumbnail(size)
    return upload(key, image2png(image))
