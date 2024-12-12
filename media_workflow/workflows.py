import asyncio
import functools
import inspect
import sys
from datetime import timedelta
from json import dumps as json_dumps

from temporalio import workflow


with workflow.unsafe.imports_passed_through():
    import media_workflow.activities.video as video
    from media_workflow.activities.video import SpriteParams

start = functools.partial(
    workflow.start_activity,
    start_to_close_timeout=timedelta(minutes=5),
    schedule_to_close_timeout=timedelta(minutes=20),
)


@workflow.defn(name="file-analysis")
class FileAnalysis:
    def __init__(self):
        self.results = {}

    @workflow.update
    async def get(self, key):
        await workflow.wait_condition(lambda: key in self.results)
        return self.results[key]

    @workflow.run
    async def run(self, request):
        try:
            file = await start(
                "download",
                request["file"],
                heartbeat_timeout=timedelta(minutes=1),
                start_to_close_timeout=timedelta(minutes=30),
                schedule_to_close_timeout=timedelta(minutes=60),
            )

            async with asyncio.TaskGroup() as tg:
                if "image-thumbnail" in request["activities"]:
                    tg.create_task(self.image_thumbnail(file, request))
                if "image-detail" in request["activities"]:
                    tg.create_task(self.image_detail(file, request))
                if "image-detail-basic" in request["activities"]:
                    tg.create_task(self.image_detail_basic(file, request))
                if "image-color-palette" in request["activities"]:
                    tg.create_task(self.image_color_palette(file, request))
                if "video-metadata" in request["activities"]:
                    tg.create_task(self.video_metadata(file, request))
                if "video-sprite" in request["activities"]:
                    tg.create_task(self.video_sprite(file, request))
                if "video-transcode" in request["activities"]:
                    tg.create_task(self.video_transcode(file, request))
                if "audio-waveform" in request["activities"]:
                    tg.create_task(self.audio_waveform(file, request))
                if "document-thumbnail" in request["activities"]:
                    tg.create_task(self.document_thumbnail(file, request))
                if "font-thumbnail" in request["activities"]:
                    tg.create_task(self.font_thumbnail(file, request))
                if "font-metadata" in request["activities"]:
                    tg.create_task(self.font_metadata(file, request))
                if "font-detail" in request["activities"]:
                    tg.create_task(self.font_detail(file, request))

            return {
                "id": workflow.info().workflow_id,
                "request": request,
                "result": self.results,
            }

        # If the workflow timeout, report the error via callback
        except Exception as err:
            if callback := request.get("callback"):
                data = {
                    "id": workflow.info().workflow_id,
                    "request": request,
                    "error": str(err),
                }
                await start("callback", args=[callback, data])
            raise

    async def submit(self, activity, request, result):
        self.results[activity] = result
        if callback := request.get("callback"):
            response = {
                "id": workflow.info().workflow_id,
                "request": request,
                "result": {
                    activity: result,
                },
            }
            await start("callback", args=[callback, response])

    async def image_thumbnail(self, file, request):
        activity = "image-thumbnail"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        file = await start(activity, params)
        result = await start("upload", args=[file, "image/png"])
        await self.submit(activity, request, result)

    async def image_detail(self, file, request):
        activity = "image-detail"
        # convert image to PNG first
        file = await start("image-thumbnail", {"file": file, "size": [1000, 1000]})
        url = await start("upload", args=[file, "image/png"])
        params = {
            "url": url,
            **request.get("params", {}).get(activity, {}),
        }
        result = await start(activity, params)
        await self.submit(activity, request, result)

    async def image_detail_basic(self, file, request):
        activity = "image-detail-basic"
        # convert image to PNG first
        image = await start("image-thumbnail", {"file": file, "size": [1000, 1000]})
        # invoke minicpm three times
        params = {"file": image, **request.get("params", {}).get(activity, {})}
        basic = await start("image-analysis-basic", params)
        tags = await start("image-analysis-tags", params)
        details = await start("image-analysis-details", params)
        result = {
            "title": basic["title"],
            "description": basic["description"],
            "tags": ",".join(value for values in tags.values() for value in values),
            "detailed_description": [{k: v} for k, v in details.items()],
        }
        await self.submit(activity, request, result)

    async def image_color_palette(self, file, request):
        activity = "image-color-palette"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        result = await start(activity, params)
        await self.submit(activity, request, result)

    async def video_metadata(self, file, request):
        activity = "video-metadata"
        result = await start(video.metadata, video.MetadataParams(file))
        await self.submit(activity, request, result)

    async def video_sprite(self, file, request):
        activity = "video-sprite"
        metadata = await start(video.metadata, video.MetadataParams(file))
        duration = metadata["duration"]
        images = await start(
            video.sprite,
            SpriteParams(file, duration, **request.get("params", {}).get(activity, {})),
        )
        result = await asyncio.gather(
            *[start("upload", args=[image, "image/png"]) for image in images]
        )
        await self.submit(activity, request, result)

    async def video_transcode(self, file, request):
        activity = "video-transcode"
        params = video.TranscodeParams(
            file, **request.get("params", {}).get(activity, {})
        )
        path = await start(video.transcode, params)
        mimetype = f"video/{params.container}"
        result = await start("upload", args=[path, mimetype])
        await self.submit(activity, request, result)

    async def audio_waveform(self, file, request):
        activity = "audio-waveform"
        result = await start(
            video.waveform,
            video.WaveformParams(file, **request.get("params", {}).get(activity, {})),
        )
        await self.submit(activity, request, result)

    async def document_thumbnail(self, file, request):
        activity = "document-thumbnail"
        # convert the document to PDF
        params = {
            "file": file,
        }
        pdf = await start("convert-to-pdf", params)
        # extract thumbnails from pdf pages
        params = {
            "file": pdf,
            **request.get("params", {}).get(activity, {}),
        }
        images = await start("pdf-thumbnail", params)
        # upload thumbnails
        result = await asyncio.gather(
            *[start("upload", args=[image, "image/png"]) for image in images]
        )
        await self.submit(activity, request, result)

    async def font_thumbnail(self, file, request):
        activity = "font-thumbnail"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        image = await start(activity, params)
        result = await start("upload", args=[image, "image/png"])
        await self.submit(activity, request, result)

    async def font_metadata(self, file, request):
        activity = "font-metadata"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        result = await start(activity, params)
        await self.submit(activity, request, result)

    async def font_detail(self, file, request):
        activity = "font-detail"
        image = await start("font-thumbnail", {"file": file})
        image_url = await start("upload", image)
        meta = await start("font-metadata", {"file": file})
        basic_info = {
            "name": meta["full_name"],
            "designer": meta["designer"],
            "description": meta["description"],
            "supports_kerning": meta["kerning"],
            "supports_chinese": meta["chinese"],
        }
        params = {
            "url": image_url,
            "basic_info": json_dumps(basic_info),
            "language": "Simplified Chinese",
            **request.get("params", {}).get(activity, {}),
        }
        result = await start("font-detail", params)
        await self.submit(activity, request, result)


@workflow.defn(name="color-calibrate")
class ColorCalibrate:
    @workflow.run
    async def run(self, colors):
        return await start("calibrate", colors)


workflows = []
for _name, fn in inspect.getmembers(sys.modules[__name__]):
    if hasattr(fn, "__temporal_workflow_definition"):
        workflows.append(fn)
