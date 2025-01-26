FROM debian:unstable-20250113

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root

# Install system dependencies.
RUN apt-get update
RUN apt-get install -y python3-dev ffmpeg blender libreoffice pandoc texlive-xetex texlive-lang-chinese fonts-recommended fonts-noto-cjk libvips-dev

# Install uv.
RUN curl -LsSf https://astral.sh/uv/0.5.24/install.sh | sh
ENV PATH="$PATH:$HOME/.local/bin"

# Install Python dependencies.
COPY pyproject.toml uv.lock .python-version .
RUN uv sync

COPY . .

CMD uv run python worker.py
