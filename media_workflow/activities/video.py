import asyncio
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from uuid import uuid4

import numpy as np
from pydub import AudioSegment
from temporalio import activity

from media_workflow.utils import ensure_exists


@dataclass
class MetadataParams:
    file: str


@activity.defn(name="video-metadata")
async def metadata(params: MetadataParams) -> dict:
    ensure_exists(params.file)
    process = await asyncio.subprocess.create_subprocess_exec(
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        params.file,
        stdout=asyncio.subprocess.PIPE,
    )
    (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    data = json.loads(stdout.decode())
    result = {}
    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            result["duration"] = float(stream["duration"])
            result["video_codec"] = stream["codec_name"]
            result["width"] = int(stream["width"])
            result["height"] = int(stream["height"])
            numerator, denominator = map(int, stream["avg_frame_rate"].split("/"))
            result["fps"] = float(numerator) / float(denominator)
            result["bit_rate"] = int(stream["bit_rate"])
            result["bits_per_raw_sample"] = int(stream["bits_per_raw_sample"])
            result["pix_fmt"] = stream["pix_fmt"]
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
    datadir: str
    layout: Tuple[int, int] = (1, 1)
    count: int = 1
    width: int = -1
    height: int = -1


@activity.defn(name="video-sprite")
async def sprite(params: SpriteParams) -> list[str]:
    ensure_exists(params.file)
    # calculate time between frames (in seconds)
    interval = params.duration / float(
        params.count * params.layout[0] * params.layout[1]
    )

    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-vf",
        f"fps={1/interval},tile={params.layout[0]}x{params.layout[1]},scale={params.width}:{params.height}",
        "-vframes",
        str(params.count),
        f"{params.datadir}/%03d.png",
    )
    await process.wait()

    paths = list(
        path for path in Path(params.datadir).iterdir() if path.suffix == ".png"
    )
    paths.sort(key=lambda p: int(p.stem))
    return [str(path) for path in paths]


@dataclass
class TranscodeParams:
    file: str
    datadir: str
    video_codec: str = "h264"
    audio_codec: str = "libopus"
    container: str = "mp4"


@activity.defn(name="video-transcode")
async def transcode(params: TranscodeParams) -> str:
    ensure_exists(params.file)
    output = f"{params.datadir}/{uuid4()}.{params.container}"
    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-codec:v",
        params.video_codec,
        "-codec:a",
        params.audio_codec,
        output,
    )
    await process.wait()
    return output


@dataclass
class WaveformParams:
    file: str
    num_samples: int = 1000


@activity.defn(name="audio-waveform")
async def waveform(params: WaveformParams) -> list[float]:
    ensure_exists(params.file)
    audio = AudioSegment.from_file(params.file)
    data = np.array(audio.get_array_of_samples())

    samples = np.zeros(params.num_samples)
    step = math.ceil(len(data) / params.num_samples)
    for i in range(0, len(data), step):
        samples[i // step] = np.max(np.abs(data[i : i + step]))

    # Normalize the data
    samples = samples / np.max(samples)
    return samples.tolist()
