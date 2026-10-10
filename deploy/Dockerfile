FROM python:3.13-slim
WORKDIR /app
COPY deploy/requirements-cloud.txt /app/deploy/requirements-cloud.txt
RUN python -m pip install --no-cache-dir --require-hashes -r deploy/requirements-cloud.txt
COPY pyproject.toml README.md LICENSE-APACHE-2.0 /app/
COPY src /app/src
RUN python -m pip install --no-cache-dir --no-deps --no-build-isolation . \
    && useradd --uid 10001 --create-home minidora
USER 10001
ENV PORT=8080 PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
CMD ["python", "-m", "minidora.製品版", "--HDS", "--ADK", "--CloudRun", "--serve"]
