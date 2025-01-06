"""Utilities for reading and writing images.

The `imageio` library with FreeImage backend supports most image formats we need, even less common
ones such as HDR and EXR, but it's still missing SVG and PSB. The `imread()` function supports
practically every image format under the sun and returns a `PIL.Image`.

The `imwrite()` function does the reverse and writes a `PIL.Image` into a file. This is provided
mostly as a convienience.
"""

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

# Remove the image size limit. This prevents pillow from complaining about extremely large images.
Image.MAX_IMAGE_PIXELS = None


@instrument(return_value=False)
def imread(path: Path) -> Image.Image:
    """Read an image from path, converting it into RGB."""
    # open the image with imageio
    try:
        arr = iio.imread(path)
        # clip HDR images
        if arr.dtype != np.uint8:
            arr = (arr.clip(0, 1) * 255).astype(np.uint8)
        return Image.fromarray(arr).convert("RGB")
    except Exception:
        pass

    # open the image with psd-tools
    try:
        image = PSDImage.open(path).composite()
        assert image is not None
        return image.convert("RGB")
    except Exception:
        pass

    # open the image with cairosvg
    try:
        png = svg2png(url=str(path))
        assert png is not None
        return Image.open(BytesIO(png)).convert("RGB")
    except Exception:
        pass

    # give up
    raise ValueError(f"failed to open image {path}")


@instrument(skip=["image"])
def imwrite(image: Image.Image, _dir: Path) -> Path:
    """Write an image to a temporary file. Return the file path."""
    path = _dir / f"{uuid4()}.png"
    image.save(path)
    return path
