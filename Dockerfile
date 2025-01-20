FROM python:3.13.1-bookworm

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root
ENV PATH="$PATH:$HOME/.local/bin"

# Install system dependencies.
RUN apt-get update
RUN apt-get install -y curl ffmpeg libreoffice texlive fonts-recommended fonts-noto-cjk ghostscript libvips-dev

# Install uv.
RUN curl -LsSf https://astral.sh/uv/0.5.11/install.sh | sh

# Install Python dependencies.
COPY pyproject.toml uv.lock .python-version  .
RUN uv sync

COPY . .

CMD uv run python worker.py
