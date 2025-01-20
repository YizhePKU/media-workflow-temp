import os
from pathlib import Path
from tempfile import mkdtemp


def tempdir() -> Path:
    return Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"]))
