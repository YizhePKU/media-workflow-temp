import json
from base64 import b64encode
from dataclasses import dataclass
from inspect import cleandoc
from typing import Optional, Tuple

import json_repair
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from temporalio import activity

from media_workflow.activities.utils import get_datadir
from media_workflow.schema import Language, language_to_name
from media_workflow.imutils import imwrite
from media_workflow import llm

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


@dataclass
class ThumbnailParams:
    file: str
    size: Tuple[int, int] = (1000, 1000)
    font_size: int = 200


@activity.defn(name="font-thumbnail")
async def thumbnail(params: ThumbnailParams) -> str:
    margin = int(params.font_size * 0.5)
    spacing = int(params.font_size * 0.25)

    if supports_chinese(TTFont(params.file, fontNumber=0)):
        sample = CHINESE_SAMPLE
    else:
        sample = ENGLISH_SAMPLE

    font = ImageFont.truetype(params.file, size=params.font_size)

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
    if params.size is not None:
        image.thumbnail(params.size, resample=Image.LANCZOS)
    return imwrite(image, datadir=get_datadir())


@dataclass
class MetadataParams:
    file: str
    language: Language = "en-US"


@activity.defn(name="font-metadata")
async def metadata(params: MetadataParams) -> dict:
    platform_id = 3  # Microsoft
    encoding_id = 1  # Unicode BMP
    if params.language == "zh-CN":
        language_id = 2052  # Simplified Chinese
    else:
        # other language are considered as English
        language_id = 1033

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
    font = TTFont(params.file, fontNumber=0)
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
    except Exception:
        meta["line_height"] = None

    try:
        meta["sx_height"] = font["OS/2"].sxHeight
    except Exception:
        meta["sx_height"] = None

    return meta


@dataclass
class DetailParams:
    file: str
    basic_info: dict
    language: Language = "en-US"


class FontDetailResponse(BaseModel):
    description: str
    font_category: Optional[str]
    stroke_characteristics: Optional[str]
    historical_period: Optional[str]
    tags: list[str] = []


@activity.defn(name="font-detail")
async def detail(params: DetailParams) -> dict:
    """Get font detail analysis using LLM."""

    with open(params.file, "rb") as file:
        encoded_string = b64encode(file.read()).decode("utf-8")
        b64image = f"data:image/png;base64,{encoded_string}"

    client = llm.client()

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""You are an assistant skilled at font analysis.
## Guidelines
Input image will contain several characters from one source font file. You should observe the image as detailed as possible, and tell the feature of the providing font. Input also includes the basic information of the font, like name, style or weight, you can refer to them if needed.
Your answer should include description, tags, font category, stroke characteristics and historical period for the target font.
### Description
Basic description of the font, which help designers to choose suitable font. Contain the content only, do not start with something like `this font ...`, and also do not contain the font name.
### Tags
A list of keywords, which can be used to describe target font.
### Font Category
Try to classify the font into correct category
## Format Principles
- Response in JSON format
- Using {language_to_name(params.language)} for value
- Using snake_case for key""",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": json.dumps(params.basic_info)},
                    {
                        "type": "image_url",
                        "image_url": {"url": b64image, "detail": "low"},
                    },
                ],
            },
        ],
        stream=False,
        response_format={"type": "json_object"},
    )

    response = json_repair.loads(response.choices[0].message.content)

    return FontDetailResponse(**response)
