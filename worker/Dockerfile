FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/src ./worker/src
ENV PYTHONPATH=/app
CMD ["python", "-m", "worker.src.worker"]
