import asyncio
from pathlib import Path

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.fs import tempdir

# To run multiple instances of LibreOffice concurrently, they must be configured to use different profile directories.
# Instead of trying to maintain a pool of profiles, we'll use a lock to limit one instance of LibreOffice running at a
# time. This might seem restricting, but LibreOffice takes a lot of memory, so we couldn't run many of them anyways.
LOCK = asyncio.Lock()


class DocumentToPdfParams(BaseModel):
    file: Path


@instrument
@activity.defn
async def document_to_pdf(params: DocumentToPdfParams) -> Path:
    if params.file.suffix in [".md", ".tex", ".epub", ".txt", ".html", ".csv"]:
        return await pandoc_to_pdf(params.file)
    else:
        return await libreoffice_to_pdf(params.file)


async def pandoc_to_pdf(file: Path) -> Path:
    output = tempdir() / f"{file.stem}.pdf"
    process = await asyncio.subprocess.create_subprocess_exec(
        "pandoc",
        "--pdf-engine=xelatex",
        "--variable=CJKmainfont:Noto Sans CJK SC",
        "--variable=documentclass=ctexart",
        "--variable=fontsize=12pt",
        "--variable=geometry:margin=0mm",
        f"--output={output}",
        file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"pandoc failed: {stdout.decode()} {stderr.decode()}")
    assert output.exists()
    return output


async def libreoffice_to_pdf(file: Path) -> Path:
    outdir = tempdir()
    async with LOCK:
        # heartbeat so that we abort the operation in case the activity already timed out
        activity.heartbeat()
        process = await asyncio.subprocess.create_subprocess_exec(
            "soffice",
            "--convert-to",
            "pdf",
            "--outdir",
            outdir,
            file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"soffice failed: {stdout.decode()} {stderr.decode()}")
    output = outdir / f"{Path(file).stem}.pdf"
    assert output.exists()
    return output
