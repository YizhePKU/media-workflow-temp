import os
from pathlib import Path

import aioboto3
from botocore.config import Config
from pydantic import BaseModel
from temporalio import activity

from media_workflow.trace import instrument


class UploadParams(BaseModel):
    file: Path
    content_type: str = "binary/octet-stream"


@instrument
@activity.defn
async def upload(params: UploadParams) -> str:
    """Upload file and return a presigned URL that can be used to download it."""
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(region_name=os.environ["S3_REGION"], signature_version="v4"),
    ) as s3:  # type: ignore
        with open(params.file, "rb") as file:
            key = params.file.name
            data = file.read()
            await s3.put_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=key,
                Body=data,
                ContentType=params.content_type,
            )
        presigned_url = await s3.generate_presigned_url(
            "get_object", Params={"Bucket": os.environ["S3_BUCKET"], "Key": key}
        )
        return presigned_url
