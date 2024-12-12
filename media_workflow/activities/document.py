from dataclasses import dataclass
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

import pymupdf
from PIL import Image
from temporalio import activity

from media_workflow.utils import imwrite


def page2image(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


@dataclass
class ToPdfParams:
    file: str


@activity.defn(name="convert-to-pdf")
async def to_pdf(params: ToPdfParams) -> str:
    dir = tempfile.gettempdir()
    subprocess.run(["soffice", "--convert-to", "pdf", "--outdir", dir, params.file])
    stem = Path(params.file).stem
    return f"{dir}/{stem}.pdf"


@dataclass
class ThumbnailParams:
    file: str
    pages: list[int] = None
    size: Tuple[int, int] = None


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
    return [imwrite(image) for image in images]
