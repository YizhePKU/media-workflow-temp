from io import BytesIO
from typing import BinaryIO

from cairosvg import svg2png
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()


def load_image(file: BinaryIO) -> Image:
    """Load an image as an PIL.Image instance.

    In addition to formats natively supported by PIL.Image (see [1] for the full list), this
    function also supports the following formats:

    HEIC: High Efficiency Image File
    SVG: Scalable Vector Graphics

    [1]: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
    """
    try:
        return Image.open(file)
    except UnidentifiedImageError:
        try:
            file.seek(0)
            return Image.open(BytesIO(svg2png(file_obj=file)))
        except:
            pass
        raise
