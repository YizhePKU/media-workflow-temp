"""Schema definition of image detail tasks."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from media_workflow.schema import Language

ModelType = Literal["public", "private"]


@dataclass
class ImageDetailParams:
    """Basic params of image detail related activities."""

    file: str
    language: Language = "en-US"
    model_type: ModelType = "public"
    industry: list[str] = field(default_factory=list)


class ImageDetailMainResponse(BaseModel):
    """First response of image-detail pipeline.

    Include title, description, main_category, sub_category and tags.
    """

    title: str
    description: str
    main_category: str
    sub_category: str
    tags: dict[str, list[str]]


@dataclass
class ImageDetailDetailsParams(ImageDetailParams):
    """Params of image-detail-details activity."""

    main_response: ImageDetailMainResponse = field(
        default_factory=lambda: ImageDetailMainResponse(
            title="", description="", main_category="", sub_category="", tags={}
        )
    )


class ImageDetailFinalResponse(BaseModel):
    """Final response of image-detail and image-detail-basic pipeline."""

    title: str
    description: str
    tags: list[str]
    detailed_description: list[dict[str, str | None]]


class ImageDetailBasicMainResponse(BaseModel):
    """Main response of image-detail-basic pipeline."""

    title: str
    description: str


def validate_detailed_description(data) -> dict[str, str | None]:
    """Validate format of detailed description.

    Raises:
        ValueError: If data is not dict[str, str].

    """
    if not isinstance(data, dict):
        raise ValueError(f"detailed_description should be a dictionary: {data}")

    for key, value in data.items():
        if not isinstance(key, str):
            raise ValueError(f"detailed_description key should be a string: {data}")
        if value is not None and not isinstance(value, str):
            raise ValueError(f"detailed_description value should be a string: {data}")

    return data


def validate_tags(data) -> dict[str, list[str]]:
    """Validate format of tags.

    Raises:
        ValueError: If data is not dict[str, list[str]].

    """
    if not isinstance(data, dict):
        raise ValueError(f"tags should be a dictionary: {data}")

    for key, value in data.items():
        if not isinstance(key, str):
            raise ValueError(f"tags key should be a string: {data}")
        if not isinstance(value, list):
            raise ValueError(f"tags value should be a list: {data}")
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"tags value should be a list of strings: {data}")

    return data
