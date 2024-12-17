FROM debian:bookworm-20241202

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update
RUN apt-get install -y python3-poetry libcairo2-dev ffmpeg libreoffice fonts-recommended fonts-noto-cjk ghostscript libfreeimage3 wget

ARG TARGETARCH
RUN wget -O temporal.tar.gz "https://temporal.download/cli/archive/latest?platform=linux&arch=$TARGETARCH"
RUN tar xf temporal.tar.gz

COPY poetry.lock pyproject.toml .
RUN poetry install --no-interaction --no-root

COPY . .
RUN poetry install --no-interaction

CMD poetry run python media_workflow/worker.py
