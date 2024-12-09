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
        id = workflow.info().workflow_id
        file = await start(
            "download", request["file"], heartbeat_timeout=timedelta(seconds=10)
        )

        postprocess = {
            "image-thumbnail": lambda path: start("upload", args=[path, "image/png"]),
            "video-transcode": lambda path: start("upload", args=[path]),
        }

        async with asyncio.TaskGroup() as tg:
            for activity in request["activities"]:
                # define one task per activity
                async def task():
                    params = {
                        "file": file,
                        **request.get("params", {}).get(activity, {}),
                    }
                    result = await start(activity, params)
                    if fn := postprocess.get(activity):
                        result = await fn(result)
                    if callback := request.get("callback"):
                        await start("callback", args=[callback, result])
                    self.results[activity] = result

                tg.create_task(task())

        return {
            "id": id,
            "request": request,
            "result": self.results,
        }


@workflow.defn(name="color-calibrate")
class ColorCalibrate:
    @workflow.run
    async def run(self, colors):
        return await start("calibrate", colors)


workflows = []
for _name, fn in inspect.getmembers(sys.modules[__name__]):
    if hasattr(fn, "__temporal_workflow_definition"):
        workflows.append(fn)
