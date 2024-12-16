FROM debian:bookworm-20241202

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update
RUN apt-get install -y python3-poetry libcairo2-dev ffmpeg libreoffice fonts-recommended fonts-noto-cjk ghostscript libfreeimage3

# Github Actions forces $HOME to be /github/home, breaking poetry's virtualenv
RUN poetry config virtualenvs.in-project true

COPY poetry.lock pyproject.toml .
RUN poetry install --no-interaction --no-root

COPY . .
RUN poetry install --no-interaction

CMD poetry run python media_workflow/worker.py
