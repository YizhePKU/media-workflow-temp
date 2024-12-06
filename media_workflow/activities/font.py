import os
from inspect import cleandoc
from typing import BinaryIO

import aiohttp
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from temporalio import activity

from media_workflow.utils import imwrite

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


def thumbnail(font: str | BinaryIO, size, font_size) -> Image.Image:
    """Generate a thumbnail for the font."""
    margin = int(font_size * 0.5)
    spacing = int(font_size * 0.25)

    if supports_chinese(TTFont(font, fontNumber=0)):
        sample = CHINESE_SAMPLE
    else:
        sample = ENGLISH_SAMPLE

    font.seek(0)
    font = ImageFont.truetype(font, size=font_size)

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


def metadata(font: TTFont, language: str):
    """Extract font metadata."""
    platform_id = 3  # Microsoft
    encoding_id = 1  # Unicode BMP
    if language == "Simplified Chinese":
        language_id = 2052  # Simplified Chinese
    elif language == "English":
        language_id = 1033  # English
    else:
        raise Exception(f"unsupported language: {language}")

    indices = {
        "copyright_notice": 0,
        "font_family": 1,
        "font_subfamily": 2,
        "identifier": 3,
        "full_name": 4,
        "version": 5,
        "postscript_name": 6,
        "trademark": 7,
        "manufacturer": 8,
        "designer": 9,
        "description": 10,
        "vendor_url": 11,
        "designer_url": 12,
        "license_description": 13,
        "license_url": 14,
        "typographic_family": 16,
        "typographic_subfamily": 17,
    }
    meta = {}
    for key, index in indices.items():
        if record := font["name"].getName(index, platform_id, encoding_id, language_id):
            meta[key] = record.toStr()
        else:
            meta[key] = None

    meta["kerning"] = "kern" in font
    meta["variable"] = "fvar" in font
    meta["chinese"] = supports_chinese(font)

    try:
        height = font["hhea"].lineGap + font["hhea"].ascent - font["hhea"].descent
        meta["line_height"] = (height / font["head"].unitsPerEm) * 16
    except Exception as e:
        meta["line_height"] = None

    try:
        meta["sx_height"] = font["OS/2"].sxHeight
    except:
        meta["sx_height"] = None

    return meta


@activity.defn(name="font-thumbnail")
async def font_thumbnail(params) -> str:
    image = thumbnail(
        params["file"],
        size=params.get("size", (800, 600)),
        font_size=params.get("font_size", 200),
    )
    return imwrite(image)


@activity.defn(name="font-metadata")
async def font_metadata(params) -> str:
    return metadata(
        TTFont(params["file"], fontNumber=0),
        language=params.get("language", "English"),
    )


@activity.defn(name="font-detail")
async def font_detail(params) -> dict:
    headers = {"Authorization": f"Bearer {os.environ["DIFY_FONT_DETAIL_KEY"]}"}
    json = {
        "inputs": {
            "language": params["language"],
            "basic_info": params["basic_info"],
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": params["file"],
            },
        },
        "user": os.environ["DIFY_USER"],
        "response_mode": "blocking",
    }
    async with aiohttp.ClientSession() as session:
        url = f"{os.environ["DIFY_ENDPOINT_URL"]}/workflows/run"
        async with session.post(url, headers=headers, json=json) as r:
            r.raise_for_status()
            result = await r.json()
    assert result["data"]["status"] == "succeeded"
    output = result["data"]["outputs"]

    assert isinstance(output["description"], str)
    assert isinstance(output["tags"], str)
    assert isinstance(output["font_category"], str)
    assert isinstance(output["stroke_characteristics"], str)
    assert isinstance(output["historical_period"], str)
    return output
