import functools
from datetime import timedelta

from temporalio import workflow

start = functools.partial(
    workflow.start_activity, start_to_close_timeout=timedelta(seconds=60)
)


@workflow.defn(name="image-thumbnail")
class ImageThumbnail:
    @workflow.run
    async def run(self, params):
        return {
            "file": await start(
                "image_thumbnail", args=[params["file"], params.get("size")]
            )
        }


@workflow.defn(name="pdf-thumbnail")
class PdfThumbnail:
    @workflow.run
    async def run(self, params):
        return {
            "file": await start(
                "pdf_thumbnail", args=[params["file"], params.get("size")]
            )
        }


@workflow.defn(name="image-detail")
class ImageDetail:
    @workflow.run
    async def run(self, params):
        inputs = {
            "language": params["language"],
            "image": {
                "type": "image",
                "transfer_method": "remote_url",
                "url": params["file"],
            },
        }
        return await start("dify", args=["DIFY_IMAGE_DETAIL_KEY", inputs])
