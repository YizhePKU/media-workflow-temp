import sys
from pathlib import Path
from tempfile import mkdtemp
from zipfile import ZipFile

import bpy  # type: ignore


def find_model(project: Path) -> Path:
    """Find the first model in a 3D project directory."""
    assert project.is_dir()
    for file in project.rglob("*"):
        if file.suffix in [".obj", ".stl", ".fbx", ".gltf", ".glb"]:
            return file
    raise FileNotFoundError("No model file found in 3D project")


def import_model(model: Path):
    """Import the model into Blender."""
    assert model.is_file()
    if model.suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(model))
    elif model.suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=str(model))
    elif model.suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(model))
    elif model.suffix == ".gltf" or file.suffix == ".glb":
        bpy.ops.import_scene.gltf(filepath=str(model))
    else:
        raise NotImplementedError(f"{model} is not in a recognized 3D model format")


# Usage: blender --background --python-exit-code 1 --python scripts/blend.py -- <file>
file = Path(sys.argv[7])
assert file.exists()

# Delete the default cube.
bpy.ops.object.delete()

# If we received a zip archive, extract all content into a temporary directory and import the first model we found.
if file.suffix == ".zip":
    zipfile = ZipFile(file)
    outdir = Path(mkdtemp())
    zipfile.extractall(outdir)
    model = find_model(outdir)
    import_model(model)
else:
    import_model(file)

# Export to glb.
bpy.ops.export_scene.gltf(filepath=str(file.with_suffix(".glb")))

# Align the active camera to the model.
bpy.ops.view3d.camera_to_view_selected()

# Render a picture.
bpy.context.scene.render.image_settings.file_format = "JPEG"
bpy.ops.render.render(use_viewport=True)
bpy.data.images["Render Result"].save_render(filepath=str(file.with_suffix(".jpeg")))
