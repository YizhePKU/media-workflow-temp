import subprocess

import pymupdf
from PIL import Image
from temporalio import activity

from media_workflow.utils import imwrite


def page2image(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap()
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


@activity.defn(name="pdf-thumbnail")
async def pdf_thumbnail(params) -> list[str]:
    images = []
    with pymupdf.Document(filename=params["file"]) as doc:
        if pages := params.get("pages"):
            for i in pages:
                images.append(page2image(doc[i]))
        else:
            for page in doc.pages():
                images.append(page2image(page))
    if size := params.get("size"):
        for image in images:
            image.thumbnail(size, resample=Image.LANCZOS)
    return [imwrite(image) for image in images]


@activity.defn(name="convert-to-pdf")
async def convert_to_pdf(params) -> str:
    # TODO: DOESN'T WORK
    with TemporaryDirectory() as dir:
        stem = str(uuid4())
        input = f"{dir}/{stem}"
        subprocess.run(
            ["soffice", "--convert-to", "pdf", "--outdir", dir, params["file"]]
        )
        return f"{input}.pdf"
