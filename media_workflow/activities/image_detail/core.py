import asyncio
from base64 import b64encode

import json_repair
from temporalio import activity

from media_workflow.activities.image_detail.prompts import (
    prompt_image_detail_basic_details,
    prompt_image_detail_basic_main,
    prompt_image_detail_basic_tags,
    prompt_image_detail_detailed_description,
    prompt_image_detail_main,
)
from media_workflow.activities.image_detail.types import (
    ImageDetailBasicMainResponse,
    ImageDetailBasicParams,
    ImageDetailFinalResponse,
    ImageDetailMainResponse,
    ImageDetailParams,
    validate_detailed_description,
    validate_tags,
)
from media_workflow.activities.utils import llm


async def _image_detail(params: ImageDetailParams) -> ImageDetailFinalResponse:
    """Get image structured description."""

    with open(params.file, "rb") as file:
        encoded_string = b64encode(file.read()).decode("utf-8")
        b64image = f"data:image/png;base64,{encoded_string}"

    client = llm()

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
    main_response = ImageDetailMainResponse(**repaired_response)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": prompt_image_detail_detailed_description(
                    params, main_response
                ),
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
        title=main_response.title,
        description=main_response.description,
        tags=[tag for tag_list in main_response.tags.values() for tag in tag_list],
        detailed_description=[
            {key: value} for key, value in detailed_description.items()
        ],
    )


@activity.defn(name="image-detail")
async def image_detail(params: ImageDetailParams) -> ImageDetailFinalResponse:
    """`image-detail` activity wrapper."""

    return await _image_detail(params)


async def _image_detail_basic(
    params: ImageDetailBasicParams,
) -> ImageDetailFinalResponse:
    """Get image structured description with lightweight model."""

    with open(params.file, "rb") as file:
        encoded_string = b64encode(file.read()).decode("utf-8")
        b64image = f"data:image/png;base64,{encoded_string}"

    client = llm()

    model_name = (
        "qwen2-vl-7b-instruct"
        if params.model_type == "public"
        else "minicpm-v:8b-2.6-q4_K_S"
    )

    main_fut = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": prompt_image_detail_basic_main(params),
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

    detail_fut = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": prompt_image_detail_basic_details(params),
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

    tags_fut = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": prompt_image_detail_basic_tags(params)},
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

    main_resp, detail_resp, tags_resp = await asyncio.gather(
        main_fut, detail_fut, tags_fut
    )

    main_resp = json_repair.loads(main_resp.choices[0].message.content)
    detail_resp = json_repair.loads(detail_resp.choices[0].message.content)
    tags_resp = json_repair.loads(tags_resp.choices[0].message.content)

    main_resp = ImageDetailBasicMainResponse(**main_resp)

    tags = validate_tags(tags_resp)
    detailed_description = validate_detailed_description(detail_resp)

    return ImageDetailFinalResponse(
        title=main_resp.title,
        description=main_resp.description,
        tags=[tag for tag_list in tags.values() for tag in tag_list],
        detailed_description=[
            {key: value} for key, value in detailed_description.items()
        ],
    )


@activity.defn(name="image-detail-basic")
async def image_detail_basic(
    params: ImageDetailBasicParams,
) -> ImageDetailFinalResponse:
    """`image-detail-basic` activity wrapper."""

    return await _image_detail_basic(params)
