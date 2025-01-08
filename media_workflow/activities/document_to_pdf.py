import asyncio
import os
from pathlib import Path
from tempfile import mkdtemp

from pydantic import BaseModel
from temporalio import activity

from media_workflow.trace import instrument


class DocumentToPdfParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def document_to_pdf(params: DocumentToPdfParams) -> Path:
    _dir = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
    process = await asyncio.subprocess.create_subprocess_exec(
        "soffice",
        # To run multiple instances of LibreOffice concurrently, they must have different profile directories.
        f"-env:UserInstallation=file://{mkdtemp()}",
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
