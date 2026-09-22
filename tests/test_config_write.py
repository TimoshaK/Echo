"""Tests for atomic, owner-only config writes (SEC-01)."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from echo import config


class ConfigWriteTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "app_config.json"
        self._original_path = config.CONFIG_PATH
        config.CONFIG_PATH = self.path

    def tearDown(self):
        config.CONFIG_PATH = self._original_path
        self._tmpdir.cleanup()

    def _entries(self):
        return sorted(p.name for p in Path(self._tmpdir.name).iterdir())

    def _tmp_entries(self):
        return [name for name in self._entries() if name.endswith(".tmp")]

    def test_save_config_creates_valid_json(self):
        config.save_config({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["llm"]["api_key"], "sk-test-1234567890")
        self.assertTrue(data["llm"]["enabled"])

    def test_defaults_are_merged_into_a_partial_config(self):
        config.save_config({"llm": {"api_key": "sk-test-1234567890"}})
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["llm"]["base_url"], config.DEFAULT_CONFIG["llm"]["base_url"])
        self.assertEqual(data["llm"]["summary_preset"], "free")

    def test_no_temp_residue_after_save(self):
        config.save_config({"llm": {}})
        self.assertEqual(self._tmp_entries(), [])

    def test_two_saves_leave_exactly_one_file(self):
        config.save_config({"llm": {"api_key": "first-key-value"}})
        config.save_config({"llm": {"api_key": "second-key-value"}})
        self.assertEqual(len(self._entries()), 1)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["llm"]["api_key"], "second-key-value")

    def test_failed_replace_keeps_the_previous_file_intact(self):
        config.save_config({"llm": {"api_key": "first-key-value"}})
        original = self.path.read_text(encoding="utf-8")
        with mock.patch.object(config.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                config.save_config({"llm": {"api_key": "second-key-value"}})
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)
        self.assertEqual(self._tmp_entries(), [])

    def test_failed_replace_does_not_create_the_file(self):
        with mock.patch.object(config.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                config.save_config({"llm": {}})
        self.assertFalse(self.path.exists())
        self.assertEqual(self._tmp_entries(), [])

    def test_owner_only_mode_is_requested(self):
        with mock.patch.object(config.os, "chmod") as chmod:
            config.save_config({"llm": {}})
        chmod.assert_called_once()
        self.assertEqual(chmod.call_args[0][1], 0o600)

    def test_chmod_failure_does_not_lose_the_key(self):
        with mock.patch.object(config.os, "chmod", side_effect=OSError("unsupported")):
            config.save_config({"llm": {"api_key": "keep-me-please"}})
        self.assertIn("keep-me-please", self.path.read_text(encoding="utf-8"))

    def test_acl_helper_tolerates_missing_icacls(self):
        with mock.patch.object(config.shutil, "which", return_value=None):
            config._restrict_windows_acl(self.path)

    def test_acl_helper_never_propagates_subprocess_errors(self):
        with mock.patch.object(
            config.subprocess, "run", side_effect=subprocess.TimeoutExpired("icacls", 10)
        ):
            config._restrict_windows_acl(self.path)

    def test_acl_helper_swallows_arbitrary_errors(self):
        with mock.patch.object(config.subprocess, "run", side_effect=OSError("boom")):
            config._restrict_windows_acl(self.path)

    @unittest.skipUnless(os.name == "nt", "Windows-only ACL assertion")
    def test_windows_acl_has_no_inherited_entries(self):
        config.save_config({"llm": {"api_key": "sk-test-1234567890"}})
        result = subprocess.run(
            ["icacls", str(self.path)], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("(I)", result.stdout)

    def test_file_is_utf8_with_trailing_newline(self):
        config.save_config({"llm": {"model": "тестовая-модель"}})
        raw = self.path.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertIn("тестовая-модель", raw.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
