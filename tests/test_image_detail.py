import pytest
import openai

import media_workflow.activities
from media_workflow.activities.image_detail import (
    _image_detail,
    _image_detail_basic,
    ImageDetailParams,
    ImageDetailBasicParams,
)
import media_workflow
import json
import io


@pytest.fixture
def mock_openai_chatcompletion(monkeypatch):
    """Monkeypatch openai package to prevent useless api calls."""

    # Create a mock async function that simulates `openai.chat.completions.create`
    async def mock_create(*args, **kwargs):
        # Use different response according to system prompt
        system_prompt: str = kwargs["messages"][0]["content"]

        if system_prompt.startswith(
            "You are an assistant skilled at image understanding."
        ):
            test_detail_response = {
                "title": "image-detail-title",
                "description": "image-detail-description",
                "main_category": "general",
                "sub_category": "general",
                "tags": {"aspect": ["tag"]},
            }
        elif system_prompt.startswith(
            "You are an assistant skilled at image description."
        ):
            test_detail_response = {"aspect": "content"}
        elif system_prompt.startswith("从图像中提取一个标题和详细描述。"):
            test_detail_response = {"title": "标题", "description": "描述"}
        elif system_prompt.startswith(
            "Extract a title and a detailed description from the image."
        ):
            test_detail_response = {
                "title": "image-detail-basic-title",
                "description": "image-detail-basic-description",
            }
        elif system_prompt.startswith(
            "根据以下预定义的方面从图像中提取标签"
        ) or system_prompt.startswith(
            "Extract tags from the image according to some predefined aspects."
        ):
            test_detail_response = {"aspect": ["tag"]}
        elif system_prompt.startswith(
            "根据一些预定义的方面，从图像中提取详细描述"
        ) or system_prompt.startswith(
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
            choices = [
                MockChoice(
                    message=MockMessage(content=json.dumps(test_detail_response))
                )
            ]

        return MockResponse()

    def mock_llm():
        client = openai.AsyncOpenAI(api_key="sk-123")

        monkeypatch.setattr(client.chat.completions, "create", mock_create)

        return client

    monkeypatch.setattr(media_workflow.activities.utils, "llm", mock_llm)


@pytest.fixture
def mock_openfile(monkeypatch):
    # Create a file-like object (empty file)
    empty_file = io.BytesIO(b"")

    # Use monkeypatch to replace the open function
    monkeypatch.setattr("builtins.open", lambda file, mode: empty_file)


@pytest.mark.asyncio
async def test_image_detail(mock_openai_chatcompletion, mock_openfile):
    params = ImageDetailParams(file="")
    result = await _image_detail(params)

    assert result.title == "image-detail-title"
    assert result.description == "image-detail-description"


@pytest.mark.asyncio
async def test_image_detail_basic(mock_openai_chatcompletion, mock_openfile):
    params = ImageDetailBasicParams(file="")
    result = await _image_detail_basic(params)

    assert result.title == "image-detail-basic-title"
    assert result.description == "image-detail-basic-description"


@pytest.mark.asyncio
async def test_image_detail_basic_zh(mock_openai_chatcompletion, mock_openfile):
    params = ImageDetailBasicParams(file="", language="zh-CN")
    result = await _image_detail_basic(params)

    assert result.title == "标题"
    assert result.description == "描述"
