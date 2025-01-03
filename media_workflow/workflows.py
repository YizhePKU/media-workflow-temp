import asyncio
import functools
from datetime import timedelta

from temporalio import workflow

from media_workflow.activities import (
    document,
    font,
    image,
    image_detail,
    utils,
    video,
)
from media_workflow.trace import instrument

start = functools.partial(
    workflow.start_activity,
    start_to_close_timeout=timedelta(minutes=5),
)


@workflow.defn(name="file-analysis")
class FileAnalysis:
    def __init__(self):
        self.results = {}

    @instrument
    @workflow.update
    async def get(self, key):
        await workflow.wait_condition(lambda: key in self.results)
        return self.results[key]

    @instrument
    @workflow.run
    async def run(self, request):
        self.request = request

        file = await start(
            utils.download,
            utils.DownloadParams(request["file"]),
            start_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(seconds=30),
        )

        async with asyncio.TaskGroup() as tg:
            if "image-thumbnail" in request["activities"]:
                tg.create_task(self.image_thumbnail(file))
            if "image-detail" in request["activities"]:
                tg.create_task(self.image_detail(file))
            if "image-detail-basic" in request["activities"]:
                tg.create_task(self.image_detail_basic(file))
            if "image-color-palette" in request["activities"]:
                tg.create_task(self.image_color_palette(file))
            if "video-metadata" in request["activities"]:
                tg.create_task(self.video_metadata(file))
            if "video-sprite" in request["activities"]:
                tg.create_task(self.video_sprite(file))
            if "video-transcode" in request["activities"]:
                tg.create_task(self.video_transcode(file))
            if "audio-waveform" in request["activities"]:
                tg.create_task(self.audio_waveform(file))
            if "document-thumbnail" in request["activities"]:
                tg.create_task(self.document_thumbnail(file))
            if "font-thumbnail" in request["activities"]:
                tg.create_task(self.font_thumbnail(file))
            if "font-metadata" in request["activities"]:
                tg.create_task(self.font_metadata(file))
            if "font-detail" in request["activities"]:
                tg.create_task(self.font_detail(file))
            if "c4d-preview" in request["activities"]:
                tg.create_task(self.c4d_preview())

        return {
            "id": workflow.info().workflow_id,
            "request": request,
            "result": self.results,
        }

    @instrument
    async def submit(self, activity, result):
        self.results[activity] = result
        if callback := self.request.get("callback"):
            params = utils.WebhookParams(
                url=callback,
                msg_id=str(workflow.uuid4()),
                payload={
                    "id": workflow.info().workflow_id,
                    "request": self.request,
                    "result": {
                        activity: result,
                    },
                },
            )
            await workflow.start_child_workflow(
                Webhook.run, params, parent_close_policy=workflow.ParentClosePolicy.ABANDON
            )

    @instrument
    async def image_thumbnail(self, file):
        activity = "image-thumbnail"
        file = await start(
            image.thumbnail,
            image.ThumbnailParams(
                file,
                **self.request.get("params", {}).get(activity, {}),
            ),
        )
        result = await start(utils.upload, utils.UploadParams(file, "image/png"))
        await self.submit(activity, result)

    @instrument
    async def image_detail(self, file):
        activity = "image-detail"
        # convert image to PNG first
        png = await start(
            image.thumbnail,
            image.ThumbnailParams(file, size=(1024, 1024)),
        )
        params = image_detail.ImageDetailParams(png, **self.request.get("params", {}).get(activity, {}))
        main_response = await start(
            image_detail.image_detail_main,
            params,
        )
        result = await start(
            image_detail.image_detail_details,
            image_detail.ImageDetailDetailsParams(
                **params.__dict__,
                main_response=main_response,
            ),
        )
        await self.submit(activity, result)

    @instrument
    async def image_detail_basic(self, file):
        activity = "image-detail-basic"
        # convert image to PNG first
        png = await start(
            image.thumbnail,
            image.ThumbnailParams(file, size=(1024, 1024)),
        )
        params = image_detail.ImageDetailParams(png, **self.request.get("params", {}).get(activity, {}))
        main_result = await start(image_detail.image_detail_basic_main, params)
        details_result = await start(image_detail.image_detail_basic_details, params)
        tags_result = await start(image_detail.image_detail_basic_tags, params)
        result = {
            "title": main_result.title,
            "description": main_result.description,
            "tags": tags_result,
            "detailed_description": details_result,
        }
        await self.submit(activity, result)

    @instrument
    async def image_color_palette(self, file):
        activity = "image-color-palette"
        result = await start(
            image.color_palette,
            image.ColorPaletteParams(file, **self.request.get("params", {}).get(activity, {})),
        )
        await self.submit(activity, result)

    @instrument
    async def video_metadata(self, file):
        activity = "video-metadata"
        result = await start(video.metadata, video.MetadataParams(file))
        await self.submit(activity, result)

    @instrument
    async def video_sprite(self, file):
        activity = "video-sprite"
        metadata = await start(video.metadata, video.MetadataParams(file))
        duration = metadata["duration"]
        result = await start(
            video.sprite,
            video.SpriteParams(
                file,
                duration,
                **self.request.get("params", {}).get(activity, {}),
            ),
        )
        result["files"] = await asyncio.gather(
            *[start(utils.upload, utils.UploadParams(image, "image/png")) for image in result["files"]]
        )
        await self.submit(activity, result)

    @instrument
    async def video_transcode(self, file):
        activity = "video-transcode"
        params = video.TranscodeParams(
            file,
            **self.request.get("params", {}).get(activity, {}),
        )
        path = await start(video.transcode, params, start_to_close_timeout=timedelta(minutes=30))
        mimetype = f"video/{params.container}"
        result = await start(utils.upload, utils.UploadParams(path, mimetype))
        await self.submit(activity, result)

    @instrument
    async def audio_waveform(self, file):
        activity = "audio-waveform"
        result = await start(
            video.waveform,
            video.WaveformParams(file, **self.request.get("params", {}).get(activity, {})),
        )
        await self.submit(activity, result)

    @instrument
    async def document_thumbnail(self, file):
        activity = "document-thumbnail"
        # convert the document to PDF
        pdf = await start(document.to_pdf, document.ToPdfParams(file))
        # extract thumbnails from pdf pages
        images = await start(
            document.thumbnail,
            document.ThumbnailParams(
                pdf,
                **self.request.get("params", {}).get(activity, {}),
            ),
        )
        # upload thumbnails
        result = await asyncio.gather(
            *[start(utils.upload, utils.UploadParams(image, "image/png")) for image in images]
        )
        await self.submit(activity, result)

    @instrument
    async def font_thumbnail(self, file):
        activity = "font-thumbnail"
        image = await start(
            font.thumbnail,
            font.ThumbnailParams(
                file,
                **self.request.get("params", {}).get(activity, {}),
            ),
        )
        result = await start(utils.upload, utils.UploadParams(image, "image/png"))
        await self.submit(activity, result)

    @instrument
    async def font_metadata(self, file):
        activity = "font-metadata"
        result = await start(
            font.metadata,
            font.MetadataParams(file, **self.request.get("params", {}).get(activity, {})),
        )
        await self.submit(activity, result)

    @instrument
    async def font_detail(self, file):
        activity = "font-detail"
        image = await start(font.thumbnail, font.ThumbnailParams(file))
        metadata = await start(font.metadata, font.MetadataParams(file))
        basic_info = {
            "name": metadata["full_name"],
            "designer": metadata["designer"],
            "description": metadata["description"],
            "supports_kerning": metadata["kerning"],
            "supports_chinese": metadata["chinese"],
        }
        result = await start(
            font.detail,
            font.DetailParams(
                file=image,
                basic_info=basic_info,
                **self.request.get("params", {}).get(activity, {}),
            ),
        )
        await self.submit(activity, result)

    @instrument
    async def c4d_preview(self):
        activity = "c4d-preview"
        result = await start(
            "c4d-preview",
            {"url": self.request["file"]},
            task_queue="media-c4d",
            start_to_close_timeout=timedelta(minutes=15),
        )
        await self.submit(activity, result)


@workflow.defn(name="color-calibrate")
class ColorCalibrate:
    @instrument
    @workflow.run
    async def run(self, colors):
        return await start("calibrate", colors)


@workflow.defn(name="webhook")
class Webhook:
    @instrument
    @workflow.run
    async def run(self, params):
        await start(utils.webhook, params, task_queue="webhook")
