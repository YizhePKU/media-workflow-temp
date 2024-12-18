from dataclasses import dataclass
import os
from pathlib import Path
from typing import Tuple
import asyncio

import pymupdf
from PIL import Image
from temporalio import activity

from media_workflow.activities.utils import get_datadir
from media_workflow.utils import imwrite


def page2image(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


@dataclass
class ToPdfParams:
    file: str


@activity.defn(name="convert-to-pdf")
async def to_pdf(params: ToPdfParams) -> str:
    datadir = get_datadir()
    process = await asyncio.subprocess.create_subprocess_exec(
        "soffice", "--convert-to", "pdf", "--outdir", datadir, params.file
    )
    await process.wait()
    output = f"{datadir}/{Path(params.file).stem}.pdf"
    assert os.path.exists(output)
    return output


@dataclass
class ThumbnailParams:
    file: str
    pages: list[int] | None = None
    size: Tuple[int, int] | None = None


@activity.defn(name="pdf-thumbnail")
async def thumbnail(params: ThumbnailParams) -> list[str]:
    images = []
    with pymupdf.Document(filename=params.file) as doc:
        if params.pages is not None:
            for i in params.pages:
                images.append(page2image(doc[i]))
        else:
            for page in doc.pages():
                images.append(page2image(page))
    if params.size is not None:
        for image in images:
            image.thumbnail(params.size, resample=Image.LANCZOS)
    return [imwrite(image, datadir=get_datadir()) for image in images]
