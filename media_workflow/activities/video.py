from dataclasses import dataclass
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple
from uuid import uuid4

import ffmpeg
import numpy as np
from pydub import AudioSegment
from temporalio import activity


@dataclass
class MetadataParams:
    file: str


@activity.defn(name="video-metadata")
async def metadata(params: MetadataParams) -> dict:
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        params.file,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.decode()}")

    data = json.loads(result.stdout.decode())
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
    layout: Tuple[int, int] = (1, 1)
    count: int = 1
    width: int = -1
    height: int = -1


@activity.defn(name="video-sprite")
async def sprite(params: SpriteParams) -> list[str]:
    dir = tempfile.mkdtemp()

    # calculate time between frames (in seconds)
    interval = params.duration / float(
        params.count * params.layout[0] * params.layout[1]
    )

    stream = ffmpeg.input(params.file)
    stream = stream.filter("fps", 1 / interval)
    stream = stream.filter("tile", layout=f"{params.layout[0]}x{params.layout[1]}")
    stream = stream.filter("scale", width=params.width, height=params.height)
    stream = stream.output(f"{dir}/%03d.png", vframes=params.count)
    stream.run()

    paths = list(Path(dir).iterdir())
    paths.sort(key=lambda p: int(p.stem))
    return [str(path) for path in paths]


@dataclass
class TranscodeParams:
    file: str
    video_codec: str = "h264"
    audio_codec: str = "libopus"
    container: str = "mp4"


@activity.defn(name="video-transcode")
async def transcode(params: TranscodeParams) -> str:
    dir = tempfile.gettempdir()
    path = f"{dir}/{uuid4()}.{params.container}"
    stream = ffmpeg.input(params.file)
    kwargs = {
        "codec:v": params.video_codec,
        "codec:a": params.audio_codec,
    }
    stream = stream.output(path, **kwargs)
    stream.run()
    return path


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
