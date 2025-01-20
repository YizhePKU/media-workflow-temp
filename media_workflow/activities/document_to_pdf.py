import asyncio
import os
from pathlib import Path
from tempfile import mkdtemp

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument

# To run multiple instances of LibreOffice concurrently, they must have different profile directories. We'll use a lock
# to limit one instance of LibreOffice at a time. This might seem restricting, but LibreOffice takes a lot of memory, so
# we couldn't run many of those anyways.
LOCK = asyncio.Lock()


class DocumentToPdfParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def document_to_pdf(params: DocumentToPdfParams) -> Path:
    _dir = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
    async with LOCK:
        # heartbeat so that we abort the operation in case the activity already timed out
        activity.heartbeat()
        process = await asyncio.subprocess.create_subprocess_exec(
            "soffice",
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
