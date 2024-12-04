from io import BytesIO

import imageio.v3 as iio
from cairosvg import svg2png
from PIL import Image
from psd_tools import PSDImage

from media_workflow.trace import tracer
from media_workflow.utils import fetch

# remove image size limit
Image.MAX_IMAGE_PIXELS = None


@tracer.start_as_current_span("imread")
async def imread(uri: str, **kwargs) -> Image:
    """Read an image from a URI or a local path."""
    bytes = await fetch(uri)

    # open the image with imageio
    try:
        return Image.fromarray(iio.imread(bytes, **kwargs))
    except:
        pass

    # open the image with psd-tools
    try:
        return PSDImage.open(BytesIO(bytes)).composite()
    except:
        pass

    # open the image with cairosvg
    try:
        return Image.open(BytesIO(svg2png(file_obj=BytesIO(bytes))))
    except:
        pass

    # give up
    raise ValueError(f"Failed to open image {uri}")
