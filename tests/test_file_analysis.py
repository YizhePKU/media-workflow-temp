from uuid import uuid4

from media_workflow.activities import download
from media_workflow.utils import imread
from media_workflow.worker import get_client


async def test_file_analysis():
    client = await get_client()
    params = {
        "file": "https://sunyizhe.s3.us-west-002.backblazeb2.com/%E5%BC%B9%E6%A1%8612.psd",
    }
    output = await client.execute_workflow(
        "file-analysis", params, id=f"{uuid4()}", task_queue="media"
    )
    image = imread(await download(output["result"]["image-thumbnail"]))
    assert image.mode == "RGB"
