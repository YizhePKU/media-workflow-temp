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
from media_workflow.otel import instrument

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
        """The main entrypoint of the application."""
        self.request = request

        file = await start(
            download,
            DownloadParams(url=request["file"]),
            start_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(seconds=30),
        )

        # Dispatch tasks to workflow code.
        activity2fn = {
            "audio-waveform": self._audio_waveform,
            "c4d-preview": self._c4d_preview,
            "document-thumbnail": self._document_thumbnail,
            "font-detail": self._font_detail,
            "font-metadata": self._font_metadata,
            "font-thumbnail": self._font_thumbnail,
            "image-color-palette": self._image_color_palette,
            "image-detail-basic": self._image_detail_basic,
            "image-detail": self._image_detail,
            "image-thumbnail": self._image_thumbnail,
            "video-metadata": self._video_metadata,
            "video-sprite": self._video_sprite,
            "video-transcode": self._video_transcode,
        }

        # Start all tasks in the background concurrently.
        async with asyncio.TaskGroup() as tg:
            for activity in request["activities"]:
                assert activity in activity2fn

                async def task(activity):
                    params = request.get("params", {}).get(activity, {})
                    self.results[activity] = await activity2fn[activity](file, params)
                    if url := request.get("callback"):
                        await workflow.start_child_workflow(
                            Webhook.run,
                            WebhookParams(
                                url=url,
                                msg_id=str(workflow.uuid4()),
                                payload={
                                    "id": workflow.info().workflow_id,
                                    "request": request,
                                    "result": {activity: self.results[activity]},
                                },
                            ),
                            task_queue="webhook",
                            parent_close_policy=workflow.ParentClosePolicy.ABANDON,
                        )

                tg.create_task(task(activity))

        return {
            "id": workflow.info().workflow_id,
            "request": request,
            "result": self.results,
        }

    @instrument
    async def _image_thumbnail(self, file, params):
        thumbnail = await start(image_thumbnail, ImageThumbnailParams(file=file, **params))
        return await start(upload, UploadParams(file=thumbnail, content_type="image/jpeg"))

    @instrument
    async def _image_detail(self, file, params):
        # convert image to jpeg
        thumbnail = await start(image_thumbnail, ImageThumbnailParams(file=file, size=(1024, 1024)))
        # extract title, description, main/sub category, and tags
        main = await start(image_detail_main, ImageDetailMainParams(file=thumbnail, **params))
        # extract details from aspects derived from main/sub category
        details = await start(
            image_detail_details,
            ImageDetailDetailsParams(
                file=thumbnail, main_category=main.main_category, sub_category=main.sub_category, **params
            ),
        )
        return {
            "title": main.title,
            "description": main.description,
            "tags": [tag for tags in main.tags.values() for tag in tags],
            "detailed_description": [{key: value} for key, value in details.model_dump().items()],
        }

    @instrument
    async def _image_detail_basic(self, file, params):
        # convert image to jpeg
        thumbnail = await start(image_thumbnail, ImageThumbnailParams(file=file, size=(1024, 1024)))
        # invoke LLM three times
        params = ImageDetailBasicParams(file=thumbnail, **params)
        main = start(image_detail_basic_main, params)
        details = start(image_detail_basic_details, params)
        tags = start(image_detail_basic_tags, params)
        [main, details, tags] = await asyncio.gather(main, details, tags)
        return {
            "title": main.title,
            "description": main.description,
            "tags": tags.model_dump(),
            "detailed_description": details.model_dump(),
        }

    @instrument
    async def _image_color_palette(self, file, params):
        thumbnail = await start(image_thumbnail, ImageThumbnailParams(file=file, size=(1000, 1000)))
        return await start(image_color_palette, ImageColorPaletteParams(file=thumbnail, **params))

    @instrument
    async def _video_metadata(self, file, params):
        return await start(video_metadata, VideoMetadataParams(file=file, **params))

    @instrument
    async def _video_sprite(self, file, params):
        metadata = await start(video_metadata, VideoMetadataParams(file=file, **params))
        result = await start(video_sprite, VideoSpriteParams(file=file, duration=metadata["duration"], **params))
        files = await asyncio.gather(
            *[start(upload, UploadParams(file=image, content_type="image/jpeg")) for image in result["sprites"]]
        )
        return {
            "interval": result["interval"],
            "width": result["width"],
            "height": result["height"],
            "files": files,
        }

    @instrument
    async def _video_transcode(self, file, params):
        params = VideoTranscodeParams(file=file, **params)
        transcoded = await start(video_transcode, params, start_to_close_timeout=timedelta(minutes=30))
        return await start(upload, UploadParams(file=transcoded, content_type=f"video/{params.container}"))

    @instrument
    async def _audio_waveform(self, file, params):
        return await start(audio_waveform, AudioWaveformParams(file=file, **params))

    @instrument
    async def _document_thumbnail(self, file, params):
        # convert the document to PDF
        pdf = await start(document_to_pdf, DocumentToPdfParams(file=file))
        # extract thumbnails from pdf pages
        images = await start(document_thumbnail, DocumentThumbnailParams(file=pdf, **params))
        # upload thumbnails
        return await asyncio.gather(
            *[start(upload, UploadParams(file=image, content_type="image/jpeg")) for image in images]
        )

    @instrument
    async def _font_thumbnail(self, file, params):
        image = await start(font_thumbnail, FontThumbnailParams(file=file, **params))
        return await start(upload, UploadParams(file=image, content_type="image/jpeg"))

    @instrument
    async def _font_metadata(self, file, params):
        return await start(font_metadata, FontMetadataParams(file=file, **params))

    @instrument
    async def _font_detail(self, file, params):
        image = await start(font_thumbnail, FontThumbnailParams(file=file))
        metadata = await start(font_metadata, FontMetadataParams(file=file))
        basic_info = {
            "name": metadata["full_name"],
            "designer": metadata["designer"],
            "description": metadata["description"],
            "supports_kerning": metadata["kerning"],
            "supports_chinese": metadata["chinese"],
        }
        return await start(font_detail, FontDetailParams(file=image, basic_info=basic_info, **params))

    @instrument
    async def _c4d_preview(self, file, params):
        return await start(
            "c4d-preview",
            {"url": self.request["file"]},
            task_queue="media-c4d",
        )


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
        await start(webhook, params)
