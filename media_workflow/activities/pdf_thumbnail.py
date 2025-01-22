from pathlib import Path

import pymupdf
import pyvips
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.fs import tempdir


def page2image(page: pymupdf.Page, size: tuple[int, int] | None) -> Path:
    zoom = 2  # render images at higher DPI
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))  # type: ignore
    image = pyvips.Image.new_from_memory(pix.samples, pix.width, pix.height, 3, pyvips.enums.BandFormat.UCHAR)
    if size is not None:
        image = image.thumbnail_image(size[0])  # type: ignore

    path = tempdir() / "page.jpeg"
    image.write_to_file(path)  # type: ignore
    return path


class PdfThumbnailParams(BaseModel):
    file: Path
    pages: list[int] | None = None
    size: tuple[int, int] | None = None


@instrument
@activity.defn
async def pdf_thumbnail(params: PdfThumbnailParams) -> list[Path]:
    images = []
    with pymupdf.Document(filename=params.file) as doc:
        if params.pages is not None:
            for i in params.pages:
                images.append(page2image(doc[i], params.size))
        else:
            for page in doc.pages():
                images.append(page2image(page, params.size))
    return images
