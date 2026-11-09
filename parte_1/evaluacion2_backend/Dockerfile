FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --system --uid 10001 mariachi && mkdir /data && chown mariachi /data
COPY common ./common
COPY services ./services
COPY scripts ./scripts
USER mariachi
