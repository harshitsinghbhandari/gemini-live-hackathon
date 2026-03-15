import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to sys.path so we can import cmd.backend
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

# Mock out dependencies to avoid needing network or credentials in test
sys.modules['firebase_admin'] = unittest.mock.MagicMock()
sys.modules['firebase_admin.messaging'] = unittest.mock.MagicMock()
sys.modules['google.cloud.firestore'] = unittest.mock.MagicMock()

from cmd.backend.run_backend import app

class TestBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("timestamp", data)

if __name__ == "__main__":
    unittest.main()
