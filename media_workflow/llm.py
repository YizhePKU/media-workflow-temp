import os

from openai import AsyncOpenAI


def client() -> AsyncOpenAI:
    """
    Get llm client.
    Currently it should use litellm proxy server.
    """
    openai_client = AsyncOpenAI(
        base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"]
    )

    return openai_client
