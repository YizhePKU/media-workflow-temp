from pathlib import Path

from media_workflow.image_loader import load_image


def test_load_images():
    for path in Path("tests/images").iterdir():
        with open(path, "rb") as file:
            _image = load_image(file)
