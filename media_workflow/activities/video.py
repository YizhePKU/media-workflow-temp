import asyncio
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from uuid import uuid4

import numpy as np
from pydub import AudioSegment
from temporalio import activity

from media_workflow.activities.utils import get_datadir


@dataclass
class MetadataParams:
    file: str


@activity.defn(name="video-metadata")
async def metadata(params: MetadataParams) -> dict:
    process = await asyncio.subprocess.create_subprocess_exec(
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_entries",
        "format=duration",
        "-show_streams",
        params.file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    data = json.loads(stdout.decode())
    result = {}
    result["duration"] = float(data["format"]["duration"])
    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            result["video_codec"] = stream["codec_name"]
            result["width"] = int(stream["width"])
            result["height"] = int(stream["height"])
            numerator, denominator = map(int, stream["avg_frame_rate"].split("/"))
            result["fps"] = float(numerator) / float(denominator)
            result["pix_fmt"] = stream["pix_fmt"]
            # bitrate info is not available in every video
            result["bit_rate"] = int(stream.get("bit_rate", 0))
            result["bits_per_raw_sample"] = int(stream.get("bits_per_raw_sample", 0))
        if stream["codec_type"] == "audio":
            result["audio_codec"] = stream["codec_name"]
            result["sample_fmt"] = stream["sample_fmt"]
            result["channel_layout"] = stream["channel_layout"]
            result["sample_rate"] = int(stream["sample_rate"])

    result["size"] = os.path.getsize(params.file)
    return result


@dataclass
class SpriteParams:
    file: str
    duration: float
    layout: Tuple[int, int] = (5, 5)
    count: int = 1
    width: int = 200
    height: int = -1


@activity.defn(name="video-sprite")
async def sprite(params: SpriteParams) -> dict:
    datadir = get_datadir()
    # calculate time between frames (in seconds)
    interval = params.duration / float(
        params.count * params.layout[0] * params.layout[1]
    )

    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-vf",
        f"fps={1/interval},scale={params.width}:{params.height},tile={params.layout[0]}x{params.layout[1]}",
        "-vframes",
        str(params.count),
        f"{datadir}/%03d.png",
        stderr=asyncio.subprocess.PIPE,
    )
    (_, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    for line in stderr.decode().split("\n"):
        if match := re.search(r"Video: png.*?(\d+)x(\d+)", line):
            width = int(match.group(1))
            height = int(match.group(2))

    paths = list(path for path in Path(datadir).iterdir() if path.suffix == ".png")
    paths.sort(key=lambda p: int(p.stem))
    return {
        "interval": interval,
        "width": width // params.layout[0],
        "height": height // params.layout[1],
        "files": [str(path) for path in paths],
    }


@dataclass
class TranscodeParams:
    file: str
    video_codec: str = "h264"
    audio_codec: str = "libopus"
    container: str = "mp4"


@activity.defn(name="video-transcode")
async def transcode(params: TranscodeParams) -> str:
    datadir = get_datadir()
    output = f"{datadir}/{uuid4()}.{params.container}"
    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-codec:v",
        params.video_codec,
        "-codec:a",
        params.audio_codec,
        output,
        stderr=asyncio.subprocess.PIPE,
    )
    (_, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    assert os.path.exists(output)
    return output


@dataclass
class WaveformParams:
    file: str
    num_samples: int = 1000


@activity.defn(name="audio-waveform")
async def waveform(params: WaveformParams) -> list[float]:
    audio = AudioSegment.from_file(params.file)
    data = np.array(audio.get_array_of_samples())

    samples = np.zeros(params.num_samples)
    step = math.ceil(len(data) / params.num_samples)
    for i in range(0, len(data), step):
        samples[i // step] = np.max(np.abs(data[i : i + step]))

    # Normalize the data
    samples = samples / np.max(samples)
    return samples.tolist()
