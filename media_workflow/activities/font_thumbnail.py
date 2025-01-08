from inspect import cleandoc
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from temporalio import activity

from media_workflow.activities.utils import get_datadir
from media_workflow.fontutils import supports_chinese
from media_workflow.imutils import imwrite
from media_workflow.trace import instrument

CHINESE_SAMPLE = cleandoc(
    """
    汉体书写信息技术标准相容
    档案下载使用界面简单
    AaBbCc ＡａＢｂＣｃ
    1234567890
    """
)

ENGLISH_SAMPLE = cleandoc(
    """
    ABCDEFGHIJKLMNOPQRSTUVWXYZ
    abcdefghijklmnopqrstuvwxyz
    1234567890
    """
)


class FontThumbnailParams(BaseModel):
    file: Path
    size: tuple[int, int] = (1000, 1000)
    font_size: int = 200


@instrument
@activity.defn
async def font_thumbnail(params: FontThumbnailParams) -> Path:
    margin = int(params.font_size * 0.5)
    spacing = int(params.font_size * 0.25)

    if supports_chinese(TTFont(params.file, fontNumber=0)):
        sample = CHINESE_SAMPLE
    else:
        sample = ENGLISH_SAMPLE

    font = ImageFont.truetype(params.file, size=params.font_size)

    # Calculate how large the image needs to be.
    bbox = ImageDraw.Draw(Image.new("RGB", (0, 0))).multiline_textbbox((margin, 0), sample, font=font, spacing=spacing)
    width = int(bbox[2]) + margin
    height = int(bbox[3]) + spacing

    image = Image.new("RGB", (width, height), "white")
    ImageDraw.ImageDraw(image).multiline_text(
        (margin, 0),
        sample,
        font=font,
        spacing=spacing,
        fill="black",
    )
    if params.size is not None:
        image.thumbnail(params.size, resample=Image.Resampling.LANCZOS)
    return imwrite(image, _dir=get_datadir())
