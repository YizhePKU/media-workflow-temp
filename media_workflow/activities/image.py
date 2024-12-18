from dataclasses import dataclass
from typing import Tuple

from PIL import Image
from temporalio import activity

from media_workflow.activities.utils import get_datadir
from media_workflow.utils import imread, imwrite
from pylette.color_extraction import extract_colors


@dataclass
class ThumbnailParams:
    file: str
    size: Tuple[int, int] | None = None


@activity.defn(name="image-thumbnail")
async def thumbnail(params: ThumbnailParams) -> str:
    image = imread(params.file)
    if params.size is not None:
        image.thumbnail(params.size, resample=Image.LANCZOS)
    return imwrite(image, datadir=get_datadir())


def rgb2hex(rgb: list[int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


@dataclass
class ColorPaletteParams:
    file: str
    count: int = 10


@activity.defn(name="image-color-palette")
async def color_palette(params: ColorPaletteParams) -> list:
    image = imread(params.file)
    palette = extract_colors(image.convert("RGB"), params.count)
    return [{"color": rgb2hex(color.rgb), "frequency": color.freq} for color in palette]
