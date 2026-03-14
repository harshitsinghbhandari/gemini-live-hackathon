FROM python:3.11.9-slim-bookworm AS builder
COPY services/backend/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11.9-slim-bookworm
RUN addgroup --system app && adduser --system --ingroup app app
USER app
COPY --from=builder /root/.local /home/app/.local
ENV PATH=/home/app/.local/bin:$PATH
COPY --chown=app:app . /app
WORKDIR /app
CMD ["uvicorn", "cmd.backend.run_backend:app", "--host", "0.0.0.0", "--port", "8080"]
