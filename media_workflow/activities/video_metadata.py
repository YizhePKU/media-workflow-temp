import asyncio
import json
import os
from pathlib import Path

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class VideoMetadataParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def video_metadata(params: VideoMetadataParams) -> dict:
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
    for stream in data["streams"]:
        # Some audio files contain video streams to store a thumbnail, in which case most of these fields don't make
        # sense. Ideally we would extract every field possible and skip the rest.
        try:
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
        except Exception:
            print(f"warning: failed to extract video metadata from {params.file}")

        try:
            if stream["codec_type"] == "audio":
                result["audio_codec"] = stream["codec_name"]
                result["sample_fmt"] = stream["sample_fmt"]
                result["channel_layout"] = stream["channel_layout"]
                result["sample_rate"] = int(stream["sample_rate"])
        except Exception:
            print(f"warning: failed to extract audio metadata from {params.file}")

    result["duration"] = float(data["format"]["duration"])
    result["size"] = os.path.getsize(params.file)
    return result
