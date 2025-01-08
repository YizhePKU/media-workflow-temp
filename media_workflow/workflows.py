import asyncio
import functools
from datetime import timedelta
from pathlib import Path

from pydantic import BaseModel
from temporalio import workflow

from media_workflow.activities import (
    document,
    image,
    utils,
    video,
)
from media_workflow.activities.font_detail import FontDetailParams, font_detail
from media_workflow.activities.font_metadata import FontMetadataParams, font_metadata
from media_workflow.activities.font_thumbnail import FontThumbnailParams, font_thumbnail
from media_workflow.activities.image_detail import (
    ImageDetailDetailsParams,
    ImageDetailMainParams,
    image_detail_details,
    image_detail_main,
)
from media_workflow.activities.image_detail_basic import (
    ImageDetailBasicParams,
    image_detail_basic_details,
    image_detail_basic_main,
    image_detail_basic_tags,
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

    # TODO: get rid of this, pass params directly to methods like image_thumbnail()
    def _params(self, activity):
        return self.request.get("params", {}).get(activity, {})

    @instrument
    @workflow.update
    async def get(self, key):
        await workflow.wait_condition(lambda: key in self.results)
        return self.results[key]

    @instrument
    @workflow.run
    async def run(self, request):
        self.request = request

        file = await workflow.start_activity(
            utils.download,
            utils.DownloadParams(url=request["file"]),
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
                tg.create_task(self._font_thumbnail(file))
            if "font-metadata" in request["activities"]:
                tg.create_task(self._font_metadata(file))
            if "font-detail" in request["activities"]:
                tg.create_task(self._font_detail(file))
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
                file=file,
                **self._params(activity),
            ),
        )
        result = await start(utils.upload, utils.UploadParams(file=file, content_type="image/png"))
        await self.submit(activity, result)

    @instrument
    async def image_detail(self, file):
        activity = "image-detail"
        png = await start(image.thumbnail, image.ThumbnailParams(file=file, size=(1024, 1024)))

        # extract title, description, main/sub category, and tags
        main_response = await start(
            image_detail_main,
            ImageDetailMainParams(
                file=png,
                language=self._params(activity)["language"],
                industries=self._params(activity)["industries"],
            ),
        )

        # extract details from aspects derived from main/sub category
        details_response = await start(
            image_detail_details,
            ImageDetailDetailsParams(
                file=png,
                main_category=main_response.main_category,
                sub_category=main_response.sub_category,
                language=self._params(activity)["language"],
            ),
        )
        result = {
            "title": main_response.title,
            "description": main_response.description,
            "tags": [tag for tags in main_response.tags.values() for tag in tags],
            "detailed_description": [{key: value} for key, value in details_response.model_dump().items()],
        }
        await self.submit(activity, result)

    @instrument
    async def image_detail_basic(self, file):
        activity = "image-detail-basic"
        png = await start(image.thumbnail, image.ThumbnailParams(file=file, size=(1024, 1024)))

        # TODO: handle optional arguments
        params = ImageDetailBasicParams(
            file=png,
            language=self._params(activity)["language"],
            model_type=self._params(activity)["model_type"],
        )
        main = start(image_detail_basic_main, params)
        details = start(image_detail_basic_details, params)
        tags = start(image_detail_basic_tags, params)
        [main, details, tags] = await asyncio.gather(main, details, tags)
        result = {
            "title": main.title,
            "description": main.description,
            "tags": tags.model_dump(),
            "detailed_description": details.model_dump(),
        }
        await self.submit(activity, result)

    @instrument
    async def image_color_palette(self, file):
        activity = "image-color-palette"
        result = await start(
            image.color_palette,
            image.ColorPaletteParams(file=file, **self._params(activity)),
        )
        await self.submit(activity, result)

    @instrument
    async def video_metadata(self, file):
        activity = "video-metadata"
        result = await start(video.metadata, video.MetadataParams(file=file))
        await self.submit(activity, result)

    @instrument
    async def video_sprite(self, file):
        activity = "video-sprite"
        metadata = await start(video.metadata, video.MetadataParams(file=file))
        duration = metadata["duration"]
        result = await start(
            video.sprite,
            video.SpriteParams(
                file=file,
                duration=duration,
                **self._params(activity),
            ),
        )
        result["files"] = await asyncio.gather(
            *[
                start(utils.upload, utils.UploadParams(file=image, content_type="image/png"))
                for image in result["files"]
            ]
        )
        await self.submit(activity, result)

    @instrument
    async def video_transcode(self, file):
        activity = "video-transcode"
        params = video.TranscodeParams(
            file=file,
            **self._params(activity),
        )
        path = await start(video.transcode, params, start_to_close_timeout=timedelta(minutes=30))
        mimetype = f"video/{params.container}"
        result = await start(utils.upload, utils.UploadParams(file=path, content_type=mimetype))
        await self.submit(activity, result)

    @instrument
    async def audio_waveform(self, file):
        activity = "audio-waveform"
        result = await start(
            video.waveform,
            video.WaveformParams(file=file, **self._params(activity)),
        )
        await self.submit(activity, result)

    @instrument
    async def document_thumbnail(self, file):
        activity = "document-thumbnail"
        # convert the document to PDF
        pdf = await start(document.to_pdf, document.ToPdfParams(file=file))
        # extract thumbnails from pdf pages
        images = await start(
            document.thumbnail,
            document.ThumbnailParams(
                file=pdf,
                **self._params(activity),
            ),
        )
        # upload thumbnails
        result = await asyncio.gather(
            *[start(utils.upload, utils.UploadParams(file=image, content_type="image/png")) for image in images]
        )
        await self.submit(activity, result)

    # TODO: make all these methods private to prevent name clash
    @instrument
    async def _font_thumbnail(self, file):
        activity = "font-thumbnail"
        image = await start(font_thumbnail, FontThumbnailParams(file=file, **self._params(activity)))
        result = await start(utils.upload, utils.UploadParams(file=image, content_type="image/png"))
        await self.submit(activity, result)

    @instrument
    async def _font_metadata(self, file):
        activity = "font-metadata"
        result = await start(font_metadata, FontMetadataParams(file=file, **self._params(activity)))
        await self.submit(activity, result)

    @instrument
    async def _font_detail(self, file):
        activity = "font-detail"
        image = await start(font_thumbnail, FontThumbnailParams(file=file))
        metadata = await start(font_metadata, FontMetadataParams(file=file))
        basic_info = {
            "name": metadata["full_name"],
            "designer": metadata["designer"],
            "description": metadata["description"],
            "supports_kerning": metadata["kerning"],
            "supports_chinese": metadata["chinese"],
        }
        result = await start(font_detail, FontDetailParams(file=image, basic_info=basic_info, **self._params(activity)))
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


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, person):
        return person


class Person(BaseModel):
    name: str
    path: Path
