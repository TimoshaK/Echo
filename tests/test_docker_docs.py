"""Durable documentation invariants for the containerized GUI delivery (CNTR-04).

Plan 09-01 owns ``tests/test_docker_delivery.py`` (Dockerfile + entrypoint). This
module owns the *documentation* contract introduced by Plan 09-03: BUILD.md,
README.md and SETUP_GUIDE.txt must keep telling an operator how to build, run,
configure and redeploy the image.
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "BUILD.md"
README = ROOT / "README.md"
GUIDE = ROOT / "SETUP_GUIDE.txt"


class BuildDocTests(unittest.TestCase):
    """BUILD.md is the build/run/deploy guide."""

    def setUp(self):
        self.build = BUILD.read_text(encoding="utf-8")

    def test_documents_the_browser_gui_url_and_port(self):
        self.assertIn("vnc.html", self.build)
        self.assertIn("6080", self.build)

    def test_binds_the_port_to_loopback_by_default(self):
        self.assertIn("127.0.0.1:6080:6080", self.build)

    def test_documents_save_and_load_deployment(self):
        self.assertIn("docker save", self.build)
        self.assertIn("docker load", self.build)

    def test_documents_the_echo_config_path_override(self):
        self.assertIn("ECHO_CONFIG_PATH=/config/app_config.json", self.build)

    def test_mounts_the_config_directory_and_the_whisper_cache(self):
        self.assertIn("/config", self.build)
        self.assertIn("/root/.cache/whisper", self.build)

    def test_documents_the_vnc_password_for_lan_exposure(self):
        self.assertIn("VNC_PASSWORD", self.build)

    def test_preserves_the_lock_regeneration_section(self):
        self.assertIn("pip-compile", self.build)

    def test_documents_the_https_endpoint(self):
        self.assertIn("https", self.build)

    def test_warns_against_the_single_file_config_mount(self):
        # The key pitfall: a single-file bind mount makes os.replace fail with
        # EBUSY, so the docs must steer operators to a directory mount.
        self.assertIn("EBUSY", self.build)
        self.assertIn("directory", self.build.lower())


class ReadmeDocTests(unittest.TestCase):
    """The user-facing docs point at the container workflow."""

    def setUp(self):
        self.readme = README.read_text(encoding="utf-8")
        self.guide = GUIDE.read_text(encoding="utf-8")

    def test_readme_mentions_docker_and_the_port(self):
        self.assertIn("Docker", self.readme)
        self.assertIn("6080", self.readme)

    def test_readme_links_to_the_build_doc(self):
        self.assertIn("BUILD.md", self.readme)

    def test_setup_guide_mentions_docker(self):
        self.assertIn("Docker", self.guide)
        self.assertIn("6080", self.guide)


class EncodingTests(unittest.TestCase):
    """Phase 8 convention: user-facing docs are UTF-8 with CRLF only."""

    def test_user_docs_decode_as_utf8(self):
        for path in (README, GUIDE):
            with self.subTest(path=path.name):
                path.read_bytes().decode("utf-8")

    def test_readme_has_no_bare_lf(self):
        raw = README.read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), "README.md has a bare LF")

    def test_setup_guide_has_no_bare_lf(self):
        raw = GUIDE.read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), "SETUP_GUIDE.txt has a bare LF")


if __name__ == "__main__":
    unittest.main()
