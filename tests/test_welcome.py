import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Prompt import welcome


class WelcomeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.memory_root = self.repo_root / "Memory"
        self.app_space_dir = self.memory_root / "app_space"
        self.user_specific_dir = self.memory_root / "user_specific"
        self.shared_space_dir = self.memory_root / "shared_space"
        self.welcome_cache_dir = self.user_specific_dir / "welcome_cache"

        self.original_paths = {
            "REPO_ROOT": welcome.REPO_ROOT,
            "_MEMORY_ROOT": welcome._MEMORY_ROOT,
            "_APP_SPACE_DIR": welcome._APP_SPACE_DIR,
            "_USER_SPECIFIC_DIR": welcome._USER_SPECIFIC_DIR,
            "_SHARED_SPACE_DIR": welcome._SHARED_SPACE_DIR,
            "_USER_WELCOME_CACHE_DIR": welcome._USER_WELCOME_CACHE_DIR,
            "_SAYINGS_FILE": welcome._SAYINGS_FILE,
        }

        welcome.REPO_ROOT = self.repo_root
        welcome._MEMORY_ROOT = self.memory_root
        welcome._APP_SPACE_DIR = self.app_space_dir
        welcome._USER_SPECIFIC_DIR = self.user_specific_dir
        welcome._SHARED_SPACE_DIR = self.shared_space_dir
        welcome._USER_WELCOME_CACHE_DIR = self.welcome_cache_dir
        welcome._SAYINGS_FILE = self.app_space_dir / "xiexin_sayings.json"
        welcome._ensure_memory_layout()

    def tearDown(self):
        for name, value in self.original_paths.items():
            setattr(welcome, name, value)
        self.temp_dir.cleanup()

    def _write_sayings(self, sayings):
        welcome._SAYINGS_FILE.write_text(
            json.dumps({"sayings": sayings}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_history(self, session_id, entries):
        target = welcome._USER_WELCOME_CACHE_DIR / f"{session_id}.jsonl"
        payload = [json.dumps({"text": item, "ts": index}, ensure_ascii=False) for index, item in enumerate(entries, start=1)]
        target.write_text("\n".join(payload), encoding="utf-8")

    def test_pick_welcome_text_returns_fixed_default_by_default(self):
        session_id = "fixed-default-session"
        self._write_sayings([
            "清风徐来，水波不兴 🍃",
            "想象力比知识更重要 💡",
        ])

        selected, debug_payload = welcome.pick_welcome_text(session_id=session_id)

        self.assertEqual(selected, "你好~我是广分谢鑫😀")
        self.assertEqual(debug_payload["mode"], "fixed-default")
        self.assertTrue(debug_payload["featureFlagEnabled"])
        self.assertEqual(debug_payload["candidateCount"], 0)

    def test_pick_welcome_text_skips_legacy_history_without_emoji(self):
        session_id = "legacy-session"
        self._write_sayings([
            "清风徐来，水波不兴 🍃",
            "想象力比知识更重要 💡",
        ])
        self._write_history(session_id, ["清风徐来，水波不兴"])

        with patch.dict(os.environ, {"XIEXIN_WELCOME_FIXED_DEFAULT": "0"}, clear=False):
            with patch("Prompt.welcome.random.choice", side_effect=lambda items: items[0]):
                selected, debug_payload = welcome.pick_welcome_text(session_id=session_id)

        self.assertEqual(selected, "想象力比知识更重要 💡")
        self.assertEqual(debug_payload["mode"], "local-sayings-random")
        self.assertFalse(debug_payload["featureFlagEnabled"])
        self.assertEqual(debug_payload["candidateCount"], 1)
        self.assertEqual(debug_payload["recentHistory"], ["清风徐来，水波不兴"])

    def test_record_welcome_word_preserves_recent_sequence(self):
        session_id = "sequence-session"

        welcome.record_welcome_word(session_id, "第一句")
        welcome.record_welcome_word(session_id, "第二句")
        history = welcome.record_welcome_word(session_id, "第一句")

        self.assertEqual(history, ["第一句", "第二句", "第一句"])
        self.assertEqual(
            welcome.get_user_specific_welcome_memory(session_id),
            ["第一句", "第二句", "第一句"],
        )


if __name__ == "__main__":
    unittest.main()