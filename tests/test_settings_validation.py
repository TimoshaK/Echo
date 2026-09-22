"""Tests for the settings-dialog base_url guard (SEC-02)."""

import unittest
from unittest import mock

from echo.ui import settings_dialog


class ValidateSettingsBaseUrlTests(unittest.TestCase):
    def test_live_url_is_accepted(self):
        ok, result = settings_dialog.validate_settings_base_url("https://api.dslab.tech/v1")
        self.assertTrue(ok)
        self.assertEqual(result, "https://api.dslab.tech/v1")

    def test_trailing_slash_is_normalized(self):
        ok, result = settings_dialog.validate_settings_base_url("https://openrouter.ai/api/v1/")
        self.assertTrue(ok)
        self.assertEqual(result, "https://openrouter.ai/api/v1")

    def test_http_is_refused_with_a_message(self):
        ok, message = settings_dialog.validate_settings_base_url("http://example.com/v1")
        self.assertFalse(ok)
        self.assertIn("https://", message)

    def test_empty_is_refused(self):
        ok, message = settings_dialog.validate_settings_base_url("")
        self.assertFalse(ok)
        self.assertTrue(message)

    def test_userinfo_is_refused(self):
        ok, _ = settings_dialog.validate_settings_base_url(
            "https://user:pass@api.example.com/v1"
        )
        self.assertFalse(ok)

    def test_helper_never_raises(self):
        for raw in ("", "   ", "ftp://x", "https://", "not a url at all"):
            with self.subTest(raw=raw):
                ok, message = settings_dialog.validate_settings_base_url(raw)
                self.assertIsInstance(ok, bool)
                self.assertIsInstance(message, str)


class _FakeSummarizer:
    def __init__(self):
        self.config = {
            "llm": {
                "api_key": "sk-test-1234567890",
                "base_url": "https://api.dslab.tech/v1",
                "model": "test-model",
                "enabled": False,
            }
        }
        self.updates = []

    def update_config(self, **kwargs):
        self.updates.append(kwargs)


class _FakeApp:
    def __init__(self, root):
        self.root = root
        self.bg_color = "#252525"
        self.panel_dark = "#1a1a1a"
        self.accent_color = "#F2A900"
        self.accent_dark = "#c98a00"
        self.text_color = "#e0e0e0"
        self.summarizer = _FakeSummarizer()


class SettingsDialogIntegrationTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk

            self.root = tk.Tk()
            self.root.withdraw()
        except Exception as exc:  # no display available
            self.skipTest("no Tk display: %s" % exc)
        import tkinter as tk

        self.tk = tk

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _open_dialog(self):
        self.app = _FakeApp(self.root)
        settings_dialog.open_settings(self.app)
        self.root.update_idletasks()
        toplevels = [
            w for w in self.root.winfo_children() if isinstance(w, self.tk.Toplevel)
        ]
        self.assertEqual(len(toplevels), 1)
        toplevel = toplevels[0]
        entries = [w for w in toplevel.winfo_children() if isinstance(w, self.tk.Entry)]
        buttons = [w for w in toplevel.winfo_children() if isinstance(w, self.tk.Button)]
        self.assertEqual(len(entries), 3)
        self.assertEqual(len(buttons), 1)
        return toplevel, entries, buttons[0]

    def _set_base_url(self, entry, value):
        entry.delete(0, self.tk.END)
        entry.insert(0, value)

    def test_invalid_url_is_refused_and_not_persisted(self):
        _, entries, save_button = self._open_dialog()
        self._set_base_url(entries[1], "http://example.com/v1")
        with mock.patch.object(settings_dialog.messagebox, "showerror") as showerror:
            save_button.invoke()
        showerror.assert_called_once()
        self.assertEqual(self.app.summarizer.updates, [])
        self.assertTrue(self.tk.Toplevel.winfo_exists(entries[1].winfo_toplevel()))

    def test_valid_url_is_persisted_and_normalized(self):
        _, entries, save_button = self._open_dialog()
        self._set_base_url(entries[1], "https://openrouter.ai/api/v1/")
        with mock.patch.object(settings_dialog.messagebox, "showerror") as showerror:
            save_button.invoke()
        showerror.assert_not_called()
        self.assertEqual(len(self.app.summarizer.updates), 1)
        self.assertEqual(
            self.app.summarizer.updates[0]["base_url"], "https://openrouter.ai/api/v1"
        )


if __name__ == "__main__":
    unittest.main()
