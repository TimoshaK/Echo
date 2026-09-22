"""Tests for SummarizationEngine handling of a corrupt config (SEC-04, SEC-05)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from echo import config
from echo.summarization_engine import SummarizationEngine


class EngineConfigErrorTests(unittest.TestCase):
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

    def test_corrupt_config_is_captured_not_raised(self):
        self._write("}{")
        engine = SummarizationEngine()
        self.assertIsNotNone(engine.config_error)
        self.assertIn("app_config.json", engine.config_error)

    def test_corrupt_config_falls_back_to_defaults(self):
        self._write('["not", "an", "object"]')
        engine = SummarizationEngine()
        self.assertEqual(engine.config["llm"]["api_key"], "")
        self.assertFalse(engine.config["llm"]["enabled"])

    def test_corrupt_config_reports_not_configured(self):
        self._write("}{")
        engine = SummarizationEngine()
        self.assertFalse(engine.is_configured())

    def test_corrupt_config_blocks_summarize_with_a_clear_message(self):
        self._write("}{")
        engine = SummarizationEngine()
        with self.assertRaises(RuntimeError) as ctx:
            engine.summarize("какой-то текст")
        self.assertIn("app_config.json", str(ctx.exception))

    def test_missing_config_file_is_not_an_error(self):
        engine = SummarizationEngine()
        self.assertIsNone(engine.config_error)

    def test_valid_config_has_no_config_error(self):
        self._write(
            json.dumps({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        )
        engine = SummarizationEngine()
        self.assertIsNone(engine.config_error)
        self.assertTrue(engine.is_configured())

    def test_invalid_utf8_config_is_captured(self):
        self._write(b"\xff\xfe\x00\x01\x02")
        engine = SummarizationEngine()
        self.assertIsNotNone(engine.config_error)
        self.assertFalse(engine.is_configured())

    def test_queued_error_payload_is_sanitized(self):
        self._write(
            json.dumps({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        )
        engine = SummarizationEngine()
        boom = RuntimeError("upstream says sk-test-1234567890 is invalid")
        with mock.patch.object(engine, "summarize", side_effect=boom):
            engine._run_summary("какой-то текст")

        first = engine.progress_queue.get_nowait()
        self.assertEqual(first["type"], "summary_status")

        terminal = engine.progress_queue.get_nowait()
        self.assertEqual(terminal["type"], "summary_error")
        self.assertNotIn("sk-test-1234567890", terminal["error"])
        self.assertIn("[REDACTED]", terminal["error"])

    def test_queued_payload_is_quoted_only_once(self):
        self._write(
            json.dumps({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        )
        engine = SummarizationEngine()
        with mock.patch.object(engine, "summarize", side_effect=RuntimeError("boom")):
            engine._run_summary("текст")
        engine.progress_queue.get_nowait()
        terminal = engine.progress_queue.get_nowait()
        self.assertEqual(terminal["error"], "boom")


if __name__ == "__main__":
    unittest.main()
