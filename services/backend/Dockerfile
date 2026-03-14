FROM python:3.11.9-slim-bookworm

# Create app user
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install as root so uvicorn lands in /usr/local/bin (on PATH)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and drop privileges
COPY --chown=app:app . .
USER app

# Run uvicorn
CMD ["uvicorn", "run_backend:app", "--host", "0.0.0.0", "--port", "8080"]