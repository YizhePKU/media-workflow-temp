#!/usr/bin/env python3

import sys
from pathlib import Path

import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider

auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())
endpoint = "https://oss-cn-beijing.aliyuncs.com"
region = "cn-beijing"
bucket = oss2.Bucket(auth, endpoint, "tezign-ai-models", region=region)


# Usage: ./upload.py <file>
file = Path(sys.argv[1])
assert file.exists()

result = bucket.put_object_from_file(f"media-workflow/{file.name}", file)
assert result.status == 200
print(f"https://tezign-ai-models.oss-cn-beijing.aliyuncs.com/media-workflow/{file.name}")
