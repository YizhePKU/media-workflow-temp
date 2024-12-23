# Environment Variables

This project reads the following environment variables. If you're using VSCode, you can save the
values in an `.env` file, and the VSCode Python extension will load the values whenever a Python
environment is activated.

```bash
# Data directory shared between workers. If running as a container, this should be a volumn mount.
MEDIA_WORKFLOW_DATADIR=

# 256-bit key for signing webhook requests with HMAC-SHA256.
WEBHOOK_SIGNATURE_KEY=

# Temporal endpoint.
TEMPORAL_SERVER_HOST=
TEMPORAL_NAMESPACE=

# S3 endpoint.
S3_ENDPOINT_URL=
S3_REGION=
S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# LiteLLM endpoint.
LLM_BASE_URL=
LLM_API_KEY=

# Force OpenCV to enable OpenEXR.
# See https://github.com/opencv/opencv/issues/21326
OPENCV_IO_ENABLE_OPENEXR=1

# OpenTelemetry endpoint. Currently only honeycomb is supported.
HONEYCOMB_KEY=
```
