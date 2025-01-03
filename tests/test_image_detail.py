import builtins
import io
import json

import openai
import pytest

from media_workflow.activities.image_detail import (
    ImageDetailDetailsParams,
    ImageDetailParams,
    _image_detail_basic,
    _image_detail_details,
    _image_detail_main,
)
from media_workflow.activities.image_detail.category import (
    INDUSTRY_CATEGORY_MAPPING,
    INDUSTRY_NAME_MAPPING,
    get_category_tree,
)


@pytest.fixture(autouse=True)
def mock_openai_chatcompletion(monkeypatch):
    """Monkeypatch openai package to prevent useless api calls."""

    # Create a mock async function that simulates `openai.chat.completions.create`
    async def mock_create(*args, **kwargs):
        # Use different response according to system prompt
        system_prompt: str = kwargs["messages"][0]["content"]

        if system_prompt.startswith("You are an assistant skilled at image understanding."):
            test_detail_response = {
                "title": "image-detail-title",
                "description": "image-detail-description",
                "main_category": "general",
                "sub_category": "general",
                "tags": {"aspect": ["tag"]},
            }
        elif system_prompt.startswith("You are an assistant skilled at image description."):
            test_detail_response = {"aspect": "content"}
        elif system_prompt.startswith("从图像中提取一个标题和详细描述。"):
            test_detail_response = {"title": "标题", "description": "描述"}
        elif system_prompt.startswith("Extract a title and a detailed description from the image."):
            test_detail_response = {
                "title": "image-detail-basic-title",
                "description": "image-detail-basic-description",
            }
        elif system_prompt.startswith("根据以下预定义的方面从图像中提取标签") or system_prompt.startswith(
            "Extract tags from the image according to some predefined aspects."
        ):
            test_detail_response = {"aspect": ["tag"]}
        elif system_prompt.startswith("根据一些预定义的方面，从图像中提取详细描述") or system_prompt.startswith(
            "Extract detailed descriptions from the image according to"
        ):
            test_detail_response = {"aspect": "description"}
        else:
            test_detail_response = {}

        class MockMessage:
            content: str

            def __init__(self, content: str):
                self.content = content

        class MockChoice:
            message: MockMessage

            def __init__(self, message: MockMessage):
                self.message = message

        class MockResponse:
            choices = [MockChoice(message=MockMessage(content=json.dumps(test_detail_response)))]

        return MockResponse()

    def mock_llm():
        client = openai.AsyncOpenAI(api_key="sk-123")

        monkeypatch.setattr(client.chat.completions, "create", mock_create)

        return client

    monkeypatch.setattr("media_workflow.llm.client", mock_llm)


@pytest.fixture
def mock_openfile(monkeypatch):
    def mock_open(*args, **kwargs):
        return io.BytesIO(b"")

    # Use monkeypatch to replace the open function
    monkeypatch.setattr(builtins, "open", mock_open)


def test_image_detail_category_tree():
    # valid data from backend
    valid_data = [
        {"name": "室内设计", "name_en": "Interior Design"},
        {"name": "建筑设计", "name_en": "Architecture Design"},
        {"name": "服装设计", "name_en": "Fashion Design"},
        {"name": "插画设计", "name_en": "Illustration"},
        {"name": "视觉设计", "name_en": "Graphic Design"},
        {"name": "UI/UX 设计", "name_en": "UI/UX"},
        {"name": "3D 设计", "name_en": "3D"},
        {"name": "游戏设计", "name_en": "Game Design"},
        {"name": "自媒体运营", "name_en": "Social Media"},
        {"name": "摄影", "name_en": "Photography"},
        {"name": "电商", "name_en": "E-commerce"},
        {"name": "互联网", "name_en": "Internet"},
        {"name": "其他", "name_en": "Others"},
    ]

    for data in valid_data:
        assert data["name"] in INDUSTRY_NAME_MAPPING
        assert data["name_en"].lower() in INDUSTRY_CATEGORY_MAPPING

        assert get_category_tree(
            ImageDetailParams(file="", language="en-US", industry=[data["name"]])
        ) == get_category_tree(ImageDetailParams(file="", language="en-US", industry=[data["name_en"]]))


async def test_image_detail(mock_openai_chatcompletion, mock_openfile):
    params = ImageDetailParams(file="")

    main_response = await _image_detail_main(params)

    assert main_response.title == "image-detail-title"
    assert main_response.description == "image-detail-description"

    result = await _image_detail_details(ImageDetailDetailsParams(**params.__dict__, main_response=main_response))

    assert result.title == main_response.title
    assert result.description == main_response.description


async def test_image_detail_basic(mock_openai_chatcompletion, mock_openfile):
    params = ImageDetailParams(file="")
    result = await _image_detail_basic(params, "main")

    assert result.title == "image-detail-basic-title"
    assert result.description == "image-detail-basic-description"


async def test_image_detail_basic_zh(mock_openai_chatcompletion, mock_openfile):
    params = ImageDetailParams(file="", language="zh-CN")
    result = await _image_detail_basic(params, "main")

    assert result.title == "标题"
    assert result.description == "描述"
