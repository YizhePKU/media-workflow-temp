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
    # Invoke Blender with `scripts/blend.py`.
    blender = "/Applications/Blender.app/Contents/MacOS/Blender" if platform == "darwin" else "blender"
    process = await asyncio.subprocess.create_subprocess_exec(
        blender,
        "--background",  # headless mode, no GUI
        "--python-exit-code",  # make blender crash if the Python script throws an exception
        "1",
        "--python",
        "scripts/blend.py",
        "--",
        params.file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={},  # clear PATH so that blender doesn't use our Python virtual environment
    )
    (stdout, stderr) = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"blender failed: {stdout.decode()} {stderr.decode()}")
    preview = params.file.with_suffix(".jpeg")
    glb = params.file.with_suffix(".glb")
    assert preview.exists()
    assert glb.exists()
    return {
        "preview": preview,
        "glb": glb,
    }
