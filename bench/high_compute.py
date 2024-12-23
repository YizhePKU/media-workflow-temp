import asyncio
from time import time
from uuid import uuid4

from media_workflow.client import get_client

videos = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.mp4",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/dream.mkv",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/dream.webm",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/ocean.rm",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.avi",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/surfing.ts",
]

sets = 4
total = (len(videos)) * sets
completed = 0


def increment():
    global completed
    completed += 1
    print(f"Progress: {completed}/{total}")


async def process(client, video):
    params = {
        "file": video,
        "activities": ["video-thumbnail", "video-transcode"],
    }
    await client.execute_workflow("file-analysis", params, id=str(uuid4()), task_queue="media")
    increment()


async def main():
    client = await get_client()

    tasks = []
    for _ in range(sets):
        for video in videos:
            tasks.append(process(client, video))

    print(f"Starting {total} tasks")
    start = time()
    await asyncio.gather(*tasks)
    end = time()
    print(f"{completed}/{total} tasks completed, time = {end - start}")


if __name__ == "__main__":
    asyncio.run(main())
