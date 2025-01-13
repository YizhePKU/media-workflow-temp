import os
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument


class DownloadParams(BaseModel):
    url: str


@instrument
@activity.defn
async def download(params: DownloadParams) -> Path:
    """Download a file from a URL. Return the file path.

    The filename is randomly generated, but if the original URL contains a file extension, it will
    be retained.
    """
    # If MEDIA_WORKFLOW_TEST_DATADIR is set, check that directory for filename matches.
    path = Path(urlparse(params.url).path)
    if test_datadir := os.environ.get("MEDIA_WORKFLOW_TEST_DATADIR"):
        file = Path(test_datadir) / path.name
        if file.exists():
            return file

    file = Path(mkdtemp(dir=os.environ["MEDIA_WORKFLOW_DATADIR"])) / f"{uuid4()}{path.suffix}"
    timeout = aiohttp.ClientTimeout(total=1500, sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(params.url) as response:
            response.raise_for_status()
            with open(file, "wb") as fp:
                async for chunk, _ in response.content.iter_chunks():
                    fp.write(chunk)
                    activity.heartbeat()
    return file
