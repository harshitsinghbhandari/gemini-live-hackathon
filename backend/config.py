import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("PROJECT_ID", "guardian-agent-160706")
FCM_KEY = os.environ.get("FCM_KEY")
