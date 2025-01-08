from pathlib import Path
from typing import Literal

from fontTools.ttLib import TTFont
from pydantic import BaseModel
from temporalio import activity

from media_workflow.fontutils import supports_chinese
from media_workflow.trace import instrument


class FontMetadataParams(BaseModel):
    file: Path
    language: Literal["zh-CN", "en-US"] = "en-US"


@instrument
@activity.defn(name="font-metadata")
async def font_metadata(params: FontMetadataParams) -> dict:
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
        if record := font["name"].getName(index, platform_id, encoding_id, language_id):  # type: ignore
            meta[key] = record.toStr()
        else:
            meta[key] = None

    meta["kerning"] = "kern" in font
    meta["variable"] = "fvar" in font
    meta["chinese"] = supports_chinese(font)

    try:
        height = font["hhea"].lineGap + font["hhea"].ascent - font["hhea"].descent  # type: ignore
        meta["line_height"] = (height / font["head"].unitsPerEm) * 16  # type: ignore
    except Exception:
        meta["line_height"] = None

    try:
        meta["sx_height"] = font["OS/2"].sxHeight  # type: ignore
    except Exception:
        meta["sx_height"] = None

    return meta
