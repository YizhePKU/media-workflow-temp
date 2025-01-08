from pathlib import Path
from typing import Literal

import jinja2
from pydantic import BaseModel, RootModel
from temporalio import activity

from media_workflow.utils.llm import get_category_tree, get_description_aspects, language_to_name, llm

env = jinja2.Environment(loader=jinja2.PackageLoader("media_workflow"), autoescape=False)  # noqa: S701


class ImageDetailMainParams(BaseModel):
    file: Path
    language: Literal["zh-CN", "en-US"] = "en-US"
    industries: list[str] = []


class ImageDetailMainResponse(BaseModel):
    title: str
    description: str
    main_category: str
    sub_category: str
    tags: dict[str, list[str]]


@activity.defn
async def image_detail_main(params: ImageDetailMainParams) -> ImageDetailMainResponse:
    prompt = env.get_template("image_detail/main.md").render(
        language=language_to_name(params.language),
        category_tree=get_category_tree(params.industries),
    )
    return await llm(model="gpt-4o", prompt=prompt, image=params.file, result_type=ImageDetailMainResponse)


class ImageDetailDetailsParams(BaseModel):
    file: Path
    main_category: str
    sub_category: str
    language: Literal["zh-CN", "en-US"] = "en-US"


ImageDetailDetailsResponse = RootModel[dict[str, str | None]]


@activity.defn
async def image_detail_details(params: ImageDetailDetailsParams) -> ImageDetailDetailsResponse:
    aspects = get_description_aspects(params.main_category, params.sub_category)
    prompt = env.get_template("image_detail/details.md").render(
        language=language_to_name(params.language),
        aspects=aspects,
    )
    return await llm(model="gpt-4o", prompt=prompt, image=params.file, result_type=ImageDetailDetailsResponse)
