# ruff: noqa: E501

import json
from typing import Literal

from media_workflow.activities.image_detail.category import (
    get_category_tree,
    get_description_aspects,
)

from .schema import (
    ImageDetailDetailsParams,
    ImageDetailParams,
)


# NOTE: intentionally not DRY across modules
def language_to_name(language: Literal["zh-CN", "en-US"]) -> str:
    """Convert language code to language name."""
    match language:
        case "zh-CN":
            return "Simplified Chinese"
        case _:
            return "English"


def prompt_image_detail_main(params: ImageDetailParams) -> str:
    """System prompt for image-detail first step, getting the basic information of the image."""
    category_tree = get_category_tree(params)

    return f"""You are an assistant skilled at image understanding.
## Guidelines
You should try to observe the input image as detailed as possible and try to extract title, tags and category.
### Title
Title is used to summarize the image in less than 10 words. No punctuation mark should be in the title. Using {language_to_name(params.language)}.
### Description
Detailed description of the image. Contain the content only, do not start with something like `this image ...`. Using {language_to_name(params.language)}. If you can see some human-readable characters (like English or Chinese) in the image, please describe them in the description. Furthermore, you should try to tell the font category of these characters as detailed as possible.
### Tags
Tags should be in JSON format, with following keys:
- Theme Identification: Accurately capture the core theme of the material, covering areas such as education, technology, health, etc.
- Emotion Capture: Sensitively perceive the emotional tone conveyed by the material, such as motivational, joyful, sad, etc.
- Style Annotation: Clearly define the visual or linguistic style of the material, including modern, vintage, minimalist, etc.
- Color Analysis: Based on the main colors of the material, select corresponding tags such as blue, red, black and white, etc.
- Scene Description: Describe the environmental background where the material takes place, such as office, outdoor, home, etc.
- Character Analysis: Tag characters in the material based on their roles or features, such as professionals, children, athletes, etc.
- Purpose Clarification: Clearly specify the intended application scenarios of the material, such as advertising, education, social media, etc.
- Technology Identification: Mark the specific technologies applied in the material, such as 3D printing, virtual reality, etc.
- Time Marking: Add corresponding time tags based on the material's relevance to time, such as spring, night, 20th century, etc.
- Trend Tracking: Reflect current trends or hot issues, such as sustainable development, artificial intelligence, etc.
Tagging Principles:
- Highly Relevant: Ensure each tag is closely connected to the content to enhance retrieval accuracy.
- Concise and Clear: Use simple tags for quick user understanding and searchability.
- System Consistency: Use a unified tagging system within the same theme to maintain consistency.
- Diverse Classification: Categorize content from different dimensions to enhance retrieval flexibility and coverage.
Format Principles:
- Each key should be in snake case
- Values (tags) should be in {language_to_name(params.language)}
- If no tag for a key, set the value of the key to an empty
- Examples: `{{"theme_identification": ["标签", ...], "trend_tracking": [], ...}}`
### Category
You should find one best category in the following tree for the image:
```
{json.dumps(category_tree, ensure_ascii=False)}
```
The tree is a 2-layer json, where the key in the first layer is main_category, the key in the second layer is sub_category and the value is the description for the sub_category.
You should find best main_category and corresponding sub_category to describe the image.
### Special Tips for Category
`interface_screenshots` are very tricky to distinguish, you need to obverse the whole image very carefully, and try to avoid affected by the main objects. If the image contains components in website or application, like close button, window border etc., it is very likely to be a screenshots.
## Input
An image.
## Response Example (JSON format)
```
{{"title": "...", "description": "...", "tags": {{"color_schema": ["..."], ...}}, "main_category": "...", "sub_category": "..."}}
```"""


def prompt_image_detail_detailed_description(
    params: ImageDetailDetailsParams,
) -> str:
    """System prompt to generate detailed description in image-detail pipeline."""
    _, sub_category, aspects = get_description_aspects(
        params.main_response.main_category, params.main_response.sub_category
    )

    aspects = "\n".join([f"- {k}" if v is None else f"- {k}: {v}" for k, v in aspects.items()])

    return f"""You are an assistant skilled at image description.
User will input an image of {sub_category}, you should try to describe it in following aspect:
{aspects}
You should response in JSON format, with each aspect as key (in snake_case format), and the concrete description as value.
If you can't describe for an aspect, use `null` as value.
You should try to use {language_to_name(params.language)} in description."""


def prompt_image_detail_basic_main(params: ImageDetailParams) -> str:
    """System prompt for image-detail-basic main result."""
    match params.language:
        case "zh-CN":
            return """从图像中提取一个标题和详细描述。输出应为简体中文。
输出应为 JSON 格式。输出的 JSON 应包含以下键：
- title
- description
标题应以简体中文总结图像内容，用一句简短的单句表示。标题中不应包含标点符号。
描述应为长文本，用于详细描述图像的内容。图像中出现的所有对象都应被描述。如果图像中有任何文字，提到该文字并描述其字体类型。"""

        case _:
            return """Extract a title and a detailed description from the image. The output should be in English.
The output should be in JSON format. The output JSON should contain the following keys:
- title
- description
The title should summarize the image in a short, single sentence using English. No punctuation mark should be in the title.
The description should be a long text that describes the content of the image. All objects that appear in the image should be described. If there're any text in the image, mention the text and the font type of that text.
"""


def prompt_image_detail_basic_tags(params: ImageDetailParams) -> str:
    """System prompt for image-detail-basic tags result."""
    match params.language:
        case "zh-CN":
            return """根据以下预定义的方面从图像中提取标签。输出应为简体中文。

输出格式应为一个JSON对象，包含以下键：
• theme_identification：总结素材的核心主题，例如教育、科技、健康等。
• emotion_capture：总结素材传递的情感基调，例如激励、愉悦、悲伤等。
• style_annotation：总结素材的视觉或语言风格，例如现代、复古、极简等。
• color_analysis：总结素材的主要颜色，例如蓝色、红色、黑白等。
• scene_description：总结素材发生的环境背景，例如办公室、户外、家中等。
• character_analysis：根据角色或特征总结素材中的人物，例如专业人士、儿童、运动员等。
• purpose_clarification：总结素材的预期应用场景，例如广告、教育、社交媒体等。
• technology_identification：总结素材中应用的具体技术，例如3D打印、虚拟现实等。
• time_marking：基于素材与时间的相关性总结时间标签（如适用），例如春天、夜晚、20世纪等。
• trend_tracking：总结当前趋势或热点问题，例如可持续发展、人工智能等。

每个标签的值应为一个JSON列表，包含零个或多个简短的字符串。每个字符串应简要描述图像内容，并使用简体中文编写。仅使用字符串列表，不应包含复杂对象。

不要使用 "无" "null" 等字符串作为标签。
如果提取的值含糊不清或信息量不足，或者该标签不适用于该图像，请将其值设为空列表。
如果提取的值为复杂对象而非字符串，请将其总结为简短的字符串。
如果提取的值过长，请通过总结关键信息进行简化。"""

        case _:
            return """Extract tags from the image according to some predefined aspects.

The output should be a JSON object with the following keys:
- theme_identification: summarize the core theme of the material, such as education, technology, health, etc.
- emotion_capture: summarize the emotional tone conveyed by the material, such as motivational, joyful, sad, etc.
- style_annotation: summarize the visual or linguistic style of the material, such as modern, vintage, minimalist, etc.
- color_analysis: summarize the main colors of the material, such as blue, red, black and white, etc.
- scene_description: summarize the environmental background where the material takes place, such as office, outdoor, home, etc.
- character_analysis: summarize characters in the material based on their roles or features, such as professionals, children, athletes, etc.
- purpose_clarification: summarize the intended application scenarios of the material, such as advertising, education, social media, etc.
- technology_identification: summarize the specific technologies applied in the material, such as 3D printing, virtual reality, etc.
- time_marking: summarize time tags based on the material's relevance to time, if applicable, such as spring, night, 20th century, etc.
- trend_tracking: summarize current trends or hot issues, such as sustainable development, artificial intelligence, etc.

Each tag value should be a JSON list containing zero of more short strings. Each string should briefly describes the image in {{#1730167939128.language#}}. Only use strings inside lists, not complex objects.

If the extracted value is vague or non-informative, or if the tag doesn't apply to this image, set the value to an empty list instead.
If the extracted value is a complex object instead of a string, summarize it in a short string instead.
If the extracted value is too long, shorten it by summarizing the key information."""


def prompt_image_detail_basic_details(params: ImageDetailParams) -> str:
    """System prompt for image-detail-basic detailed description result."""
    match params.language:
        case "zh-CN":
            return """根据一些预定义的方面，从图像中提取详细描述。输出应为简体中文。

输出应为一个包含以下键的JSON对象：
- usage （用途）
- mood （情绪）
- color_scheme （配色方案）
- culture_traits （文化特征）
- industry_domain （行业领域）
- seasonality （季节性）
- holiday_theme （节日主题）

每个值应为用简体中文描述图像的完整且详细的长句。如果无法从图像中提取相关信息，或者结果模糊，请将值设置为null。"""

        case _:
            return """Extract detailed descriptions from the image according to some predefined aspects.
The output should be a JSON object with the following keys:
- usage
- mood
- color_scheme
- culture_traits
- industry_domain
- seasonality
- holiday_theme
Each value should be a long, complete sentence that describes the image in detail.
If no relevant information can be extracted from the image, or if the result is vague, set the value to null instead."""
