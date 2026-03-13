#!/bin/bash
# Builds and deploys dashboard to Cloud Run
# Returns the Cloud Run URL when done

PROJECT_ID=guardian-agent-160706
REGION=us-central1
SERVICE_NAME=guardian-dashboard
# The backend URL the dashboard needs
BACKEND_URL="https://guardian-backend-1090554066699.us-central1.run.app"

cd "$(dirname "$0")"

# We must build the Next/Vite app with the BACKEND_URL injected.
# Wait, this is Vite. Vite requires env vars at BUILD time, not run time, for static assets.
# But inside Dockerfile, the build happens there. So we need to pass build arg.
echo "VITE_BACKEND_URL=$BACKEND_URL" > .env.production

gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/guardian/$SERVICE_NAME .
gcloud run deploy $SERVICE_NAME \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/guardian/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated
