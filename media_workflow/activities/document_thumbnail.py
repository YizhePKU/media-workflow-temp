from pathlib import Path

import pymupdf
from PIL import Image
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.image import imwrite


def page2image(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap()  # type: ignore
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore


class DocumentThumbnailParams(BaseModel):
    file: Path
    pages: list[int] | None = None
    size: tuple[int, int] | None = None


@instrument
@activity.defn
async def document_thumbnail(params: DocumentThumbnailParams) -> list[Path]:
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
            image.thumbnail(params.size, resample=Image.Resampling.LANCZOS)
    return [imwrite(image) for image in images]
