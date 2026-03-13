import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import datetime
import sys
import os

# Add backend to path so we can import modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Mock Firestore and FCM before importing app
with patch("google.cloud.firestore.AsyncClient"), \
     patch("google.cloud.firestore.Client"), \
     patch("firebase_admin.initialize_app"), \
     patch("firebase_admin.messaging.send"):
    from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch("main.save_action_log", new_callable=AsyncMock)
def test_post_action(mock_save):
    mock_save.return_value = "doc_id"
    action_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": "test action",
        "tier": "GREEN",
        "tool": "test_tool",
        "arguments": {},
        "auth_used": False,
        "confirmed_verbally": False,
        "blocked": False,
        "success": True,
        "error": None,
        "duration_ms": 100,
        "device": "test-device"
    }
    response = client.post("/action", json=action_log)
    assert response.status_code == 200
    assert response.json() == {"status": "logged"}
    mock_save.assert_called_once()

@patch("main.create_auth_request", new_callable=AsyncMock)
@patch("main.send_auth_push", new_callable=AsyncMock)
def test_post_auth_request(mock_push, mock_create):
    mock_create.return_value = "req_123"
    auth_req = {
        "action": "delete email",
        "tier": "RED",
        "reason": "sensitive",
        "speak": "confirm delete",
        "tool": "gmail.delete",
        "arguments": {"id": "1"},
        "device": "test-mac"
    }
    response = client.post("/auth/request", json=auth_req)
    assert response.status_code == 200
    assert response.json() == {"request_id": "req_123"}
    mock_create.assert_called_once()
    mock_push.assert_called_once()

@patch("main.get_auth_request", new_callable=AsyncMock)
def test_get_auth_status(mock_get):
    mock_get.return_value = {
        "status": "approved",
        "resolved_at": datetime.datetime.now()
    }
    response = client.get("/auth/status/req_123")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

@patch("main.update_auth_status", new_callable=AsyncMock)
def test_post_auth_approve(mock_update):
    response = client.post("/auth/approve/req_123", json={"approved": True})
    assert response.status_code == 200
    assert response.json() == {"status": "updated"}
    mock_update.assert_called_once_with("req_123", True)
