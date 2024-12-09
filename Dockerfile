FROM python:3.12.7-bookworm

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update
RUN apt-get install -y libcairo2-dev ffmpeg libreoffice fonts-recommended fonts-noto-cjk ghostscript libfreeimage3

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY poetry.lock pyproject.toml .
RUN /root/.local/bin/poetry install --no-interaction --no-root

COPY . .
RUN /root/.local/bin/poetry install --no-interaction

CMD /root/.local/bin/poetry run python media_workflow/worker.py
