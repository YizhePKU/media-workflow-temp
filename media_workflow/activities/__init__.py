# ruff: noqa: F403

import inspect
import sys

from media_workflow.activities.calibrate import *
from media_workflow.activities.document import *
from media_workflow.activities.font import *
from media_workflow.activities.image import *
from media_workflow.activities.utils import *
from media_workflow.activities.video import *

activities = []
for _name, fn in inspect.getmembers(sys.modules[__name__]):
    if hasattr(fn, "__temporal_activity_definition"):
        activities.append(fn)
