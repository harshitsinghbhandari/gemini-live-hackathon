import asyncio
import sys
import os
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Add root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from guardian.context import GuardianContext
from guardian.gate import gate_action

class TestGate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = GuardianContext(user_id="test_user")

    @patch("guardian.gate.classify_action")
    @patch("guardian.gate.search_and_execute")
    async def test_gate_green_action(self, mock_execute, mock_classify):
        # Mock GREEN classification
        mock_classify.return_value = {
            "tier": "GREEN",
            "reason": "Read-only calendar access",
            "upgraded": False,
            "speak": "Checking your calendar.",
            "tool": "GOOGLECALENDAR_GET_EVENTS",
            "arguments": {"max_results": 5}
        }
        mock_execute.return_value = {"success": True, "data": "some events"}

        result = await gate_action("what are my events", self.context)

        self.assertEqual(result["tier"], "GREEN")
        self.assertTrue(result["success"])
        self.assertTrue(result["executed"])
        self.assertFalse(result["auth_used"])
        mock_execute.assert_called_once()

    @patch("guardian.gate.classify_action")
    @patch("guardian.gate.request_touch_id")
    @patch("guardian.gate.search_and_execute")
    async def test_gate_red_action_auth_success(self, mock_execute, mock_auth, mock_classify):
        # Mock RED classification
        mock_classify.return_value = {
            "tier": "RED",
            "reason": "Sensitive deletion",
            "upgraded": False,
            "speak": "I need your fingerprint to delete this.",
            "tool": "FILE_DELETE",
            "arguments": {"path": "sensitive.txt"}
        }
        mock_auth.return_value = True
        mock_execute.return_value = {"success": True, "data": "deleted"}

        result = await gate_action("delete sensitive.txt", self.context)

        self.assertEqual(result["tier"], "RED")
        self.assertTrue(result["auth_used"])
        self.assertTrue(result["success"])
        mock_execute.assert_called_once()

    @patch("guardian.gate.classify_action")
    @patch("guardian.gate.request_touch_id")
    @patch("guardian.gate.search_and_execute")
    async def test_gate_red_action_auth_fail(self, mock_execute, mock_auth, mock_classify):
        # Mock RED classification
        mock_classify.return_value = {
            "tier": "RED",
            "reason": "Sensitive deletion",
            "upgraded": False,
            "speak": "I need your fingerprint to delete this.",
            "tool": "FILE_DELETE",
            "arguments": {"path": "sensitive.txt"}
        }
        mock_auth.return_value = False

        result = await gate_action("delete sensitive.txt", self.context)

        self.assertEqual(result["tier"], "RED")
        self.assertFalse(result["auth_used"])
        self.assertTrue(result["blocked"])
        self.assertFalse(result["success"])
        mock_execute.assert_not_called()

if __name__ == "__main__":
    unittest.main()
