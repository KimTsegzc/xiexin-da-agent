import unittest
from datetime import datetime

from Backend.integrations import llm_provider


class LLMProviderSystemTailTests(unittest.TestCase):
    def test_attach_runtime_system_tail_appends_to_existing_system_message(self):
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"},
        ]

        result = llm_provider._attach_runtime_system_tail(messages, datetime(2026, 4, 12, 9, 30))

        self.assertEqual(
            result[0]["content"],
            "你是一个助手\n\n今天是“2026年04月12日”，现在是“09:30”",
        )
        self.assertEqual(result[1], messages[1])

    def test_attach_runtime_system_tail_inserts_system_message_when_missing(self):
        messages = [{"role": "user", "content": "你好"}]

        result = llm_provider._attach_runtime_system_tail(messages, datetime(2026, 4, 12, 9, 30))

        self.assertEqual(
            result[0],
            {"role": "system", "content": "今天是“2026年04月12日”，现在是“09:30”"},
        )
        self.assertEqual(result[1], messages[0])


if __name__ == "__main__":
    unittest.main()