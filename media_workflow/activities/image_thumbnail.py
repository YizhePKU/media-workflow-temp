from pathlib import Path

from PIL import Image
from pydantic import BaseModel
from temporalio import activity

from media_workflow.imutils import imread, imwrite
from media_workflow.trace import instrument


class ImageThumbnailParams(BaseModel):
    file: Path
    size: tuple[int, int] = (1000, 1000)


@instrument
@activity.defn
async def image_thumbnail(params: ImageThumbnailParams) -> Path:
    image = imread(params.file)
    image.thumbnail(params.size, resample=Image.Resampling.LANCZOS)
    return imwrite(image)
