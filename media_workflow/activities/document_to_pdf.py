import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import mkdtemp
from typing import AsyncGenerator

from pydantic import BaseModel
from temporalio import activity

from media_workflow.trace import instrument

# To run multiple instances of LibreOffice concurrently, they must have different profile directories.
# We use a pool to limit the maximum concurrency, otherwise the worker can run out of memory.
MAX_PROFILES = 4
profiles = asyncio.Queue[Path](maxsize=MAX_PROFILES)

# Initialize profiles.
for _ in range(MAX_PROFILES):
    profiles.put_nowait(Path(mkdtemp()))


@asynccontextmanager
async def get_profile() -> AsyncGenerator[Path]:
    profile = await profiles.get()
    try:
        yield profile
    finally:
        await profiles.put(profile)


class DocumentToPdfParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def document_to_pdf(params: DocumentToPdfParams) -> Path:
    _dir = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
    async with get_profile() as profile:
        # heartbeat so that we abort the operation if waiting for a profile took too long
        activity.heartbeat()
        process = await asyncio.subprocess.create_subprocess_exec(
            "soffice",
            f"-env:UserInstallation=file://{profile}",
            "--convert-to",
            "pdf",
            "--outdir",
            _dir,
            params.file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"soffice failed: {stdout.decode()} {stderr.decode()}")
    output = _dir / f"{Path(params.file).stem}.pdf"
    assert output.exists()
    return output
