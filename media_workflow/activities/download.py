import os
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel
from temporalio import activity

from media_workflow.otel import instrument
from media_workflow.utils.fs import tempdir


class DownloadParams(BaseModel):
    url: str


@instrument
@activity.defn
async def download(params: DownloadParams) -> Path:
    """Download a file from a URL. Return the file path."""
    # If MEDIA_WORKFLOW_TEST_DATADIR is set, check that directory for filename matches.
    path = Path(urlparse(params.url).path)
    if test_datadir := os.environ.get("MEDIA_WORKFLOW_TEST_DATADIR"):
        file = Path(test_datadir) / path.name
        if file.exists():
            return file

    file = tempdir() / f"{path.name}"
    timeout = aiohttp.ClientTimeout(total=1500, sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(params.url) as response:
            response.raise_for_status()
            with open(file, "wb") as fp:
                async for chunk, _ in response.content.iter_chunks():
                    fp.write(chunk)
                    activity.heartbeat()
    return file
