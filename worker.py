import asyncio

from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from media_workflow.activities.audio_waveform import audio_waveform
from media_workflow.activities.blender_preview import blender_preview
from media_workflow.activities.color_calibrate import color_calibrate
from media_workflow.activities.document_to_pdf import document_to_pdf
from media_workflow.activities.download import download
from media_workflow.activities.font_detail import font_detail
from media_workflow.activities.font_metadata import font_metadata
from media_workflow.activities.font_thumbnail import font_thumbnail
from media_workflow.activities.image_color_palette import image_color_palette
from media_workflow.activities.image_detail import (
    image_detail_details,
    image_detail_main,
)
from media_workflow.activities.image_detail_basic import (
    image_detail_basic_details,
    image_detail_basic_main,
    image_detail_basic_tags,
)
from media_workflow.activities.image_thumbnail import image_thumbnail
from media_workflow.activities.pdf_thumbnail import pdf_thumbnail
from media_workflow.activities.upload import upload
from media_workflow.activities.video_metadata import video_metadata
from media_workflow.activities.video_sprite import video_sprite
from media_workflow.activities.video_thumbnail import video_thumbnail
from media_workflow.activities.video_transcode import video_transcode
from media_workflow.client import connect
from media_workflow.workflows import ColorCalibrate, FileAnalysis

workflows = [FileAnalysis, ColorCalibrate]
activities = [
    audio_waveform,
    blender_preview,
    color_calibrate,
    document_to_pdf,
    download,
    font_detail,
    font_metadata,
    font_thumbnail,
    image_color_palette,
    image_detail_basic_details,
    image_detail_basic_main,
    image_detail_basic_tags,
    image_detail_details,
    image_detail_main,
    image_thumbnail,
    pdf_thumbnail,
    upload,
    video_metadata,
    video_sprite,
    video_thumbnail,
    video_transcode,
]


async def main():
    # With asyncio debug mode, warn if a coroutine takes more than 300ms to yield.
    asyncio.get_running_loop().slow_callback_duration = 300

    client = await connect()
    worker = Worker(
        client,
        task_queue="media",
        workflows=workflows,
        activities=activities,
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    print("starting worker on task_queue media")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
