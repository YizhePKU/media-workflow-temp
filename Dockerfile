FROM python:3.13.1-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root
ENV PATH="$PATH:$HOME/.local/bin"
WORKDIR /app

RUN apt-get update
RUN apt-get install -y curl libcairo2-dev ffmpeg libreoffice fonts-recommended fonts-noto-cjk ghostscript libfreeimage3

RUN curl -LsSf https://astral.sh/uv/0.5.11/install.sh | sh

COPY pyproject.toml uv.lock .python-version  .
RUN uv sync

COPY . .

CMD uv run python worker.py
