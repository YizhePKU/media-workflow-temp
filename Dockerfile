FROM python:3.13.1-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root
ENV PATH="$PATH:$HOME/.local/bin"
WORKDIR /app

RUN apt-get update
RUN apt-get install -y curl ffmpeg libreoffice fonts-recommended fonts-noto-cjk ghostscript libvips-dev

# adjust memory limit on ImageMagick to handle large PSD files (up to 1GiB)
RUN sed -i 's/<policy domain="resource" name="memory" value="[^"]*"/<policy domain="resource" name="memory" value="1GiB"/' /etc/ImageMagick-6/policy.xml

RUN curl -LsSf https://astral.sh/uv/0.5.11/install.sh | sh

COPY pyproject.toml uv.lock .python-version  .
RUN uv sync

COPY . .

CMD uv run python worker.py
