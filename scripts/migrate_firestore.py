"""
One-time migration script.
Moves all existing flat collection documents to users/testing/ subcollections.
Run once: python scripts/migrate_firestore.py
"""
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize
firebase_admin.initialize_app()
db = firestore.client()

LEGACY_USER_ID = "testing"

COLLECTIONS_TO_MIGRATE = [
    "audit_log",
    "auth_requests",
    "devices",
    "webauthn_credentials",
    "app_state"
]

for collection_name in COLLECTIONS_TO_MIGRATE:
    docs = db.collection(collection_name).stream()
    migrated = 0
    for doc in docs:
        data = doc.to_dict()
        # Write to new location
        db.collection("users").document(LEGACY_USER_ID)\
          .collection(collection_name).document(doc.id).set(data)
        migrated += 1
    print(f"✅ {collection_name}: {migrated} documents migrated to users/{LEGACY_USER_ID}/")

print("\nMigration complete. Old collections left intact — delete manually after verification.")
