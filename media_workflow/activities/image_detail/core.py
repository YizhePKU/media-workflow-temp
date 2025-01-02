import os
from base64 import b64encode
from typing import Literal

import json_repair
from openai import AsyncOpenAI
from temporalio import activity

from media_workflow.activities.image_detail.prompts import (
    prompt_image_detail_basic_details,
    prompt_image_detail_basic_main,
    prompt_image_detail_basic_tags,
    prompt_image_detail_detailed_description,
    prompt_image_detail_main,
)
from media_workflow.activities.image_detail.schema import (
    ImageDetailBasicMainResponse,
    ImageDetailDetailsParams,
    ImageDetailFinalResponse,
    ImageDetailMainResponse,
    ImageDetailParams,
    validate_detailed_description,
    validate_tags,
)


async def _image_detail_main(params: ImageDetailParams) -> ImageDetailMainResponse:
    """Get image structured description."""
    with open(params.file, "rb") as file:
        encoded_string = b64encode(file.read()).decode("utf-8")
        b64image = f"data:image/png;base64,{encoded_string}"

    client = AsyncOpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": prompt_image_detail_main(params),
            },
            {
                "role": "user",
                "content": [
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

    repaired_response = json_repair.loads(response.choices[0].message.content)
    return ImageDetailMainResponse(**repaired_response)


async def _image_detail_details(
    params: ImageDetailDetailsParams,
) -> ImageDetailFinalResponse:
    with open(params.file, "rb") as file:
        encoded_string = b64encode(file.read()).decode("utf-8")
        b64image = f"data:image/png;base64,{encoded_string}"

    client = AsyncOpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": prompt_image_detail_detailed_description(params),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": b64image,
                            "detail": "low",
                        },
                    }
                ],
            },
        ],
        stream=False,
        response_format={"type": "json_object"},
    )

    detailed_description = json_repair.loads(response.choices[0].message.content)
    detailed_description = validate_detailed_description(detailed_description)

    return ImageDetailFinalResponse(
        title=params.main_response.title,
        description=params.main_response.description,
        tags=[tag for tag_list in params.main_response.tags.values() for tag in tag_list],
        detailed_description=[{key: value} for key, value in detailed_description.items()],
    )


@activity.defn(name="image-detail-main")
async def image_detail_main(params: ImageDetailParams) -> ImageDetailMainResponse:
    """`image-detail-main` activity wrapper."""
    return await _image_detail_main(params)


@activity.defn(name="image-detail-details")
async def image_detail_details(
    params: ImageDetailDetailsParams,
) -> ImageDetailFinalResponse:
    """`image-detail-details` activity wrapper."""
    return await _image_detail_details(params)


async def _image_detail_basic(
    params: ImageDetailParams,
    task: Literal["main", "details", "tags"] = "main",
):
    """Get image structured description with lightweight model."""
    with open(params.file, "rb") as file:
        encoded_string = b64encode(file.read()).decode("utf-8")
        b64image = f"data:image/png;base64,{encoded_string}"

    client = AsyncOpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
    model_name = "qwen2-vl-7b-instruct" if params.model_type == "public" else "minicpm-v:8b-2.6-q4_K_S"

    match task:
        case "main":
            system_prompt = prompt_image_detail_basic_main(params)

        case "details":
            system_prompt = prompt_image_detail_basic_details(params)

        case "tags":
            system_prompt = prompt_image_detail_basic_tags(params)

        case _:
            raise ValueError(f"Unknown task: {task}")

    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": b64image, "detail": "low"},
                    }
                ],
            },
        ],
        stream=False,
    )

    response = json_repair.loads(response.choices[0].message.content)

    match task:
        case "main":
            return ImageDetailBasicMainResponse(**response)
        case "details":
            detailed_description = validate_detailed_description(response)
            return [{key: value} for key, value in detailed_description.items()]
        case "tags":
            tags = validate_tags(response)
            return [tag for tag_list in tags.values() for tag in tag_list]
        case _:
            return {}


@activity.defn(name="image-detail-basic-main")
async def image_detail_basic_main(
    params: ImageDetailParams,
) -> ImageDetailBasicMainResponse:
    """`image-detail-basic-main` activity wrapper."""
    return await _image_detail_basic(params, "main")


@activity.defn(name="image-detail-basic-tags")
async def image_detail_basic_tags(
    params: ImageDetailParams,
) -> list[str]:
    """`image-detail-basic-tags` activity wrapper."""
    return await _image_detail_basic(params, "tags")


@activity.defn(name="image-detail-basic-details")
async def image_detail_basic_details(
    params: ImageDetailParams,
) -> list[dict[str, str | None]]:
    """`image-detail-basic-details` activity wrapper."""
    return await _image_detail_basic(params, "details")
