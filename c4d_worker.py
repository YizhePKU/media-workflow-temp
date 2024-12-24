import asyncio
import json
import os
import socket
from dataclasses import dataclass

from temporalio import activity
from temporalio.worker import Worker

from media_workflow.activities import utils
from media_workflow.client import get_client
from media_workflow.trace import tracer


@dataclass
class PreviewParams:
    url: str


@activity.defn(name="c4d-preview")
async def c4d_preview(params: PreviewParams):
    with tracer.start_as_current_span("c4d-download"):
        file = await utils.download(utils.DownloadParams(params.url))

    host = os.environ.get("C4D_SERVER_HOST", "localhost")
    port = os.environ.get("C4D_SERVER_PORT", 8848)
    with tracer.start_as_current_span("c4d-server", attributes={"host": host, "port": port}):
        with socket.create_connection((host, port)) as conn:
            conn.send(json.dumps(file).encode())
            response = json.loads(conn.recv(1000))  # TODO: make this async
            if response["status"] != "success":
                reason = response["reason"]
                raise ValueError(f"C4D server returned error: {reason}")

    with tracer.start_as_current_span("c4d-upload", attributes={"png": response["png"], "gltf": response["gltf"]}):
        png_task = utils.upload(utils.UploadParams(response["png"], "image/png"))
        gltf_task = utils.upload(utils.UploadParams(response["gltf"]))
        (png_url, gltf_url) = await asyncio.gather(png_task, gltf_task)

    return {"gltf": gltf_url, "png": png_url}


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await get_client()
    worker = Worker(
        client,
        task_queue="media-c4d",
        activities=[c4d_preview],
    )
    print("starting C4D worker on task queue media-c4d")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
