FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN groupadd --system minidora && useradd --system --gid minidora --home /app minidora

COPY pyproject.toml README.md ./
COPY src ./src
COPY config/minidora.toml.example ./config/minidora.toml
RUN pip install --no-cache-dir . && mkdir -p /app/data && chown -R minidora:minidora /app

USER minidora
EXPOSE 8765
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=3)"
CMD ["minidora", "serve", "--host", "0.0.0.0", "--port", "8765", "--allow-public-without-auth"]
