import os
from pathlib import Path
from uuid import uuid4

import pymupdf
import pyvips
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


def page2image(page: pymupdf.Page, size: tuple[int, int]) -> Path:
    pix = page.get_pixmap()  # type: ignore
    image = pyvips.Image.new_from_memory(pix.samples, pix.width, pix.height, 3, pyvips.enums.BandFormat.UCHAR)
    image = image.thumbnail_image(size[0])  # type: ignore

    path = Path(os.environ["MEDIA_WORKFLOW_DATADIR"]) / f"{uuid4()}.jpeg"
    image.write_to_file(path)  # type: ignore
    return path


class PdfThumbnailParams(BaseModel):
    file: Path
    pages: list[int] | None = None
    size: tuple[int, int] = (1024, 1024)


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
