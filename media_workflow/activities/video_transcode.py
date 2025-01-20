import asyncio
from pathlib import Path

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.fs import tempdir


class VideoTranscodeParams(BaseModel):
    file: Path
    video_codec: str = "copy"
    audio_codec: str = "copy"
    container: str = "mp4"


@instrument
@activity.defn
async def video_transcode(params: VideoTranscodeParams) -> Path:
    output = tempdir() / f"{params.file.stem}.{params.container}"
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
        if params.video_codec == "copy":
            # We tried to avoid transcoding but it didn't work. Perhaps the container doesn't support the original
            # codecs. Let's try again by transcoding to some sensible defaults codecs.
            return await video_transcode(
                VideoTranscodeParams(
                    file=params.file, video_codec="h264", audio_codec="libopus", container=params.container
                )
            )
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    assert output.exists()
    return output
