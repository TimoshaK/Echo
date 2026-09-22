"""Tests for dependency pinning and doc consistency (SEC-06)."""

import importlib.metadata
import pathlib
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

EXPECTED_PINS = {
    "openai-whisper": "20250625",
    "torch": "2.14.0",
    "numpy": "2.4.4",
    "tqdm": "4.70.0",
}


class RequirementsPinningTests(unittest.TestCase):
    def setUp(self):
        self.text = REQUIREMENTS.read_text(encoding="utf-8")
        self.lines = [
            line.strip()
            for line in self.text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def test_every_entry_is_an_exact_pin(self):
        self.assertTrue(self.lines)
        for line in self.lines:
            with self.subTest(line=line):
                self.assertIn("==", line)
                self.assertNotIn(">=", line)

    def test_pin_set_is_exactly_expected(self):
        parsed = dict(line.split("==") for line in self.lines)
        self.assertEqual(parsed, EXPECTED_PINS)

    def test_srt_is_no_longer_declared(self):
        self.assertNotIn("srt", self.text)

    def test_pins_match_the_installed_versions(self):
        for name, pinned in EXPECTED_PINS.items():
            with self.subTest(package=name):
                installed = importlib.metadata.version(name)
                self.assertEqual(installed.split("+")[0], pinned)

    def test_readme_drops_the_stale_srt_claims(self):
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("declared, but unused", readme)
        self.assertNotIn("| srt ", readme)

    def test_setup_guide_drops_the_stale_srt_section(self):
        guide = (PROJECT_ROOT / "SETUP_GUIDE.txt").read_text(encoding="utf-8")
        self.assertNotIn("4.4 srt", guide)

    def test_readme_keeps_the_local_srt_module_documented(self):
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("echo/srt.py", readme)


if __name__ == "__main__":
    unittest.main()
