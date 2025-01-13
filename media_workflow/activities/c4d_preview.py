import asyncio
import json
import os

from pydantic import BaseModel
from temporalio import activity

from media_workflow.activities.download import DownloadParams, download
from media_workflow.activities.upload import UploadParams, upload
from media_workflow.otel import tracer


class C4dPreviewParams(BaseModel):
    url: str


@activity.defn(name="c4d-preview")
async def c4d_preview(params: C4dPreviewParams):
    with tracer.start_as_current_span("c4d-download"):
        file = await download(DownloadParams(url=params.url))

    host = os.environ.get("C4D_SERVER_HOST", "localhost")
    port = os.environ.get("C4D_SERVER_PORT", 8848)
    with tracer.start_as_current_span("c4d-server", attributes={"host": host, "port": port}):
        (reader, writer) = await asyncio.open_connection(host, port)
        writer.write(json.dumps(file).encode())
        await writer.drain()

        response = json.loads(await reader.read(-1))
        if response["status"] != "success":
            reason = response["reason"]
            raise ValueError(f"C4D server returned error: {reason}")

        writer.close()

    with tracer.start_as_current_span("c4d-upload", attributes={"png": response["png"], "gltf": response["gltf"]}):
        png_task = upload(UploadParams(file=response["png"], content_type="image/png"))
        gltf_task = upload(UploadParams(file=response["gltf"]))
        (png_url, gltf_url) = await asyncio.gather(png_task, gltf_task)

    return {"gltf": gltf_url, "png": png_url}
