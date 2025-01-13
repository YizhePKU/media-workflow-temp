from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.image import imread
from pylette.color_extraction import extract_colors


def rgb2hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


class ImageColorPaletteParams(BaseModel):
    file: Path
    count: int = 10


Entry = TypedDict("Entry", {"color": str, "frequency": float})


@instrument
@activity.defn
async def image_color_palette(params: ImageColorPaletteParams) -> list[Entry]:
    image = imread(params.file)
    palette = extract_colors(image.convert("RGB"), params.count)
    return [{"color": rgb2hex(color.rgb), "frequency": color.freq} for color in palette]
