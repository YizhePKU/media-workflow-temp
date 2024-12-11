import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

import ffmpeg
import numpy as np
from pydub import AudioSegment
from temporalio import activity


@activity.defn(name="video-metadata")
async def video_metadata(file) -> dict:
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        file,
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
            result["pix_fmt"] = stream["pix_fmt"]
        if stream["codec_type"] == "audio":
            result["audio_codec"] = stream["codec_name"]
            result["sample_fmt"] = stream["sample_fmt"]
            result["channel_layout"] = stream["channel_layout"]
            result["sample_rate"] = int(stream["sample_rate"])

    result["size"] = os.path.getsize(file)
    return result


@activity.defn(name="video-sprite")
async def video_sprite(params) -> list[str]:
    dir = tempfile.gettempdir()
    stream = ffmpeg.input(params["file"])

    interval = params.get("interval", 5)
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
    return paths


@activity.defn(name="video-transcode")
async def video_transcode(params) -> str:
    dir = tempfile.gettempdir()
    stream = ffmpeg.input(params["file"])
    container = params.get("container", "mp4")
    path = f"{dir}/{uuid4()}.{container}"
    kwargs = {
        "codec:v": params.get("video-codec", "h264"),
        "codec:a": params.get("audio-codec", "libopus"),
    }
    stream = stream.output(path, **kwargs)
    stream.run()
    return path


@activity.defn(name="audio-waveform")
async def audio_waveform(params) -> list[float]:
    audio = AudioSegment.from_file(params["file"])
    data = np.array(audio.get_array_of_samples())

    samples = np.zeros(params["num_samples"])
    step = math.ceil(len(data) / params["num_samples"])
    for i in range(0, len(data), step):
        samples[i // step] = np.max(np.abs(data[i : i + step]))

    # Normalize the data
    samples = samples / np.max(samples)
    return samples.tolist()
