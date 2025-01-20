import asyncio
import os
from pathlib import Path
from tempfile import mkdtemp

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class VideoThumbnailParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def video_thumbnail(params: VideoThumbnailParams) -> Path:
    _dir = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
    thumbnail = _dir / "thumbnail.jpeg"
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
