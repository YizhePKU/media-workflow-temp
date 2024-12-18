from dataclasses import dataclass
import os
from base64 import b64encode
from inspect import cleandoc
from json import loads as json_loads
import re
from typing import Tuple

import aiohttp
from PIL import Image
from temporalio import activity

from media_workflow.activities.utils import get_datadir
from media_workflow.utils import ensure_exists, imread, imwrite
from pylette.color_extraction import extract_colors


@dataclass
class ThumbnailParams:
    file: str
    size: Tuple[int, int] | None = None


@activity.defn(name="image-thumbnail")
async def thumbnail(params: ThumbnailParams) -> str:
    ensure_exists(params.file)
    image = imread(params.file)
    if params.size is not None:
        image.thumbnail(params.size, resample=Image.LANCZOS)
    return imwrite(image, datadir=get_datadir())


@dataclass
class DetailParams:
    url: str
    language: str = "Simplified Chinese"


@activity.defn(name="image-detail")
async def detail(params: DetailParams) -> dict:
    headers = {"Authorization": f"Bearer {os.environ['DIFY_IMAGE_DETAIL_KEY']}"}
    json = {
        "inputs": {
            "language": params.language,
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": params.url,
            },
        },
        "user": os.environ["DIFY_USER"],
        "response_mode": "blocking",
    }
    async with aiohttp.ClientSession() as session:
        url = f"{os.environ['DIFY_ENDPOINT_URL']}/workflows/run"
        async with session.post(url, headers=headers, json=json) as r:
            result = await r.json()
    try:
        assert result["data"]["status"] == "succeeded"
    except (KeyError, AssertionError):
        raise RuntimeError(f"dify failed: {await r.text()}")

    try:
        assert isinstance(result["data"]["outputs"]["tags"], str)
    except AssertionError:
        raise RuntimeError(f"validation failed for dify output: {await r.json()}")

    return result["data"]["outputs"]


@dataclass
class DetailBasicParams:
    file: str
    language: str = "Simplified Chinese"


async def minicpm(prompt: str, image: str, postprocess=None):
    with open(image, "rb") as file:
        b64image = b64encode(file.read()).decode("ascii")

    url = f"{os.environ['OLLAMA_ENDPOINT']}/api/chat"
    headers = {"Authorization": f"Bearer {os.environ['OLLAMA_KEY']}"}
    json = {
        "model": "minicpm-v:8b-2.6-q4_K_S",
        "stream": False,
        "messages": [{"role": "user", "content": prompt, "images": [b64image]}],
    }
    async with aiohttp.ClientSession() as client:
        async with client.post(url, headers=headers, json=json) as r:
            if r.status != 200:
                raise Exception(f"Ollama returned status {r.status}: {await r.text()}")
            json = await r.json()

    if error := json.get("error"):
        raise Exception(error)
    content = json["message"]["content"]
    if postprocess:
        content = postprocess(content)
    return content


@activity.defn(name="image-minicpm-basic")
async def minicpm_basic(params: DetailBasicParams):
    def postprocess(content):
        json = json_loads(content)
        assert isinstance(json["title"], str)
        assert isinstance(json["description"], str)
        if json["title"].isascii() or json["description"].isascii():
            raise Exception(
                "Model generated English result when the requested language is not English"
            )
        return json

    ensure_exists(params.file)
    prompt = cleandoc(
        f"""
        Extract a title and a detailed description from the image. The output should be in {params.language}.

        The output should be in JSON format. The output JSON should contain the following keys:
        - title
        - description

        The title should summarize the image in a short, single sentence using {params.language}.
        No punctuation mark should be in the title.

        The description should be a long text that describes the content of the image.
        All objects that appear in the image should be described.
        If there're any text in the image, mention the text and the font type of that text.
        """
    )
    return await minicpm(prompt, params.file, postprocess)


@activity.defn(name="image-minicpm-tags")
async def minicpm_tags(params: DetailBasicParams):
    def postprocess(content):
        keys = [
            "theme_identification",
            "emotion_capture",
            "style_annotation",
            "color_analysis",
            "scene_description",
            "character_analysis",
            "purpose_clarification",
            "technology_identification",
            "time_marking",
            "trend_tracking",
        ]

        json = json_loads(content)
        for key in keys:
            # check that each value is a list
            if key not in json or not isinstance(json[key], list):
                json[key] = []
            # check that each value inside that list is a string
            if json[key] and not isinstance(json[key][0], str):
                json[key] = []
            # split values that have commas
            json[key] = list(
                subvalue for value in json[key] for subvalue in re.split(",|，", value)
            )
        # reject English results if the language is not set to English
        if params.language.lower() != "english":
            for tags in json.values():
                for tag in tags:
                    if tag.isascii():
                        raise Exception(
                            "Model generated English result when the requested language is not English"
                        )
        return json

    ensure_exists(params.file)
    prompt = cleandoc(
        f"""
        Extract tags from the image according to some predefined aspects. The output should be in {params.language}.

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

        Each tag value should be a JSON list containing zero of more short strings.
        Each string should briefly describes the image in {params.language}.
        Only use strings inside lists, not complex objects.

        If the extracted value is vague or non-informative, or if the tag doesn't apply to this image, set the value to an empty list instead. 
        If the extracted value is a complex object instead of a string, summarize it in a short string instead.
        If the extracted value is too long, shorten it by summarizing the key information.
        """
    )
    return await minicpm(prompt, params.file, postprocess)


@activity.defn(name="image-minicpm-details")
async def minicpm_details(params: DetailBasicParams):
    def postprocess(content):
        keys = [
            "usage",
            "mood",
            "color_theme",
            "culture_traits",
            "industry_domain",
            "seasonality",
            "holiday_theme",
        ]

        json = json_loads(content)
        for key in keys:
            if key not in json or not isinstance(json[key], str):
                json[key] = None

        # reject English results if the language is not set to English
        if params.language.lower() != "english":
            for value in json.values():
                if value and value.isascii():
                    raise Exception(
                        "Model generated English result when the requested language is not English"
                    )
        return json

    ensure_exists(params.file)
    prompt = cleandoc(
        f"""
        Extract detailed descriptions from the image according to some predefined aspects.
        The output should be in {params.language}.

        The output should be a JSON object with the following keys:
        - usage
        - mood
        - color_theme
        - culture_traits
        - industry_domain
        - seasonality
        - holiday_theme

        Each value should be a short phrase that describes the image in {params.language}.
        If the extracted value is not in {params.language}, translate the value to {params.language} instead.
        If no relevant information can be extracted from the image, or if the result is vague, set the value to null instead.
        """
    )
    return await minicpm(prompt, params.file, postprocess)


def rgb2hex(rgb: list[int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


@dataclass
class ColorPaletteParams:
    file: str
    count: int = 10


@activity.defn(name="image-color-palette")
async def color_palette(params: ColorPaletteParams) -> list:
    ensure_exists(params.file)
    image = imread(params.file)
    palette = extract_colors(image.convert("RGB"), params.count)
    return [{"color": rgb2hex(color.rgb), "frequency": color.freq} for color in palette]
