from pathlib import Path

from media_workflow.image_loader import image_open


def test_load_images():
    for path in Path("tests/images").iterdir():
        with open(path, "rb") as file:
            _image = image_open(file)
