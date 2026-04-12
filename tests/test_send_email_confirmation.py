import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Backend.runtime.contracts import AgentRequest


_pending_module = importlib.import_module("Backend.runtime.skills.skill_send_email.pending_confirmation")
_router_module = importlib.import_module("Backend.runtime.router")
_skill_module = importlib.import_module("Backend.runtime.skills.skill_send_email.skill")
SendEmailSkill = _skill_module.SendEmailSkill


class SendEmailConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_pending_root = _pending_module._PENDING_ROOT
        _pending_module._PENDING_ROOT = Path(self.temp_dir.name) / "pending_email_confirmation"

    def tearDown(self):
        _pending_module._PENDING_ROOT = self.original_pending_root
        self.temp_dir.cleanup()

    def test_initial_request_requires_receiver_confirmation(self):
        skill = SendEmailSkill()
        request = AgentRequest(
            user_input="user: 帮我发邮件",
            session_id="session_confirm_1",
            metadata={
                "email": {
                    "receiver": "xiexin1.gd@ccb.com, longjiang.gd@ccb.com",
                    "subject": "测试主题",
                    "body": "这是可以直接发送的测试正文，请两位查收并按需处理。",
                }
            },
        )

        response = skill.run_once(request)

        self.assertIn("我编好内容了，帮我确认一下收件人，我怕打扰到大家~", response.content)
        self.assertIn("收件人：xiexin1.gd@ccb.com，longjiang.gd@ccb.com", response.content)
        self.assertEqual(response.metrics["send_email"]["reason"], "confirmation_pending")
        self.assertTrue(_pending_module.has_pending_email_confirmation("session_confirm_1"))

    def test_confirmation_yes_sends_email_and_clears_pending_state(self):
        skill = SendEmailSkill()
        _pending_module.save_pending_email_confirmation(
            "session_confirm_2",
            {
                "receivers": ["xiexin1.gd@ccb.com", "longjiang.gd@ccb.com"],
                "subject": "测试主题",
                "body": "这是可以直接发送的测试正文，请两位查收并按需处理。",
                "base_metrics": {"llm_adapter_used": False},
            },
        )

        with patch.object(_skill_module.EmailSender, "send_text", return_value={
            "ok": True,
            "receiver": "xiexin1.gd@ccb.com, longjiang.gd@ccb.com",
            "receivers": ["xiexin1.gd@ccb.com", "longjiang.gd@ccb.com"],
            "subject": "测试主题",
            "transport": "ssl",
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
        }) as mocked_send:
            response = skill.run_once(AgentRequest(user_input="user: 是", session_id="session_confirm_2"))

        mocked_send.assert_called_once_with(
            subject="测试主题",
            body="这是可以直接发送的测试正文，请两位查收并按需处理。",
            receiver=["xiexin1.gd@ccb.com", "longjiang.gd@ccb.com"],
        )
        self.assertIn("邮件已发送。", response.content)
        self.assertFalse(_pending_module.has_pending_email_confirmation("session_confirm_2"))

    def test_confirmation_no_cancels_email_and_clears_pending_state(self):
        skill = SendEmailSkill()
        _pending_module.save_pending_email_confirmation(
            "session_confirm_3",
            {
                "receivers": ["xiexin1.gd@ccb.com"],
                "subject": "测试主题",
                "body": "这是可以直接发送的测试正文，请查收并按需处理。",
                "base_metrics": {"llm_adapter_used": False},
            },
        )

        response = skill.run_once(AgentRequest(user_input="user: 否", session_id="session_confirm_3"))

        self.assertEqual(response.content, "好，这封邮件先不发了，已取消。")
        self.assertEqual(response.metrics["send_email"]["reason"], "user_cancelled")
        self.assertFalse(_pending_module.has_pending_email_confirmation("session_confirm_3"))

    def test_router_treats_pending_confirmation_as_send_email_intent(self):
        _pending_module.save_pending_email_confirmation(
            "session_confirm_4",
            {
                "receivers": ["xiexin1.gd@ccb.com"],
                "subject": "测试主题",
                "body": "这是可以直接发送的测试正文，请查收并按需处理。",
                "base_metrics": {},
            },
        )

        result = _router_module._is_send_email_intent(
            AgentRequest(user_input="user: 是", session_id="session_confirm_4")
        )

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()