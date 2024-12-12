import inspect

import media_workflow.activities.calibrate as calibrate
import media_workflow.activities.document as document
import media_workflow.activities.font as font
import media_workflow.activities.image as images
import media_workflow.activities.utils as utils
import media_workflow.activities.video as video


activities = []
for module in [calibrate, document, font, images, utils, video]:
    for _name, fn in inspect.getmembers(module):
        if hasattr(fn, "__temporal_activity_definition"):
            activities.append(fn)
