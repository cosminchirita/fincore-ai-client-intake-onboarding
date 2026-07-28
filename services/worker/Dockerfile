FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .
COPY services/api /app/services/api
COPY services/worker /app/services/worker
ENV PYTHONPATH=/app/services/api
CMD ["python", "/app/services/worker/dispatcher.py"]
