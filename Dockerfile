FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update
RUN apt-get install -y pkg-config python3-dev python3-poetry libcairo2-dev ffmpeg libreoffice

COPY . .

RUN poetry install

CMD poetry run python media_workflow/worker.py
