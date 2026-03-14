#!/bin/bash
# Builds and deploys all Aegis services to Cloud Run
# Returns the Cloud Run URLs when done

set -e # Exit on any error

PROJECT_ID=${PROJECT_ID:-"guardian-agent-160706"}
REGION="us-central1"

# Read .env file for environment variables if it exists (used only for backend)
ENV_VARS="PROJECT_ID=$PROJECT_ID"
if [ -f .env ]; then
  # Basic parsing of .env file
  while IFS= read -r line || [ -n "$line" ]; do
    if [[ ! $line =~ ^# ]] && [[ $line == *=* ]]; then
      ENV_VARS="$ENV_VARS,$line"
    fi
  done < .env
fi

# Define services list (Space separated: SERVICE_NAME:DIR)
SERVICES=(
  "guardian-landing:apps/landing"
  "guardian-backend:services/backend"
  "guardian-dashboard:apps/dashboard"
  "guardian-mac-app:apps/mac-app"
  "guardian-mobile-app:apps/mobile-app"
)

echo "🚀 Starting deployments for project $PROJECT_ID in $REGION..."

# File to store deployed URLs since we can't use associative arrays
rm -f deployed_urls.tmp
touch deployed_urls.tmp

for entry in "${SERVICES[@]}"; do
  # Split entry into SERVICE_NAME and DIR using parameter expansion
  SERVICE_NAME="${entry%%:*}"
  DIR="${entry##*:}"
  
  echo "--------------------------------------------------------"
  echo "📦 Building $SERVICE_NAME from $DIR..."
  echo "--------------------------------------------------------"
  
  IMAGE_TAG="us-central1-docker.pkg.dev/$PROJECT_ID/guardian/$SERVICE_NAME"
  
  # Submit build
  gcloud builds submit --tag "$IMAGE_TAG" "$DIR"
  
  echo "--------------------------------------------------------"
  echo "☁️  Deploying $SERVICE_NAME to Cloud Run..."
  echo "--------------------------------------------------------"
  
  # Deploy to Cloud Run
  if [ "$SERVICE_NAME" == "guardian-backend" ]; then
    # Backend needs environment variables
    DEPLOY_CMD="gcloud run deploy $SERVICE_NAME --image $IMAGE_TAG --platform managed --region $REGION --allow-unauthenticated --set-env-vars $ENV_VARS"
  else
    # Frontend services
    DEPLOY_CMD="gcloud run deploy $SERVICE_NAME --image $IMAGE_TAG --platform managed --region $REGION --allow-unauthenticated"
  fi
  
  # Run deploy and capture output to extract URL
  $DEPLOY_CMD --format="value(status.url)" > url.tmp
  
  SERVICE_URL=$(cat url.tmp)
  echo "$SERVICE_NAME: $SERVICE_URL" >> deployed_urls.tmp
  
  echo "✅ $SERVICE_NAME deployed to $SERVICE_URL"
done

rm -f url.tmp

echo ""
echo "========================================================"
echo "🎉 ALL SERVICES SUCCESSFULLY DEPLOYED"
echo "========================================================"
cat deployed_urls.tmp
echo "========================================================"

rm -f deployed_urls.tmp
