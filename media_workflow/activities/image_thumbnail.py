import os
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

import pyvips
from psd_tools import PSDImage
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class ImageThumbnailParams(BaseModel):
    file: Path
    size: tuple[int, int] = (1024, 1024)


@instrument
@activity.defn
async def image_thumbnail(params: ImageThumbnailParams) -> Path:
    thumbnail = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"])) / f"{uuid4()}.jpeg"

    # pyvips supports PSD via ImageMagick, but it uses too much memory when processing PSD with a lot of layers. We'll
    # use psd-tools instead, which can composite image layers much more efficiently (hopefully). On the other hand,
    # psd-tools pulls in a lot of dependencies that I've been trying to avoid.
    if params.file.suffix in [".psd", ".psb"]:
        image = PSDImage.open(params.file).composite()
        assert image is not None
        image.thumbnail(params.size)
        image.convert("RGB").save(thumbnail)
    else:
        pyvips.Image.thumbnail(params.file, params.size[0]).write_to_file(thumbnail)  # type: ignore

    assert thumbnail.exists()
    return thumbnail
