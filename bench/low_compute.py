import asyncio
from time import time
from media_workflow.worker import get_client
from uuid import uuid4

images = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/apartment.hdr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/cmyk.jpeg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/cocktail.svg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/fei.psb",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/flowers.exr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/golden-gate.exr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/hackson.heic",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.psd",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.svg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/water-girl.jpeg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/float.tiff",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.jpeg",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.psd",
]
documents = [
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/bill.cdr",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/MuseDam.key",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/dam.docx",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/materials.xlsx",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/multipage.ai",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/nova.key",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.ai",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.eps",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.pdf",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/sample.pptx",
    "https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/large.pptx",
]

sets = 1
total = (len(images) + len(documents)) * sets
completed = 0


def increment():
    global completed
    completed += 1
    print(f"Progress: {completed}/{total}")


async def image_thumbnail(client, image):
    params = {
        "file": image,
        "activities": ["image-thumbnail"],
        "params": {"image-thumbnail": {"size": [400, 400]}},
    }
    await client.execute_workflow(
        "file-analysis", params, id=str(uuid4()), task_queue="media"
    )
    increment()


async def document_thumbnail(client, document):
    params = {
        "file": document,
        "activities": ["document-thumbnail"],
        "params": {"document-thumbnail": {"size": [400, 400], "pages": [0]}},
    }
    await client.execute_workflow(
        "file-analysis", params, id=str(uuid4()), task_queue="media"
    )
    increment()


async def main():
    client = await get_client()

    tasks = []
    for _ in range(sets):
        for image in images:
            tasks.append(image_thumbnail(client, image))
        for document in documents:
            tasks.append(document_thumbnail(client, document))

    print(f"Starting {total} tasks")
    start = time()
    await asyncio.gather(*tasks)
    end = time()
    print(f"{completed}/{total} tasks completed, time = {end - start}")


if __name__ == "__main__":
    asyncio.run(main())
