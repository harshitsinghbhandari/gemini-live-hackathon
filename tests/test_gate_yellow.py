import asyncio
import sys
import os
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Add root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from guardian.context import GuardianContext
from guardian.gate import gate_action

class TestGateYellow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = GuardianContext(user_id="test_user")
        self.context.session = AsyncMock()

    @patch("guardian.gate.classify_action")
    @patch("guardian.gate.request_yellow_confirmation")
    @patch("guardian.gate.search_and_execute")
    async def test_gate_yellow_confirmed(self, mock_execute, mock_yellow, mock_classify):
        mock_classify.return_value = {
            "tier": "YELLOW",
            "reason": "Sending an email",
            "upgraded": False,
            "speak": "Should I send this?",
            "tool": "GMAIL_SEND",
            "arguments": {"to": "test@example.com"}
        }
        mock_yellow.return_value = True
        mock_execute.return_value = {"success": True, "data": "sent"}

        result = await gate_action("send email", self.context)

        self.assertEqual(result["tier"], "YELLOW")
        self.assertTrue(result["confirmed_verbally"])
        self.assertTrue(result["success"])
        mock_execute.assert_called_once()

    @patch("guardian.gate.classify_action")
    @patch("guardian.gate.request_yellow_confirmation")
    @patch("guardian.gate.search_and_execute")
    async def test_gate_yellow_declined(self, mock_execute, mock_yellow, mock_classify):
        mock_classify.return_value = {
            "tier": "YELLOW",
            "reason": "Sending an email",
            "upgraded": False,
            "speak": "Should I send this?",
            "tool": "GMAIL_SEND",
            "arguments": {"to": "test@example.com"}
        }
        mock_yellow.return_value = False

        result = await gate_action("send email", self.context)

        self.assertEqual(result["tier"], "YELLOW")
        self.assertFalse(result["confirmed_verbally"])
        self.assertTrue(result["blocked"])
        mock_execute.assert_not_called()

if __name__ == "__main__":
    unittest.main()
