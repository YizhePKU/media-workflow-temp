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
