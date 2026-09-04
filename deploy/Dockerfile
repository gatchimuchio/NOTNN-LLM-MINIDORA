FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir -e .
ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "minidora.製品版", "--serve"]
