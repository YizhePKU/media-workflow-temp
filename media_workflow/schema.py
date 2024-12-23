from typing import Literal

Language = Literal["zh-CN", "en-US"]


def language_to_name(language: Language) -> str:
    """Convert language code to language name."""
    match language:
        case "zh-CN":
            return "Simplified Chinese"
        case _:
            return "English"
