import os
from dotenv import load_dotenv

load_dotenv()

def get_secret(secret_id, project_id):
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        # Fallback for local development if GCP not fully setup or missing perm
        return os.environ.get(secret_id)

PROJECT_ID = os.environ.get("PROJECT_ID")
FCM_KEY = get_secret("FCM_KEY", PROJECT_ID)
