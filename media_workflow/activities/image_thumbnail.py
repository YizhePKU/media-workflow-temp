from pathlib import Path

from PIL import Image
from pydantic import BaseModel
from temporalio import activity

from media_workflow.imutils import imread, imwrite
from media_workflow.trace import instrument


class ImageThumbnailParams(BaseModel):
    file: Path
    size: tuple[int, int] | None = None


@instrument
@activity.defn
async def image_thumbnail(params: ImageThumbnailParams) -> Path:
    image = imread(params.file)
    if size := params.size:
        image.thumbnail(size, resample=Image.Resampling.LANCZOS)
    return imwrite(image)
