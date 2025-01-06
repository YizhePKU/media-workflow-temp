from pathlib import Path

from PIL import Image
from pydantic import BaseModel
from temporalio import activity

from media_workflow.activities.utils import get_datadir
from media_workflow.imutils import imread, imwrite
from media_workflow.trace import instrument
from pylette.color_extraction import extract_colors


class ThumbnailParams(BaseModel):
    file: Path
    size: tuple[int, int] | None = None


@instrument
@activity.defn(name="image-thumbnail")
async def thumbnail(params: ThumbnailParams) -> Path:
    image = imread(params.file)
    if params.size is not None:
        image.thumbnail(params.size, resample=Image.Resampling.LANCZOS)
    return imwrite(image, _dir=get_datadir())


def rgb2hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


class ColorPaletteParams(BaseModel):
    file: Path
    count: int = 10


@instrument
@activity.defn(name="image-color-palette")
async def color_palette(params: ColorPaletteParams) -> list:
    image = imread(params.file)
    palette = extract_colors(image.convert("RGB"), params.count)
    return [{"color": rgb2hex(color.rgb), "frequency": color.freq} for color in palette]
