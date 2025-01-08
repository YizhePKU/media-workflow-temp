import asyncio
import functools
from datetime import timedelta

from temporalio import workflow

from media_workflow.activities.audio_waveform import AudioWaveformParams, audio_waveform
from media_workflow.activities.color_calibrate import color_calibrate
from media_workflow.activities.document_thumbnail import DocumentThumbnailParams, document_thumbnail
from media_workflow.activities.document_to_pdf import DocumentToPdfParams, document_to_pdf
from media_workflow.activities.download import DownloadParams, download
from media_workflow.activities.font_detail import FontDetailParams, font_detail
from media_workflow.activities.font_metadata import FontMetadataParams, font_metadata
from media_workflow.activities.font_thumbnail import FontThumbnailParams, font_thumbnail
from media_workflow.activities.image_color_palette import ImageColorPaletteParams, image_color_palette
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
from media_workflow.activities.image_thumbnail import ImageThumbnailParams, image_thumbnail
from media_workflow.activities.upload import UploadParams, upload
from media_workflow.activities.video_metadata import VideoMetadataParams, video_metadata
from media_workflow.activities.video_sprite import VideoSpriteParams, video_sprite
from media_workflow.activities.video_transcode import VideoTranscodeParams, video_transcode
from media_workflow.activities.webhook import WebhookParams, webhook
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

        file = await start(
            download,
            DownloadParams(url=request["file"]),
            start_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(seconds=30),
        )

        async with asyncio.TaskGroup() as tg:
            if "image-thumbnail" in request["activities"]:
                tg.create_task(self._image_thumbnail(file))
            if "image-detail" in request["activities"]:
                tg.create_task(self._image_detail(file))
            if "image-detail-basic" in request["activities"]:
                tg.create_task(self._image_detail_basic(file))
            if "image-color-palette" in request["activities"]:
                tg.create_task(self._image_color_palette(file))
            if "video-metadata" in request["activities"]:
                tg.create_task(self._video_metadata(file))
            if "video-sprite" in request["activities"]:
                tg.create_task(self._video_sprite(file))
            if "video-transcode" in request["activities"]:
                tg.create_task(self._video_transcode(file))
            if "audio-waveform" in request["activities"]:
                tg.create_task(self._audio_waveform(file))
            if "document-thumbnail" in request["activities"]:
                tg.create_task(self._document_thumbnail(file))
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
            params = WebhookParams(
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
    async def _image_thumbnail(self, file):
        activity = "image-thumbnail"
        file = await start(image_thumbnail, ImageThumbnailParams(file=file, **self._params(activity)))
        result = await start(upload, UploadParams(file=file, content_type="image/png"))
        await self.submit(activity, result)

    @instrument
    async def _image_detail(self, file):
        activity = "image-detail"
        png = await start(image_thumbnail, ImageThumbnailParams(file=file, size=(1024, 1024)))

        # extract title, description, main/sub category, and tags
        main_response = await start(image_detail_main, ImageDetailMainParams(file=png, **self._params(activity)))

        # extract details from aspects derived from main/sub category
        details_response = await start(
            image_detail_details,
            ImageDetailDetailsParams(
                file=png,
                main_category=main_response.main_category,
                sub_category=main_response.sub_category,
                **self._params(activity),
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
    async def _image_detail_basic(self, file):
        activity = "image-detail-basic"
        png = await start(image_thumbnail, ImageThumbnailParams(file=file, size=(1024, 1024)))

        params = ImageDetailBasicParams(file=png, **self._params(activity))
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
    async def _image_color_palette(self, file):
        activity = "image-color-palette"
        result = await start(image_color_palette, ImageColorPaletteParams(file=file, **self._params(activity)))
        await self.submit(activity, result)

    @instrument
    async def _video_metadata(self, file):
        activity = "video-metadata"
        result = await start(video_metadata, VideoMetadataParams(file=file))
        await self.submit(activity, result)

    @instrument
    async def _video_sprite(self, file):
        activity = "video-sprite"
        metadata = await start(video_metadata, VideoMetadataParams(file=file))
        duration = metadata["duration"]
        result = await start(video_sprite, VideoSpriteParams(file=file, duration=duration, **self._params(activity)))
        result["files"] = await asyncio.gather(
            *[start(upload, UploadParams(file=image, content_type="image/png")) for image in result["files"]]
        )
        await self.submit(activity, result)

    @instrument
    async def _video_transcode(self, file):
        activity = "video-transcode"
        params = VideoTranscodeParams(file=file, **self._params(activity))
        path = await start(video_transcode, params, start_to_close_timeout=timedelta(minutes=30))
        result = await start(upload, UploadParams(file=path, content_type=f"video/{params.container}"))
        await self.submit(activity, result)

    @instrument
    async def _audio_waveform(self, file):
        activity = "audio-waveform"
        result = await start(
            audio_waveform,
            AudioWaveformParams(file=file, **self._params(activity)),
        )
        await self.submit(activity, result)

    @instrument
    async def _document_thumbnail(self, file):
        activity = "document-thumbnail"
        # convert the document to PDF
        pdf = await start(document_to_pdf, DocumentToPdfParams(file=file))
        # extract thumbnails from pdf pages
        images = await start(document_thumbnail, DocumentThumbnailParams(file=pdf, **self._params(activity)))
        # upload thumbnails
        result = await asyncio.gather(
            *[start(upload, UploadParams(file=image, content_type="image/png")) for image in images]
        )
        await self.submit(activity, result)

    @instrument
    async def _font_thumbnail(self, file):
        activity = "font-thumbnail"
        image = await start(font_thumbnail, FontThumbnailParams(file=file, **self._params(activity)))
        result = await start(upload, UploadParams(file=image, content_type="image/png"))
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
    async def run(self, colors: list[str]) -> dict[str, str]:
        return await start(color_calibrate, colors)


@workflow.defn(name="webhook")
class Webhook:
    @instrument
    @workflow.run
    async def run(self, params: WebhookParams):
        await start(webhook, params, task_queue="webhook")
