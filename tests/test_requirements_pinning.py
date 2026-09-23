"""Tests for dependency pinning, hash-locked installs and doc consistency (SUP-01..SUP-05)."""

import importlib.metadata
import pathlib
import re
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CPU_LOCK = PROJECT_ROOT / "requirements.txt"
CUDA_LOCK = PROJECT_ROOT / "requirements-cuda.txt"
DEV_LOCK = PROJECT_ROOT / "requirements-dev.txt"
CPU_IN = PROJECT_ROOT / "requirements.in"
CUDA_IN = PROJECT_ROOT / "requirements-cuda.in"
DEV_IN = PROJECT_ROOT / "requirements-dev.in"
README = PROJECT_ROOT / "README.md"
GUIDE = PROJECT_ROOT / "SETUP_GUIDE.txt"

CUDA_INDEX = "https://download.pytorch.org/whl/cu130"

# The SEC-06 direct-dependency contract: the four packages Echo actually declares.
DIRECT_PINS = {
    "openai-whisper": "20250625",
    "torch": "2.14.0",
    "numpy": "2.4.4",
    "tqdm": "4.70.0",
}

# pip-compile emits a requirement as `name==version \` followed by one
# `    --hash=sha256:<hex> \` line per acceptable archive. The final hash of a
# block carries no trailing backslash; `# via` and `#` lines are comments.
REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9._-]+)==([^\s\\]+)\s*\\$")
HASH_RE = re.compile(r"^\s+--hash=sha256:([0-9a-f]{64})\s*\\?$")
DECLARED_RE = re.compile(r"^[A-Za-z0-9._-]+==")


def parse_lock(path):
    """Parse a pip-compile lock file into ``{name: (version, {sha256, ...})}``."""
    locks = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT_RE.match(line)
        if match:
            current = match.group(1)
            locks[current] = (match.group(2), set())
            continue
        digest = HASH_RE.match(line)
        if digest and current is not None:
            locks[current][1].add(digest.group(1))
    return locks


class LockFileContractTests(unittest.TestCase):
    def test_all_three_locks_exist(self):
        for path in (CPU_LOCK, CUDA_LOCK, DEV_LOCK):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"{path.name} is missing")

    def test_all_lock_inputs_exist(self):
        for path in (CPU_IN, CUDA_IN, DEV_IN):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"{path.name} is missing")

    def test_every_locked_requirement_is_pinned_and_hashed(self):
        for path in (CPU_LOCK, CUDA_LOCK, DEV_LOCK):
            locks = parse_lock(path)
            with self.subTest(path=path.name):
                self.assertTrue(locks, f"{path.name} declares no requirements")
            for name, (version, hashes) in locks.items():
                with self.subTest(path=path.name, package=name):
                    self.assertTrue(version, f"{name} is not pinned")
                    self.assertTrue(hashes, f"{name} has no sha256 hash")

    def test_no_requirement_line_is_silently_skipped(self):
        for path in (CPU_LOCK, CUDA_LOCK, DEV_LOCK):
            declared = [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if DECLARED_RE.match(line)
            ]
            with self.subTest(path=path.name):
                self.assertEqual(len(declared), len(parse_lock(path)))

    def test_cpu_lock_pins_the_direct_dependencies(self):
        locks = parse_lock(CPU_LOCK)
        for name, version in DIRECT_PINS.items():
            with self.subTest(package=name):
                self.assertIn(name, locks)
                self.assertEqual(locks[name][0], version)

    def test_cuda_lock_swaps_torch_for_the_cu130_build(self):
        cuda = parse_lock(CUDA_LOCK)
        self.assertEqual(cuda["torch"][0], "2.14.0+cu130")
        self.assertTrue(cuda["torch"][1])

    def test_cuda_lock_declares_the_pytorch_index_exactly_once(self):
        text = CUDA_LOCK.read_text(encoding="utf-8")
        self.assertEqual(text.count(f"--extra-index-url {CUDA_INDEX}"), 1)

    def test_cuda_lock_matches_the_cpu_lock_apart_from_torch(self):
        cpu, cuda = parse_lock(CPU_LOCK), parse_lock(CUDA_LOCK)
        self.assertEqual(set(cpu), set(cuda))
        for name in cpu:
            if name == "torch":
                continue
            with self.subTest(package=name):
                self.assertEqual(cpu[name], cuda[name])

    def test_dev_lock_pins_the_dev_tooling(self):
        dev = parse_lock(DEV_LOCK)
        self.assertIn("pip-tools", dev)
        self.assertIn("pip-audit", dev)
        self.assertIn("pyinstaller", dev)
        self.assertEqual(dev["pyinstaller"][0], "6.19.0")

    def test_no_lock_declares_the_srt_package(self):
        for path in (CPU_LOCK, CUDA_LOCK, DEV_LOCK):
            with self.subTest(path=path.name):
                self.assertNotIn("srt", parse_lock(path))

    def test_compile_headers_record_a_reproducible_command(self):
        for path in (CPU_LOCK, CUDA_LOCK, DEV_LOCK):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("pip-compile --generate-hashes", text)
                # pip-tools' auto-generated header always records a bogus
                # --no-index even when it was never passed; CUSTOM_COMPILE_COMMAND
                # replaces it with the real command.
                self.assertNotIn("--no-index", text)

    def test_direct_pins_match_the_installed_versions(self):
        for name, pinned in DIRECT_PINS.items():
            with self.subTest(package=name):
                installed = importlib.metadata.version(name)
                self.assertEqual(installed.split("+")[0], pinned)


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.readme = README.read_text(encoding="utf-8")
        self.guide = GUIDE.read_text(encoding="utf-8")

    def test_readme_documents_the_hash_checked_install(self):
        self.assertIn("--require-hashes", self.readme)

    def test_readme_documents_the_cuda_lock(self):
        self.assertIn("requirements-cuda.txt", self.readme)

    def test_readme_documents_the_dev_lock(self):
        self.assertIn("requirements-dev.txt", self.readme)

    def test_readme_documents_the_local_pip_audit_guide(self):
        self.assertIn("pip-audit", self.readme)

    def test_setup_guide_documents_the_hash_checked_install(self):
        self.assertIn("--require-hashes", self.guide)

    def test_readme_drops_the_stale_srt_claims(self):
        self.assertNotIn("declared, but unused", self.readme)
        self.assertNotIn("| srt ", self.readme)

    def test_setup_guide_drops_the_stale_srt_section(self):
        self.assertNotIn("4.4 srt", self.guide)

    def test_readme_keeps_the_local_srt_module_documented(self):
        self.assertIn("echo/srt.py", self.readme)


if __name__ == "__main__":
    unittest.main()
