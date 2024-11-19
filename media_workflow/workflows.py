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
        result = {
            "id": workflow.info().workflow_id,
            "file": await start(
                "image_thumbnail", args=[params["file"], params.get("size")]
            ),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="pdf-thumbnail")
class PdfThumbnail:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "file": await start(
                "pdf_thumbnail", args=[params["file"], params.get("size")]
            ),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="image-detail")
class ImageDetail:
    @workflow.run
    async def run(self, params):
        result = await start("image_detail", args=[params["file"], params["language"]])
        result["id"] = workflow.info().workflow_id
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="image-detail-basic")
class ImageDetailBasic:
    @workflow.run
    async def run(self, params):
        result = await start(
            "image_detail_basic", args=[params["file"], params["language"]]
        )
        result["id"] = workflow.info().workflow_id
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="video-sprite")
class VideoSprite:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "files": await start(
                "video_sprite",
                args=[
                    params["file"],
                    params.get("interval"),
                    params.get("layout"),
                    params.get("width"),
                    params.get("height"),
                    params.get("count"),
                ],
            ),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result
