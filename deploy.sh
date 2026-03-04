#!/bin/bash
# Builds and deploys backend to Cloud Run
# Returns the Cloud Run URL when done

PROJECT_ID=guardian-agent-160706
REGION=us-central1
SERVICE_NAME=guardian-backend

# Read .env file for environment variables if it exists
ENV_VARS="PROJECT_ID=$PROJECT_ID"
if [ -f .env ]; then
  # Basic parsing of .env file
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ ! $line =~ ^# ]] && [[ $line == *=* ]]; then
      ENV_VARS="$ENV_VARS,$line"
    fi
  done < .env
fi

gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/guardian/$SERVICE_NAME ./backend
gcloud run deploy $SERVICE_NAME \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/guardian/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "$ENV_VARS"
