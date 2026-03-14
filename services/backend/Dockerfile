FROM python:3.11.9-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11.9-slim-bookworm
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app
USER app
COPY --from=builder /root/.local /home/app/.local
ENV PATH=/home/app/.local/bin:$PATH
# Context is services/backend
COPY --chown=app:app . .
CMD ["uvicorn", "run_backend:app", "--host", "0.0.0.0", "--port", "8080"]
