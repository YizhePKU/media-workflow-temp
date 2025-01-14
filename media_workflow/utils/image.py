"""The `imwrite()` function writes a `PIL.Image` into a file. This is provided mostly as a convienience."""

import os
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from PIL import Image

from media_workflow.otel import instrument


@instrument(skip=["image"])
def imwrite(image: Image.Image) -> Path:
    """Write an image to a temporary file. Return the file path."""
    path = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"])) / f"{uuid4()}.jpeg"
    image.save(path)
    return path
