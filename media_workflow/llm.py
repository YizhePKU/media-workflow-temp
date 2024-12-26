import os
from typing import Literal

from openai import AsyncOpenAI

Language = Literal["zh-CN", "en-US"]


def client() -> AsyncOpenAI:
    """Get llm client. Currently it should use litellm proxy server."""
    openai_client = AsyncOpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])

    return openai_client


def language_to_name(language: Language) -> str:
    """Convert language code to language name."""
    match language:
        case "zh-CN":
            return "Simplified Chinese"
        case _:
            return "English"
