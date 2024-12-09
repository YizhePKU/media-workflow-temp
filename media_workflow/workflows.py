import asyncio
import functools
import inspect
import sys
from datetime import timedelta
from json import dumps as json_dumps

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from media_workflow.activities import names as all_activities
    from media_workflow.utils import get_worker_specific_task_queue


start = functools.partial(
    workflow.start_activity,
    task_queue=get_worker_specific_task_queue(),
    schedule_to_close_timeout=timedelta(minutes=20),
    start_to_close_timeout=timedelta(minutes=5),
)


@workflow.defn(name="font-detail")
class FontDetail:
    @workflow.run
    async def run(self, params):
        image = await start("font_thumbnail", params)
        meta = await start("font_metadata", params)
        basic_info = {
            "name": meta["full_name"],
            "designer": meta["designer"],
            "description": meta["description"],
            "supports_kerning": meta["kerning"],
            "supports_chinese": meta["chinese"],
        }
        result = await start(
            "font_detail",
            {**params, "file": image, "basic_info": json_dumps(basic_info)},
        )
        result["id"] = workflow.info().workflow_id
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="image-detail-basic")
class ImageDetailBasic:
    @workflow.run
    async def run(self, params):
        basic = await start("image_analysis_basic", params)
        tags = await start("image_analysis_tags", params)
        details = await start("image_analysis_details", params)
        result = {
            "id": workflow.info().workflow_id,
            "title": basic["title"],
            "description": basic["description"],
            "tags": ",".join(value for values in tags.values() for value in values),
            "detailed_description": [{k: v} for k, v in details.items()],
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="file-analysis")
class FileAnalysis:
    @workflow.run
    async def run(self, request):
        id = workflow.info().workflow_id
        file = await start("download", request["file"])
        params = request.get("params", {})

        # TODO: filter down activities based on file type
        activities = request.get("activities", all_activities)

        # post-process result from activities
        postprocess = {
            "image-thumbnail": lambda path: start("upload", args=[path, "image/png"])
        }

        async def run_activity_with_callback(activity):
            result = await start(activity, {"file": file, **params.get(activity, {})})
            if fn := postprocess.get(activity):
                result = await fn(result)
            if callback := request.get("callback"):
                data = {"id": id, "request": request, "result": {activity: result}}
                await start("callback", args=[callback, data])
            return result

        tasks = [run_activity_with_callback(activity) for activity in activities]
        results = await asyncio.gather(*tasks)

        return {
            "id": id,
            "request": request,
            "result": dict(zip(activities, results)),
        }


workflows = []
for _name, fn in inspect.getmembers(sys.modules[__name__]):
    if hasattr(fn, "__temporal_workflow_definition"):
        workflows.append(fn)
