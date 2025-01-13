import asyncio
import os
import re
from pathlib import Path
from tempfile import mkdtemp
from typing import TypedDict

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class VideoSpriteParams(BaseModel):
    file: Path
    duration: float
    layout: tuple[int, int] = (5, 5)
    count: int = 1
    width: int = 200
    height: int = -1


VideoSpriteResponse = TypedDict(
    "VideoSpriteResponse",
    {
        "interval": float,
        "width": int,
        "height": int,
        "sprites": list[Path],
    },
)


@instrument
@activity.defn
async def video_sprite(params: VideoSpriteParams) -> VideoSpriteResponse:
    _dir = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
    # calculate time between frames (in seconds)
    interval = params.duration / float(params.count * params.layout[0] * params.layout[1])

    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-vf",
        f"fps={1/interval},scale={params.width}:{params.height},tile={params.layout[0]}x{params.layout[1]}",
        "-vframes",
        str(params.count),
        f"{_dir}/%03d.png",
        stderr=asyncio.subprocess.PIPE,
    )
    (_, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    width = 0
    height = 0
    for line in stderr.decode().split("\n"):
        if match := re.search(r"Video: png.*?(\d+)x(\d+)", line):
            width = int(match.group(1))
            height = int(match.group(2))

    sprites = [path for path in Path(_dir).iterdir() if path.suffix == ".png"]
    sprites.sort(key=lambda p: int(p.stem))
    return {
        "interval": interval,
        "width": width // params.layout[0],
        "height": height // params.layout[1],
        "sprites": sprites,
    }
