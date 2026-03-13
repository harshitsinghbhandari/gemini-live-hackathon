FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH="/app"
COPY services/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/backend ./services/backend
COPY packages/aegis ./packages/aegis
COPY cmd/backend ./cmd/backend
COPY configs/backend ./configs/backend
CMD ["uvicorn", "cmd.backend.run_backend:app", "--host", "0.0.0.0", "--port", "8080"]
