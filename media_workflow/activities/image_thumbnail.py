import os
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

import pyvips
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class ImageThumbnailParams(BaseModel):
    file: Path
    size: tuple[int, int] | None = None


@instrument
@activity.defn
async def image_thumbnail(params: ImageThumbnailParams) -> Path:
    thumbnail = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"])) / f"{uuid4()}.png"
    pyvips.Image.thumbnail(params.file, params.size[0]).write_to_file(thumbnail)  # type: ignore
    assert thumbnail.exists()
    return thumbnail
