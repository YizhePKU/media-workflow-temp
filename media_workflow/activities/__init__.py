import inspect

from . import calibrate
from . import document
from . import font
from . import image
from . import utils
from . import video
from . import image_detail


activities = []
for module in [calibrate, document, font, image, utils, video, image_detail]:
    for _name, fn in inspect.getmembers(module):
        if hasattr(fn, "__temporal_activity_definition"):
            activities.append(fn)
