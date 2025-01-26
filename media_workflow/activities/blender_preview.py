import asyncio
from pathlib import Path
from sys import platform
from typing import TypedDict

from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class BlenderPreviewParams(BaseModel):
    file: Path


PreviewResult = TypedDict("PreviewResult", {"preview": Path, "glb": Path})


@instrument
@activity.defn
async def blender_preview(params: BlenderPreviewParams) -> PreviewResult:
    assert params.file.exists()
    assert params.file.suffix in [".zip", ".obj", ".stl", ".fbx", ".gltf", ".glb"]
    blender = "/Applications/Blender.app/Contents/MacOS/Blender" if platform == "darwin" else "blender"
    process = await asyncio.subprocess.create_subprocess_exec(
        blender,
        "--background",
        "--python-exit-code",
        "1",
        "--python",
        "scripts/blend.py",
        "--",
        params.file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    (_, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"blender failed: {stderr.decode()}")
    preview = params.file.with_suffix(".jpeg")
    glb = params.file.with_suffix(".glb")
    assert preview.exists()
    assert glb.exists()
    return {
        "preview": preview,
        "glb": glb,
    }
