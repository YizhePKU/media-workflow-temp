import asyncio
from pathlib import Path

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.fs import tempdir


class VideoThumbnailParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def video_thumbnail(params: VideoThumbnailParams) -> Path:
    thumbnail = tempdir() / "thumbnail.jpeg"
    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-vframes",
        "1",
        thumbnail,
        stderr=asyncio.subprocess.PIPE,
    )
    (_, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    return thumbnail
