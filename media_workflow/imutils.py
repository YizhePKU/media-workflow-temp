"""Utilities for reading and writing images."""

# ruff: noqa: S110

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import imageio.v3 as iio
import numpy as np
from cairosvg import svg2png
from PIL import Image
from psd_tools import PSDImage

from media_workflow.trace import instrument

# remove image size limit
Image.MAX_IMAGE_PIXELS = None


@instrument(return_value=False)
def imread(path: Path) -> Image.Image:
    """Read an image from a local path."""
    # open the image with imageio
    try:
        arr = iio.imread(path)
        if arr.dtype != np.uint8:
            arr = (arr.clip(0, 1) * 255).astype(np.uint8)
        return Image.fromarray(arr)
    except Exception:
        pass

    # open the image with psd-tools
    try:
        image = PSDImage.open(path).composite()
        assert image is not None
        return image
    except Exception:
        pass

    # open the image with cairosvg
    try:
        png = svg2png(url=str(path))
        assert png is not None
        return Image.open(BytesIO(png))
    except Exception:
        pass

    # give up
    raise ValueError(f"failed to open image {path}")


@instrument(skip=["image"])
def imwrite(image: Image.Image, datadir: Path) -> Path:
    """Write an image to a temporary file in PNG format. Return the file path."""
    # If the image is in floating point mode, scale the value by 255
    # See https://github.com/python-pillow/Pillow/issues/3159
    if image.mode == "F":
        image = Image.fromarray((np.array(image) * 255).astype(np.uint8), mode="L")

    path = datadir / f"{uuid4()}.png"
    image.convert("RGB").save(path)
    return path
