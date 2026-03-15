# Aegis GCP Deployment Guide

Aegis relies on Google Cloud Platform (GCP) for its cloud backend. This backend is crucial for enabling out-of-band biometric authentication via WebAuthn and for providing real-time audit logs to the web dashboard.

## 1. Why GCP?

The architecture leverages two specific GCP services:

*   **Cloud Run:** A fully managed compute platform that automatically scales stateless containers. Because Aegis only needs the backend intermittently (when a RED action requires authentication or when a user views the dashboard), Cloud Run's "scale-to-zero" capability ensures minimal cost while maintaining sub-second cold starts when auth requests arrive.
*   **Firestore:** A flexible, scalable NoSQL cloud database. Aegis uses Firestore extensively because of its `on_snapshot` real-time listening capabilities. The local Mac agent can instantly detect when a mobile user has completed a Face ID challenge by listening to changes in a specific Firestore document without needing to repeatedly poll HTTP endpoints.

## 2. Prerequisites for Deployment

Before running the deployment scripts, ensure you have the following:

*   A Google Cloud Project created and configured with billing enabled.
*   The `gcloud` CLI installed and authenticated (`gcloud auth login`).
*   The target project selected (`gcloud config set project [YOUR_PROJECT_ID]`).
*   Docker installed locally (if building images manually, though Cloud Build handles this in the script).

## 3. Environment Variables Configuration

The backend requires several environment variables to function correctly. These are injected during deployment.

*   `FIRESTORE_PROJECT_ID`: The ID of your GCP project where the database lives.
*   `WEBAUTHN_RP_ID`: The Relying Party ID for WebAuthn (e.g., `aegismobile.projectalpha.in`). This must match the domain where the Mobile PWA is hosted.
*   `WEBAUTHN_RP_NAME`: The user-friendly name of the Relying Party (e.g., `Aegis`).
*   `WEBAUTHN_ORIGIN`: The exact origin URL of the Mobile PWA (e.g., `https://aegismobile.projectalpha.in`).
*   `ALLOWED_ORIGINS`: A comma-separated list of CORS origins allowed to access the API (e.g., the Mac PWA, Dashboard, and Mobile PWA domains).

## 4. Deployment Process

Aegis provides deployment scripts to automate the build and release process. The primary script for the backend is `scripts/deploy_backend.sh`.

### The `deploy_backend.sh` Script

This script performs the following actions:

1.  **Builds the Docker Image:** Uses `gcloud builds submit` to build the container image defined in `services/backend/Dockerfile`. The image is pushed to Google Artifact Registry.
2.  **Deploys to Cloud Run:** Uses `gcloud run deploy` to update the service. It configures the container with the specified environment variables, sets the memory/CPU limits, allows unauthenticated access (since the API handles its own user-based auth via X-User-ID headers), and maps the port.

```bash
# Example snippet from deploy_backend.sh (conceptual)
gcloud builds submit --tag gcr.io/[PROJECT_ID]/aegis-backend ./services/backend

gcloud run deploy aegis-backend \
  --image gcr.io/[PROJECT_ID]/aegis-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars=FIRESTORE_PROJECT_ID=[PROJECT_ID],WEBAUTHN_RP_ID=...
```

### The Full `deploy.sh` Script

The repository also includes a comprehensive `scripts/deploy.sh` script. This script orchestrates the deployment of the entire Aegis ecosystem:
1.  **Frontend Apps:** Builds and deploys the Dashboard, Mac App, Mobile App, and Landing Page using Firebase Hosting (or a similar static hosting provider).
2.  **Backend Services:** Triggers the backend deployment to Cloud Run.

### The Dockerfile

The `services/backend/Dockerfile` is standard and optimized for Python FastAPI:
*   Uses a lightweight Python 3.10-slim base image.
*   Installs dependencies from `requirements.txt`.
*   Exposes port 8080 (the default for Cloud Run).
*   Runs `uvicorn run_backend:app --host 0.0.0.0 --port $PORT` to start the server.

## 5. Proof of Deployment

Once deployed successfully, you can verify the service:

1.  Navigate to the Cloud Run console in your GCP dashboard. You should see the `aegis-backend` service running.
2.  Check the URL assigned to the service.
3.  Test a basic endpoint like the health check (if configured) or verify that the frontend apps (which point to this URL via their `.env` files) can successfully reach the API.
4.  Verify Firestore by checking the database console for the `users` collection, which should populate as users register and interact with the PWAs.