import functools
from datetime import timedelta
from json import dumps as json_dumps

from temporalio import workflow

start = functools.partial(
    workflow.start_activity, start_to_close_timeout=timedelta(seconds=60)
)


@workflow.defn(name="image-thumbnail")
class ImageThumbnail:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "file": await start("image_thumbnail", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="pdf-thumbnail")
class PdfThumbnail:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "files": await start("pdf_thumbnail", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="font-thumbnail")
class FontThumbnail:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "file": await start("font_thumbnail", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="font-metadata")
class FontMetadata:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            **await start("font_metadata", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="document-thumbnail")
class DocumentThumbnail:
    @workflow.run
    async def run(self, params):
        pdf = await start("convert_to_pdf", params)
        result = {
            "id": workflow.info().workflow_id,
            "files": await start("pdf_thumbnail", {**params, "file": pdf}),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="image-detail")
class ImageDetail:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            **await start("image_detail", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


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


@workflow.defn(name="video-sprite")
class VideoSprite:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "files": await start("video_sprite", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="video-transcode")
class VideoTranscode:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "file": await start("video_transcode", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="audio-waveform")
class AudioWaveform:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "waveform": await start("audio_waveform", params),
        }
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


@workflow.defn(name="image-color-palette")
class ImageColorPalette:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "colors": await start("image_color_palette", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result


@workflow.defn(name="color-fixed-palette")
class ColorFixedPalette:
    @workflow.run
    async def run(self, params):
        result = {
            "id": workflow.info().workflow_id,
            "colors": await start("color_fixed_palette", params),
        }
        if callback_url := params.get("callback_url"):
            await start("callback", args=[callback_url, result])
        return result
