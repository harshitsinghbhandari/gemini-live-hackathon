#!/bin/bash
set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"guardian-agent-160706"}
REGION="us-central1"
SERVICE_NAME="guardian-backend"
IMAGE_URL="us-central1-docker.pkg.dev/$PROJECT_ID/guardian/$SERVICE_NAME"

echo "🚀 Starting deployment for $SERVICE_NAME..."

# 1. Configure Docker
echo "📦 Configuring Docker for Artifact Registry..."
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

# 2. Build and Push Image (Using Cloud Build to avoid local DNS/Docker issues)
echo "🛠️ Building and Pushing image via Cloud Build..."
gcloud builds submit --tag "$IMAGE_URL" ./services/backend

# 3. Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URL" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID="$PROJECT_ID" \
  --quiet

# 4. Show Result
echo "✅ Deployment complete!"
URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
echo "🌐 Service URL: $URL"
