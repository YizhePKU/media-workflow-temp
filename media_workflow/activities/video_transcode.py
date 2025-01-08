import asyncio
import os
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from pydantic import BaseModel
from temporalio import activity

from media_workflow.trace import instrument


class VideoTranscodeParams(BaseModel):
    file: Path
    video_codec: str = "h264"
    audio_codec: str = "libopus"
    container: str = "mp4"


@instrument
@activity.defn
async def video_transcode(params: VideoTranscodeParams) -> Path:
    _dir = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
    output = _dir / f"{uuid4()}.{params.container}"
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
    assert output.exists()
    return output
