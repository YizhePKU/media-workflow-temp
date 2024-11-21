from inspect import cleandoc
from typing import BinaryIO

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

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


def supports_chinese(font: TTFont) -> bool:
    """Check if the font supports Chinese characters."""
    cmap = font.getBestCmap()
    return all(ord(char) in cmap for char in CHINESE_SAMPLE if not char.isspace())


def preview(font: str | BinaryIO, size, font_size) -> Image.Image:
    """Generate a preview image for the font."""
    margin = int(font_size * 0.5)
    spacing = int(font_size * 0.25)

    if supports_chinese(TTFont(font)):
        sample = CHINESE_SAMPLE
    else:
        sample = ENGLISH_SAMPLE

    font.seek(0)
    font = ImageFont.FreeTypeFont(font, size=font_size)

    # Calculate how large the image needs to be.
    bbox = ImageDraw.Draw(Image.new("RGB", (0, 0))).multiline_textbbox(
        (margin, 0), sample, font=font, spacing=spacing
    )
    width = bbox[2] + margin
    height = bbox[3] + spacing

    image = Image.new("RGB", (width, height), "white")
    ImageDraw.ImageDraw(image).multiline_text(
        (margin, 0),
        sample,
        font=font,
        spacing=spacing,
        fill="black",
    )
    if size:
        image.thumbnail(size, resample=Image.LANCZOS)
    return image
