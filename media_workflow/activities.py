import math
import os
import re
import subprocess
from base64 import b64encode
from inspect import cleandoc
from io import BytesIO
from json import loads as json_loads
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import aiohttp
    import ffmpeg
    import numpy as np
    import pymupdf
    from PIL import Image
    from pydub import AudioSegment

    from media_workflow.s3 import upload


def image2png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


def page2image(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


@activity.defn
async def callback(url: str, json):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json) as response:
            assert response.status == 200


@activity.defn
async def image_thumbnail(params) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(params["file"]) as response:
            image = Image.open(BytesIO(await response.read()))
    if size := params.get("size"):
        image.thumbnail(size)
    return upload(f"{uuid4()}.png", image2png(image))


@activity.defn
async def pdf_thumbnail(params) -> list[str]:
    images = []
    async with aiohttp.ClientSession() as session:
        async with session.get(params["file"]) as response:
            with pymupdf.Document(stream=await response.read()) as doc:
                if pages := params.get("pages"):
                    for i in pages:
                        images.append(page2image(doc[i]))
                else:
                    for page in doc.pages():
                        images.append(page2image(page))
    if size := params.get("size"):
        for image in images:
            image.thumbnail(size)
    return [upload(f"{uuid4()}.png", image2png(image)) for image in images]


@activity.defn
async def image_detail(params) -> dict:
    headers = {"Authorization": f"Bearer {os.environ["DIFY_IMAGE_DETAIL_KEY"]}"}
    json = {
        "inputs": {
            "language": params["language"],
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": params["file"],
            },
        },
        "user": os.environ["DIFY_USER"],
        "response_mode": "blocking",
    }
    async with aiohttp.ClientSession() as session:
        url = f"{os.environ["DIFY_ENDPOINT_URL"]}/workflows/run"
        async with session.post(url, headers=headers, json=json) as r:
            result = await r.json()
    assert result["data"]["status"] == "succeeded"
    assert isinstance(result["data"]["outputs"]["tags"], str)
    return result["data"]["outputs"]


@activity.defn
async def video_sprite(params) -> list[str]:
    with TemporaryDirectory() as dir:
        stream = ffmpeg.input(params["file"])

        if interval := params.get("interval"):
            expr = f"floor((t - prev_selected_t) / {interval})"
            stream = stream.filter("select", expr=expr)

        if layout := params.get("layout"):
            stream = stream.filter("tile", layout=f"{layout[0]}x{layout[1]}")

        stream = stream.filter(
            "scale", width=params.get("width", -1), height=params.get("height", -1)
        )

        filename = f"{dir}/%03d.png"
        if count := params.get("count"):
            stream = stream.output(filename, fps_mode="passthrough", vframes=count)
        else:
            stream = stream.output(filename, fps_mode="passthrough")

        stream.run()

        paths = list(Path(dir).iterdir())
        paths.sort(key=lambda p: int(p.stem))
        result = []
        for path in paths:
            with open(path, "rb") as file:
                result.append(upload(f"{uuid4()}.png", file.read()))
        return result


@activity.defn
async def video_transcode(params) -> str:
    with TemporaryDirectory() as dir:
        stream = ffmpeg.input(params["file"])

        path = Path(f"{dir}/{uuid4()}.{params.get("container", "mp4")}")
        kwargs = {
            "codec:v": params.get("video-codec", "h264"),
            "codec:a": params.get("audio-codec", "libopus"),
        }
        stream = stream.output(str(path), **kwargs)
        stream.run()

        with open(path, "rb") as file:
            return upload(path.name, file.read())


@activity.defn
async def audio_waveform(params) -> list[float]:
    async with aiohttp.ClientSession() as client:
        async with client.get(params["file"]) as r:
            payload = await r.read()
    audio = AudioSegment.from_file(BytesIO(payload))
    data = np.array(audio.get_array_of_samples())

    samples = np.zeros(params["num_samples"])
    step = math.ceil(len(data) / params["num_samples"])
    for i in range(0, len(data), step):
        samples[i // step] = np.max(np.abs(data[i : i + step]))

    # Normalize the data
    samples = samples / np.max(samples)
    return samples.tolist()


@activity.defn
async def convert_to_pdf(params) -> str:
    with TemporaryDirectory() as dir:
        stem = str(uuid4())
        input = f"{dir}/{stem}"
        async with aiohttp.ClientSession() as client:
            async with client.get(params["file"]) as r:
                with open(input, "wb") as file:
                    file.write(await r.read())
        subprocess.run(["soffice", "--convert-to", "pdf", "--outdir", dir, input])
        output = f"{input}.pdf"
        with open(output, "rb") as file:
            return upload(f"{stem}.pdf", file.read())


async def minicpm(prompt: str, image_url: str, postprocess=None):
    async with aiohttp.ClientSession() as client:
        async with client.get(image_url) as r:
            b64image = b64encode(await r.read()).decode("ascii")

        url = f"{os.environ["OLLAMA_ENDPOINT"]}/api/chat"
        headers = {"Authorization": f"Bearer {os.environ["OLLAMA_KEY"]}"}
        json = {
            "model": "minicpm-v:8b-2.6-q4_K_S",
            "stream": False,
            "messages": [{"role": "user", "content": prompt, "images": [b64image]}],
        }
        async with client.post(url, headers=headers, json=json) as r:
            json = await r.json()

        if error := json.get("error"):
            raise Exception(error)
        content = json["message"]["content"]
        if postprocess:
            content = postprocess(content)
        return content


@activity.defn
async def image_analysis_basic(params):
    def postprocess(content):
        json = json_loads(content)
        assert isinstance(json["title"], str)
        assert isinstance(json["description"], str)
        return json

    prompt = cleandoc(
        f"""
        Extract a title and a detailed description from the image. The output should be in {params["language"]}.

        The output should be in JSON format. The output JSON should contain the following keys:
        - title
        - description

        The title should summarize the image in a short, single sentence using {params["language"]}.
        No punctuation mark should be in the title.

        The description should be a long text that describes the content of the image.
        All objects that appear in the image should be described.
        If there're any text in the image, mention the text and the font type of that text.
        """
    )
    return await minicpm(prompt, params["file"], postprocess)


@activity.defn
async def image_analysis_tags(params):
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
        return json

    prompt = cleandoc(
        f"""
        Extract tags from the image according to some predefined aspects. The output should be in {params["language"]}.

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
        Each string should briefly describes the image in {params["language"]}.
        Only use strings inside lists, not complex objects.

        If the extracted value is vague or non-informative, or if the tag doesn't apply to this image, set the value to an empty list instead. 
        If the extracted value is a complex object instead of a string, summarize it in a short string instead.
        If the extracted value is too long, shorten it by summarizing the key information.
        """
    )
    return await minicpm(prompt, params["file"], postprocess)


@activity.defn
async def image_analysis_details(params):
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
        if params["language"].lower() != "english":
            for value in json.values():
                if value and value.isascii():
                    raise Exception(
                        "Model generated English result when the requested language is not English"
                    )
        return json

    prompt = cleandoc(
        f"""
        Extract detailed descriptions from the image according to some predefined aspects.
        The output should be in {params["language"]}.

        The output should be a JSON object with the following keys:
        - usage
        - mood
        - color_theme
        - culture_traits
        - industry_domain
        - seasonality
        - holiday_theme

        Each value should be a short phrase that describes the image in {params["language"]}.
        If the extracted value is not in {params["language"]}, translate the value to {params["language"]} instead.
        If no relevant information can be extracted from the image, or if the result is vague, set the value to null instead.
        """
    )
    return await minicpm(prompt, params["file"], postprocess)
