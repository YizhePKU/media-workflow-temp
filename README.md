# Environment variables

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

# How to run regular workers

Step 1: Install `uv`

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Step 2: Install dependencies

```
uv sync
```

Step 3: Start the worker:

```
uv run python worker.py
```

# How to run C4D workers

C4D workers run on a seperate task queue, `media-c4d`. It communicates with a seperate Python
process, `c4dpy`, which is provided by Cinema 4D. This is a workaround because `c4dpy` doesn't
support some third-party packages, and Temporal unfortunately is one of them.

Step 1: Install C4D 2025. Make sure it's properly licensed.

Step 2: Install dependencies for the worker

```
uv sync --only-group=c4d
```

Step 3: Run the worker

```
uv run python c4d_worker.py
```

Step 4: Install dependencies for `c4dpy` using regular `pip` (NOT `c4dpy`):

```
python3 -m pip install --target /Users/tezign/Library/Preferences/MAXON/python/python311/libs opentelemetry-exporter-otlp-proto-http
cp -r media_workflow /Users/tezign/Library/Preferences/MAXON/python/python311/libs
```

Step 5: Run the server with `c4dpy`. You must specify full path to `c4d_server.py`.

```
/Applications/Maxon\ Cinema\ 4D\ 2025/c4dpy.app/Contents/MacOS/c4dpy /absolute/path/to/c4d_server.py
```

