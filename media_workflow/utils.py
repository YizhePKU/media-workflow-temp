import os
import tempfile
from io import BytesIO
from uuid import uuid4

import imageio.v3 as iio
import numpy as np
from cairosvg import svg2png
from PIL import Image
from psd_tools import PSDImage

from media_workflow.trace import span_attribute, tracer

# remove image size limit
Image.MAX_IMAGE_PIXELS = None


@tracer.start_as_current_span("imread")
def imread(path: str) -> Image:
    """Read an image from a local path."""
    # open the image with imageio
    try:
        arr = iio.imread(path)
        if arr.dtype != np.uint8:
            arr = (arr * 256 / np.max(arr)).astype(np.uint8)
        return Image.fromarray(arr)
    except Exception:
        pass

    # open the image with psd-tools
    try:
        return PSDImage.open(path).composite()
    except Exception:
        pass

    # open the image with cairosvg
    try:
        return Image.open(BytesIO(svg2png(url=path)))
    except Exception:
        pass

    # give up
    raise ValueError(f"failed to open image {path}")


@tracer.start_as_current_span("imwrite")
def imwrite(image: Image) -> str:
    """Write an image to a temporary file in PNG format. Return the file path."""
    # If the image is in floating point mode, scale the value by 255
    # See https://github.com/python-pillow/Pillow/issues/3159
    if image.mode == "F":
        image = Image.fromarray((np.array(image) * 255).astype(np.uint8), mode="L")

    path = os.path.join(tempfile.gettempdir(), f"{uuid4()}.png")
    image.convert("RGB").save(path)
    span_attribute("path", path)
    return path
