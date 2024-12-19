import inspect

import media_workflow.activities.calibrate as calibrate
import media_workflow.activities.document as document
import media_workflow.activities.font as font
import media_workflow.activities.image as image
import media_workflow.activities.image_detail as image_detail
import media_workflow.activities.utils as utils
import media_workflow.activities.video as video


activities = []
for module in [
    calibrate,
    document,
    font,
    image,
    utils,
    video,
    image_detail,
    image_detail,
]:
    for _name, fn in inspect.getmembers(module):
        if hasattr(fn, "__temporal_activity_definition"):
            activities.append(fn)
