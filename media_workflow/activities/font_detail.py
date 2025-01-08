from pathlib import Path
from typing import Literal

import jinja2
from pydantic import BaseModel
from temporalio import activity

from media_workflow.trace import instrument
from media_workflow.utils.llm import language_to_name, llm

env = jinja2.Environment(loader=jinja2.PackageLoader("media_workflow"), autoescape=False)  # noqa: S701


class FontDetailParams(BaseModel):
    file: Path
    basic_info: dict
    language: Literal["zh-CN", "en-US"] = "en-US"


class FontDetailResponse(BaseModel):
    description: str
    font_category: str | None = None
    stroke_characteristics: str | None = None
    historical_period: str | None = None
    tags: list[str] = []


@instrument
@activity.defn
async def font_detail(params: FontDetailParams) -> FontDetailResponse:
    prompt = env.get_template("font_detail/main.md").render(language=language_to_name(params.language))
    return await llm(model="gpt-4o-mini", prompt=prompt, image=params.file, result_type=FontDetailResponse)
