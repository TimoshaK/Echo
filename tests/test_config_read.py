"""Tests for explicit corrupt-config reporting (SEC-04)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from echo import config
from echo.config import ConfigCorruptError


class ConfigReadTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "app_config.json"
        self._original_path = config.CONFIG_PATH
        config.CONFIG_PATH = self.path

    def tearDown(self):
        config.CONFIG_PATH = self._original_path
        self._tmpdir.cleanup()

    def _write(self, text):
        if isinstance(text, bytes):
            self.path.write_bytes(text)
        else:
            self.path.write_text(text, encoding="utf-8")

    def test_missing_file_returns_defaults(self):
        cfg = config.load_config()
        self.assertEqual(cfg["llm"]["api_key"], "")
        self.assertEqual(cfg["llm"]["base_url"], config.DEFAULT_CONFIG["llm"]["base_url"])

    def test_defaults_are_not_aliased(self):
        cfg = config.load_config()
        self.assertIsNot(cfg["llm"], config.DEFAULT_CONFIG["llm"])

    def test_truncated_json_raises(self):
        self._write('{"llm": {"api_key": "sk-abc')
        with self.assertRaises(ConfigCorruptError):
            config.load_config()

    def test_json_array_root_raises(self):
        self._write('["not", "an", "object"]')
        with self.assertRaises(ConfigCorruptError):
            config.load_config()

    def test_llm_section_of_wrong_type_raises(self):
        self._write('{"llm": ["not", "an", "object"]}')
        with self.assertRaises(ConfigCorruptError):
            config.load_config()

    def test_invalid_utf8_raises(self):
        self._write(b"\xff\xfe\x00\x01\x02")
        with self.assertRaises(ConfigCorruptError):
            config.load_config()

    def test_unreadable_file_raises(self):
        self._write("{}")
        with mock.patch.object(
            config.Path, "read_text", side_effect=PermissionError("denied")
        ):
            with self.assertRaises(ConfigCorruptError):
                config.load_config()

    def test_error_message_names_the_file(self):
        self._write("}{")
        with self.assertRaises(ConfigCorruptError) as ctx:
            config.load_config()
        self.assertIn("app_config.json", str(ctx.exception))

    def test_corrupt_config_never_returns_defaults(self):
        self._write("}{")
        try:
            cfg = config.load_config()
        except ConfigCorruptError:
            return
        self.fail("load_config returned %r instead of raising" % (cfg,))

    def test_valid_partial_config_is_merged_with_defaults(self):
        self._write(json.dumps({"llm": {"api_key": "sk-live-abcdef123456"}}))
        cfg = config.load_config()
        self.assertEqual(cfg["llm"]["api_key"], "sk-live-abcdef123456")
        self.assertEqual(cfg["llm"]["base_url"], config.DEFAULT_CONFIG["llm"]["base_url"])
        self.assertFalse(cfg["llm"]["enabled"])

    def test_unknown_keys_are_preserved(self):
        self._write(json.dumps({"llm": {"api_key": "sk-test-1234567890", "custom": 1}}))
        self.assertEqual(config.load_config()["llm"]["custom"], 1)

    def test_save_then_load_round_trip(self):
        config.save_config({"llm": {"api_key": "sk-round-trip-key", "enabled": True}})
        cfg = config.load_config()
        self.assertEqual(cfg["llm"]["api_key"], "sk-round-trip-key")
        self.assertTrue(cfg["llm"]["enabled"])


if __name__ == "__main__":
    unittest.main()
