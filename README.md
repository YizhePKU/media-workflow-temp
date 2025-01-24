# Overview

This is the source repository of the Media Processing service for Tezign.
It is implemented as a set of Temporal workflows and activities.
API definitions and more are available [here](https://tezign.feishu.cn/wiki/Q8HVw91AziK8u7k7Fy6c2SPNneR).

# Environment variables

This project reads the following environment variables. If you're using VSCode, you can save the
values in an `.env` file, and the VSCode Python extension will load the values whenever a Python
environment is activated.

```bash
# Directory for temporary files shared between workers. If running as a container, this should be a volumn mount.
MEDIA_WORKFLOW_DATADIR=

# Private key for signing webhook requests.
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

# Force OpenCV to enable OpenEXR. Should always be set to 1.
# See https://github.com/opencv/opencv/issues/21326
OPENCV_IO_ENABLE_OPENEXR=

# (Optional) Honeycomb ingest key.
HONEYCOMB_KEY=

# (Optional) Set this to 1 to only perform 1 test for each file category.
MEDIA_WORKFLOW_TEST_SMALL=
# (Optional) Set this to 1 to perform tests that are very slow.
MEDIA_WORKFLOW_TEST_LARGE=
# (Optional) Set this to 1 to perform tests that requires a C4D worker.
MEDIA_WORKFLOW_TEST_C4D=
# (Optional) Set this to 1 to perform tests that requires a local HTTP server at port 8848.
MEDIA_WORKFLOW_TEST_WEBHOOK=
```

# How to run regular workers

Step 1: Install `uv`.

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Step 2: Install dependencies.

```
uv sync
```

Step 3: Start the worker:

```
python worker.py
```

# How to run C4D workers

C4D workers run on a seperate task queue, `media-c4d`. It communicates with a seperate Python
process, `c4dpy`, which is provided by Cinema 4D. This is a workaround because `c4dpy` doesn't
support some third-party packages, and Temporal unfortunately is one of them.

Step 1: Install C4D 2025. Make sure it's properly licensed.

Step 2: Install dependencies for the worker.

```
uv sync --only-group=c4d
```

Step 3: Run the worker.

```
python c4d_worker.py
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

# How to test locally

1. set `TEMPORAL_SERVER_HOST=localhost:7233` and `TEMPORAL_NAMESPACE=default`
2. start the temporal server: `temporal server start-dev`
3. start a worker: `python worker.py`
4. start pytest (run 8 tests concurrently for faster testing): `pytest -n 8`

Test files are stored in OSS and downloaded by the worker as needed.
You can upload new files by running `scripts/upload.py <file>`.

# How to deploy

This project uses Github Actions for CI/CD. Commits pushed to the main branch are built, tested, and pushed to
production automatically. If the commit message contains `hotfix:`, the commit is deployed directly without testing, but
this is not recommended. Pull requests against the main branch are also built and tested, but not deployed. Both x86_64
and arm64 containers are built.

Environment variables are configured seperately (i.e. they're not pulled from Github Actions variables). Contact @XD if
you need to add or modify an environment variable in production.

# Project structure

This project contains two python packages (`media_workflow/` and `pylette/`) and associated tests, several scripts meant
to be run directly (`worker.py`, `webhook_worker.py`, `c4d_worker.py`, `c4d_server.py`), and benchmarks (`bench/`).

The main entry point of the application is `FileAnalysis.run()` in `media_workflow/workflows.py`. This is where we
accept requests from the users and process them. A workflow can start various activities defined in
`media_workflow/activities`. After an activity is completed, the result is saved in `self.results` for queries and
(optionally) posted to the user via webhook.

It should be noted that the term "activity" is being overloaded in the codebase. Sometimes it doesn't actually refer to
a Temporal Activity, but rather a functionality that users want. This is unfortunate, but I'd rather not change the
interface without a better reason.

The `pylette` package is forked from https://github.com/qTipTip/Pylette. Forking is necessary because `pylette` declares
numpy v1.x as a dependency, which is incompatible with other dependencies of this project (Python dependency management
is an absolute dumpster fire lol).
