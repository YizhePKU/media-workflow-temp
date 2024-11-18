import os
from uuid import uuid4

import boto3


def upload(key: str, data: bytes):
    """Upload data to S3-compatible storage. Return a presigned URL that downloads the file."""
    s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT_URL"])
    s3.put_object(Bucket=os.environ["S3_BUCKET"], Key=key, Body=data)
    return s3.generate_presigned_url(
        "get_object", Params=dict(Bucket=os.environ["S3_BUCKET"], Key=key)
    )
