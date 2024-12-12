# Install dependencies with:
# python3 -m pip install --target /Users/tezign/Library/Preferences/MAXON/python/python311/libs
# temporalio opentelemetry-exporter-otlp-proto-http aiohttp boto3

# Then install this package as dependency too:
# cp -r media_workflow /Users/tezign/Library/Preferences/MAXON/python/python311/libs

# Finally, run with /Applications/Maxon\ Cinema\ 4D\ 2025/c4dpy.app/Contents/MacOS/c4dpy

import functools
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from uuid import uuid4

import c4d
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import Worker

with workflow.unsafe.imports_passed_through():
    from media_workflow.trace import tracer
    from media_workflow.utils import fetch, upload


start = functools.partial(
    workflow.start_activity, start_to_close_timeout=timedelta(minutes=5)
)


def prog_callback(progress: float, event):
    if event == c4d.RENDERPROGRESSTYPE_BEFORERENDERING:
        text = "Before Rendering"
    elif event == c4d.RENDERPROGRESSTYPE_DURINGRENDERING:
        text = "During Rendering"
    elif event == c4d.RENDERPROGRESSTYPE_AFTERRENDERING:
        text = "After Rendering"
    elif event == c4d.RENDERPROGRESSTYPE_GLOBALILLUMINATION:
        text = "GI"
    elif event == c4d.RENDERPROGRESSTYPE_QUICK_PREVIEW:
        text = "Quick Preview"
    elif event == c4d.RENDERPROGRESSTYPE_AMBIENTOCCLUSION:
        text = "AO"
    print("prog_callback called [{0} / p: {1}]".format(text, progress * 100.0))


def write_callback(
    mode,
    bitmap: c4d.bitmaps.BaseBitmap,
    path: str,
    is_main: bool,
    frame: int,
    render_time: int,
    streamnum: int,
    streamname: str,
):
    if mode == c4d.WRITEMODE_STANDARD:
        text = "Standard"
    elif mode == c4d.WRITEMODE_ASSEMBLE_MOVIE:
        text = "Assemble Movie"
    elif mode == c4d.WRITEMODE_ASSEMBLE_SINGLEIMAGE:
        text = "Assemble single image"
    print("write_callback called [{0} / p: {1}]".format(text, render_time))


@workflow.defn(name="c4d-preview")
class C4dPreview:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            **await start("c4d_preview", params),
        }
        return result


@activity.defn
async def c4d_preview(params):
    with TemporaryDirectory() as dir:
        stem = str(uuid4())
        _c4d = f"{dir}/{stem}.c4d"
        _gltf = f"{dir}/{stem}.gltf"
        _png = f"{dir}/{stem}.png"

        with open(_c4d, "wb") as file:
            file.write(await fetch(params["file"]))

        with tracer.start_as_current_span("c4d-load-document"):
            doc = c4d.documents.LoadDocument(_c4d, c4d.SCENEFILTER_OBJECTS)
            assert doc is not None

        with tracer.start_as_current_span("c4d-export-gltf"):
            c4d.documents.SaveDocument(doc, _gltf, 0, c4d.FORMAT_GLTFEXPORT)

        with open(_gltf, "rb") as file:
            data = file.read()
            gltf_url = upload(f"{stem}.gltf", data)

        with tracer.start_as_current_span("c4d-export-png"):
            # create a bitmap with Alpha channel
            rd = doc.GetActiveRenderData()
            bitmap = c4d.bitmaps.MultipassBitmap(
                int(rd[c4d.RDATA_XRES]), int(rd[c4d.RDATA_YRES]), c4d.COLORMODE_RGB
            )
            bitmap.AddChannel(True, True)

            # render document into the bitmap
            ret = c4d.documents.RenderDocument(
                doc,
                rd.GetData(),
                bitmap,
                c4d.RENDERFLAGS_EXTERNAL,
                prog=prog_callback,
                wprog=write_callback,
            )
            assert ret == c4d.RENDERRESULT_OK

            # save bitmap as PNG
            ret = bitmap.Save(_png, c4d.FILTER_PNG)
            assert ret == c4d.IMAGERESULT_OK

        with open(_png, "rb") as file:
            data = file.read()
            png_url = upload(f"{stem}.png", data)

        return {"gltf": gltf_url, "png": png_url}


async def get_client():
    tracing_interceptor = TracingInterceptor()
    return await Client.connect(
        os.environ["TEMPORAL_SERVER_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
        interceptors=[tracing_interceptor],
    )


async def main():
    client = await get_client()
    worker = Worker(
        client,
        task_queue="media-c4d",
        workflows=[C4dPreview],
        activities=[c4d_preview],
    )
    await worker.run()
