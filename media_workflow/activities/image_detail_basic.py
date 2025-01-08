from pathlib import Path
from typing import Literal

import jinja2
from pydantic import BaseModel, RootModel
from temporalio import activity

from media_workflow.llmutils import llm

env = jinja2.Environment(loader=jinja2.PackageLoader("media_workflow"), autoescape=False)  # noqa: S701


class ImageDetailBasicParams(BaseModel):
    file: Path
    language: Literal["zh-CN", "en-US"] = "en-US"
    model_type: Literal["public", "private"] = "public"


class ImageDetailBasicMainResponse(BaseModel):
    title: str
    description: str


@activity.defn
async def image_detail_basic_main(params: ImageDetailBasicParams) -> ImageDetailBasicMainResponse:
    match params.language:
        case "zh-CN":
            prompt = env.get_template("image_detail_basic/zh/main.md").render()
        case "en-US":
            prompt = env.get_template("image_detail_basic/en/main.md").render()

    match params.model_type:
        case "public":
            model = "qwen2-vl-7b-instruct"
        case "private":
            model = "minicpm-v:8b-2.6-q4_K_S"

    return await llm(model=model, prompt=prompt, image=params.file, result_type=ImageDetailBasicMainResponse)


ImageDetailBasicDetailsResponse = RootModel[dict[str, str | None]]


@activity.defn
async def image_detail_basic_details(params: ImageDetailBasicParams) -> ImageDetailBasicDetailsResponse:
    match params.language:
        case "zh-CN":
            prompt = env.get_template("image_detail_basic/zh/details.md").render()
        case "en-US":
            prompt = env.get_template("image_detail_basic/en/details.md").render()

    match params.model_type:
        case "public":
            model = "qwen2-vl-7b-instruct"
        case "private":
            model = "minicpm-v:8b-2.6-q4_K_S"

    return await llm(model=model, prompt=prompt, image=params.file, result_type=ImageDetailBasicDetailsResponse)


ImageDetailBasicTagsResponse = RootModel[dict[str, list[str]]]


@activity.defn
async def image_detail_basic_tags(params: ImageDetailBasicParams) -> ImageDetailBasicTagsResponse:
    match params.language:
        case "zh-CN":
            prompt = env.get_template("image_detail_basic/zh/tags.md").render()
        case "en-US":
            prompt = env.get_template("image_detail_basic/en/tags.md").render()

    match params.model_type:
        case "public":
            model = "qwen2-vl-7b-instruct"
        case "private":
            model = "minicpm-v:8b-2.6-q4_K_S"

    return await llm(model=model, prompt=prompt, image=params.file, result_type=ImageDetailBasicTagsResponse)
