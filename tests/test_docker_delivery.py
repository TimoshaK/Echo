"""Static invariants for the containerized GUI delivery artifacts (CNTR-01, CNTR-02).

These tests read only committed sources (the ``Dockerfile`` and
``docker/entrypoint.sh``) and line-scan them for the required literals. They never
read, write or print ``app_config.json`` (the operator's real, gitignored API key).
"""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"
ENTRYPOINT = ROOT / "docker" / "entrypoint.sh"


class DockerfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCKERFILE.read_text(encoding="utf-8")

    def test_vnc_packages_installed(self):
        for package in ("x11vnc", "novnc", "websockify", "xvfb"):
            with self.subTest(package=package):
                self.assertIn(package, self.text)

    def test_ffmpeg_and_fonts_retained(self):
        self.assertIn("ffmpeg", self.text)
        self.assertIn("fonts-dejavu", self.text)

    def test_port_6080_exposed(self):
        self.assertRegex(self.text, r"(?m)^EXPOSE 6080$")

    def test_entrypoint_installed_and_used(self):
        self.assertIn("docker/entrypoint.sh", self.text)
        self.assertIn("/usr/local/bin/entrypoint.sh", self.text)

    def test_no_config_secret_baked(self):
        self.assertNotIn("COPY app_config.json", self.text)
        self.assertNotIn("COPY . .", self.text)

    def test_cpu_torch_install_preserved(self):
        self.assertIn("download.pytorch.org/whl/cpu", self.text)
        self.assertIn("--require-hashes", self.text)


class EntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = ENTRYPOINT.read_text(encoding="utf-8")
        cls.data = ENTRYPOINT.read_bytes()

    def test_file_exists(self):
        self.assertTrue(ENTRYPOINT.is_file())

    def test_strict_mode(self):
        self.assertIn("set -euo pipefail", self.text)

    def test_starts_full_pipeline(self):
        for literal in ("Xvfb", "python -m echo", "x11vnc", "websockify"):
            with self.subTest(literal=literal):
                self.assertIn(literal, self.text)

    def test_serves_novnc_web_root(self):
        self.assertIn("--web /usr/share/novnc/", self.text)

    def test_vnc_is_loopback_only(self):
        self.assertIn("-localhost", self.text)

    def test_waits_for_x_socket(self):
        self.assertIn("/tmp/.X11-unix/X", self.text)

    def test_signal_trap_and_lifecycle_anchor(self):
        self.assertIn("trap ", self.text)
        self.assertIn('wait "$APP_PID"', self.text)

    def test_optional_password_supported(self):
        self.assertIn("VNC_PASSWORD", self.text)

    def test_no_crlf(self):
        self.assertNotIn(b"\r", self.data, "entrypoint.sh must use LF line endings")


if __name__ == "__main__":
    unittest.main()
