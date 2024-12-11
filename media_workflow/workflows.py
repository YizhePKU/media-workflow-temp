import asyncio
import functools
import inspect
import sys
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from media_workflow.utils import get_worker_specific_task_queue


start = functools.partial(
    workflow.start_activity,
    task_queue=get_worker_specific_task_queue(),
    schedule_to_close_timeout=timedelta(minutes=20),
    start_to_close_timeout=timedelta(minutes=5),
)


# @workflow.defn(name="font-detail")
# class FontDetail:
#     @workflow.run
#     async def run(self, params):
#         image = await start("font_thumbnail", params)
#         meta = await start("font_metadata", params)
#         basic_info = {
#             "name": meta["full_name"],
#             "designer": meta["designer"],
#             "description": meta["description"],
#             "supports_kerning": meta["kerning"],
#             "supports_chinese": meta["chinese"],
#         }
#         result = await start(
#             "font_detail",
#             {**params, "file": image, "basic_info": json_dumps(basic_info)},
#         )
#         result["id"] = workflow.info().workflow_id
#         if callback_url := params.get("callback_url"):
#             await start("callback", args=[callback_url, result])
#         return result


# @workflow.defn(name="image-detail-basic")
# class ImageDetailBasic:
#     @workflow.run
#     async def run(self, params):
#         basic = await start("image_analysis_basic", params)
#         tags = await start("image_analysis_tags", params)
#         details = await start("image_analysis_details", params)
#         result = {
#             "id": workflow.info().workflow_id,
#             "title": basic["title"],
#             "description": basic["description"],
#             "tags": ",".join(value for values in tags.values() for value in values),
#             "detailed_description": [{k: v} for k, v in details.items()],
#         }
#         if callback_url := params.get("callback_url"):
#             await start("callback", args=[callback_url, result])
#         return result


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
        file = await start(
            "download", request["file"], heartbeat_timeout=timedelta(seconds=10)
        )

        async with asyncio.TaskGroup() as tg:
            if "image-thumbnail" in request["activities"]:
                tg.create_task(self.image_thumbnail(file, request))
            if "image-detail" in request["activities"]:
                tg.create_task(self.image_detail(file, request))
            if "image-color-palette" in request["activities"]:
                tg.create_task(self.image_color_palette(file, request))
            if "video-transcode" in request["activities"]:
                tg.create_task(self.video_transcode(file, request))
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
        file = await start("image-thumbnail", {"file": file})
        # dify wants remote image URL
        url = await start("upload", args=[file, "image/png"])
        params = {
            "url": url,
            **request.get("params", {}).get(activity, {}),
        }
        result = await start(activity, params)
        await self.submit(activity, request, result)

    async def image_color_palette(self, file, request):
        activity = "image-color-palette"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        result = await start(activity, params)
        await self.submit(activity, request, result)

    async def video_transcode(self, file, request):
        activity = "video-transcode"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        path = await start(activity, params)
        mimetype = f"video/{params.get("container", "mp4")}"
        result = await start("upload", args=[path, mimetype])
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
        activity = "font-thumbnail"
        params = {
            "file": file,
            **request.get("params", {}).get(activity, {}),
        }
        result = await start(activity, params)
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
