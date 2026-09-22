"""Tests for the UI surfacing of config corruption and sanitized API errors (SEC-04, SEC-05)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from echo import config


def _import_app():
    from echo.ui import app as app_module

    return app_module


class AppDisplayTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk

            self.tk = tk
            self.root = tk.Tk()
            self.root.withdraw()
        except Exception as exc:
            self.skipTest("no Tk display: %s" % exc)

        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "app_config.json"
        self._original_path = config.CONFIG_PATH
        config.CONFIG_PATH = self.path

    def _cancel_pending_timers(self):
        """Cancel the startup dialog timer so it cannot fire after teardown.

        A corrupt-config app schedules `root.after(200, self._show_config_error)`.
        unittest never runs a mainloop, but cancelling explicitly keeps a stray
        `update()` from opening a real (unmocked) modal dialog.
        """
        try:
            for timer_id in self.root.tk.call("after", "info"):
                self.root.after_cancel(timer_id)
        except Exception:
            pass

    def tearDown(self):
        self._cancel_pending_timers()
        try:
            config.CONFIG_PATH = self._original_path
        except AttributeError:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        if hasattr(self, "_tmpdir"):
            self._tmpdir.cleanup()

    def _build_app(self, config_text):
        if config_text is not None:
            self.path.write_text(config_text, encoding="utf-8")
        app_module = _import_app()
        return app_module.TranscriberApp(self.root)

    def test_corrupt_config_does_not_break_construction(self):
        app = self._build_app("}{")
        self.assertIsNotNone(app.summarizer.config_error)
        self.assertTrue(hasattr(app, "transcribe_btn"))

    def test_corrupt_config_is_surfaced_with_a_named_file(self):
        app = self._build_app("}{")
        with mock.patch.object(_import_app().messagebox, "showerror") as showerror:
            app._show_config_error()
        showerror.assert_called_once()
        shown = showerror.call_args[0][1]
        self.assertIn("app_config.json", shown)

    def test_healthy_config_schedules_no_corruption_dialog(self):
        app = self._build_app(
            json.dumps({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        )
        self.assertIsNone(app.summarizer.config_error)

    def test_summary_error_display_is_sanitized(self):
        app = self._build_app(
            json.dumps({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        )
        with mock.patch.object(_import_app().messagebox, "showerror") as showerror:
            app._handle_summary_error("upstream says sk-test-1234567890 is bad")
        showerror.assert_called_once()
        shown = showerror.call_args[0][1]
        self.assertNotIn("sk-test-1234567890", shown)
        self.assertIn("[REDACTED]", shown)
        self.assertEqual(str(app.summary_btn["state"]), "normal")

    def test_empty_summary_error_still_shows_text(self):
        app = self._build_app(
            json.dumps({"llm": {"api_key": "sk-test-1234567890", "enabled": True}})
        )
        with mock.patch.object(_import_app().messagebox, "showerror") as showerror:
            app._handle_summary_error("")
        showerror.assert_called_once()
        shown = showerror.call_args[0][1].strip()
        self.assertTrue(shown)
        self.assertNotIn("\n\n\n", shown)


if __name__ == "__main__":
    unittest.main()
