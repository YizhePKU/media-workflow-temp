import sys
from pathlib import Path

import bpy  # type: ignore

# Usage: blender --background --python-exit-code 1 --python scripts/blend.py -- <file>
file = Path(sys.argv[7])
assert file.exists()

# Delete the default cube.
bpy.ops.object.delete()

# Import the model.
if file.suffix == ".fbx":
    bpy.ops.import_scene.fbx(filepath=str(file))
else:
    raise NotImplementedError()

# Export to glb.
bpy.ops.export_scene.gltf(filepath=str(file.with_suffix(".glb")))

# Align the active camera to the model.
bpy.ops.view3d.camera_to_view_selected()

# Render a picture.
bpy.context.scene.render.image_settings.file_format = "JPEG"
bpy.ops.render.render(use_viewport=True)
bpy.data.images["Render Result"].save_render(filepath=str(file.with_suffix(".jpeg")))
