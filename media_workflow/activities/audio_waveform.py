import asyncio
import math
from pathlib import Path

import numpy as np
from pydantic import BaseModel
from temporalio import activity

from media_workflow.trace import instrument


class AudioWaveformParams(BaseModel):
    file: Path
    num_samples: int = 1000


@instrument
@activity.defn
async def audio_waveform(params: AudioWaveformParams) -> list[float]:
    # Convert the audio to raw 16-bit little-endian samples.
    process = await asyncio.subprocess.create_subprocess_exec(
        "ffmpeg",
        "-i",
        params.file,
        "-f",
        "s16le",
        "-codec:a",
        "pcm_s16le",
        "-",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
    data = np.frombuffer(stdout, dtype=np.int16)

    samples = np.zeros(params.num_samples)
    step = math.ceil(len(data) / params.num_samples)
    for i in range(0, len(data), step):
        samples[i // step] = np.max(np.abs(data[i : i + step]))

    # Normalize the data
    samples = samples / np.max(samples)
    return samples.tolist()  # type: ignore
