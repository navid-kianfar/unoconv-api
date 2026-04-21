FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    imagemagick \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    graphicsmagick \
    poppler-utils \
    ghostscript \
    locales \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN localedef -i en_US -f UTF-8 en_US.UTF-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir unoconv

COPY . .

ENV TEMP_DIR=/tmp/thumbnails
RUN mkdir -p $TEMP_DIR

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]