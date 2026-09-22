---
phase: 7
slug: security-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-22
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` (Python 3.14.3) — deliberately no new dependency |
| **Config file** | none — no `pytest.ini`, no `conftest.py`; plain `tests/test_<subject>.py` modules |
| **Quick run command** | `py -3 -m unittest discover -s tests -p "test_<subject>.py" -v` |
| **Full suite command** | `py -3 -m unittest discover -s tests -v` |
| **Estimated runtime** | quick ~2 s per module · full ~10 s (the `echo.ui.app` test imports `whisper`) |

**Why a durable `tests/` package (this reverses the Phase 6 D-05 transient-harness decision):**
Phase 6 verified a *behaviour-preserving* refactor, where an inline smoke harness was sufficient and
a `tests/` package was explicitly out of scope. Phase 7 introduces *security invariants* — atomic
writes, `0600`, cross-origin header stripping, secret redaction — that are pure functions with crisp
I/O, cannot be eyeballed, and regress silently. They need durable assertions. `unittest` (not
`pytest`) is chosen so that a phase whose final requirement is "pin every dependency" does not
itself add an unpinned one. `pytest` is not installed on this machine (verified).

**Why no `tests/__init__.py`:** `py -3 -m unittest discover -s tests` puts the repository root on
`sys.path` (so `import echo.config` resolves) and treats `tests/` as the top-level start directory.
Omitting the package marker keeps `tests/` free of a shared file that parallel same-wave plans would
otherwise both have to create.

**Cyrillic safety rule:** every assertion containing Russian user-facing text lives **inside** the
UTF-8 test modules. `<automated>` command lines are kept pure ASCII, because PowerShell mangles
non-ASCII literals on the command line (observed in this workspace).

**Live-config safety rule:** `app_config.json` holds the operator's real API key and is gitignored.
Every test that touches config must monkeypatch `echo.config.CONFIG_PATH` to a
`tempfile.TemporaryDirectory()`. No test may write through the real `CONFIG_PATH`.

---

## Sampling Rate

- **After every task commit:** Run that task's `<automated>` command (quick tier)
- **After every plan wave:** Run the full suite command plus the static invariant audit
  (`import re` absent from `echo/llm_client.py`; no `Authorization` literal outside `echo/llm_client.py`)
- **Before `/gsd-verify-work`:** Full suite must be green and `07-04` Task 1 must have passed
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | SEC-05 | T-07-01-03, T-07-01-05 | Error text is redacted (`[REDACTED]` for the configured key, `Bearer …`, `sk-…`, URL userinfo), control chars flattened, bounded to `limit`, and a 100 k-char body cannot stall it | unit | `py -3 -m unittest discover -s tests -p "test_sanitize.py" -v` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | SEC-02 | T-07-01-01 | `base_url` is https-only; `http`/`ftp`/`file`/empty/blank-host/userinfo are rejected with a clear message; the operator's live `https://api.dslab.tech/v1` is accepted; `post_chat` revalidates before sending | unit + integration (mocked opener) | `py -3 -m unittest discover -s tests -p "test_llm_client.py" -v` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | SEC-03 | T-07-01-02 | `Authorization` is dropped when the redirect target netloc (host+port) or scheme changes, and preserved on a same-origin redirect; the process-global opener is not mutated | unit | `py -3 -m unittest discover -s tests -p "test_llm_client.py" -v` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | SEC-01 | T-07-02-01, T-07-02-02 | `save_config` writes a temp file in the config directory, `fsync`s, applies `0600`, then `os.replace`s; a failure before the rename leaves the previous file intact and no `.tmp` residue; two saves leave exactly one file | unit | `py -3 -m unittest discover -s tests -p "test_config_write.py" -v` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | SEC-04 | T-07-02-03 | A corrupt/unreadable/ill-shaped config raises `ConfigCorruptError` (never a silent default, never a bare `AttributeError`); a missing file still yields defaults | unit | `py -3 -m unittest discover -s tests -p "test_config_read.py" -v` | ❌ W0 | ⬜ pending |
| 07-02-03 | 02 | 1 | SEC-06 | T-07-02-04 | `requirements.txt` pins exactly the four verified-working versions and no longer declares `srt`; README/SETUP_GUIDE no longer describe `srt` as declared | static + metadata | `py -3 -m unittest discover -s tests -p "test_requirements_pinning.py" -v` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | SEC-04, SEC-05 | T-07-03-01, T-07-03-02 | `SummarizationEngine.__init__` captures `ConfigCorruptError` into `self.config_error` instead of raising; `is_configured()` is `False`; the queued `summary_error` payload is already sanitized | unit | `py -3 -m unittest discover -s tests -p "test_engine_config_error.py" -v` | ❌ W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | SEC-02 | T-07-03-03 | The settings dialog refuses to persist a non-https `base_url`, shows a messagebox, keeps the dialog open, and never calls `update_config` | unit (GUI seam, messagebox mocked) | `py -3 -m unittest discover -s tests -p "test_settings_validation.py" -v` | ❌ W0 | ⬜ pending |
| 07-03-03 | 03 | 2 | SEC-04, SEC-05 | T-07-03-01, T-07-03-04 | A corrupt config produces a visible startup `messagebox.showerror`; the displayed summary error text is sanitized with the configured key as a secret | integration (headless Tk, messagebox mocked) | `py -3 -m unittest discover -s tests -p "test_app_error_display.py" -v` | ❌ W0 | ⬜ pending |
| 07-04-01 | 04 | 3 | SEC-01…SEC-06 | all T-07-* | Full suite green on the finished tree; static invariants hold (`import re` absent from `llm_client.py`, `os.replace` present in `config.py`, no plain `open(CONFIG_PATH, "w")`); no pre-existing feature regressed | integration + static | `py -3 -m unittest discover -s tests -v` + the static audit in the task | ❌ W0 | ⬜ pending |
| 07-04-02 | 04 | 3 | SEC-01, SEC-02, SEC-04, SEC-05 | — | Human confirms: corrupt config → explicit dialog; `http://` refused in the dialog with the file unchanged; owner-only permissions on the real filesystem; live error text free of credentials | manual | `checkpoint:human-verify` (blocking) — see the task's numbered steps | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

`tests/` does not exist in this repository (verified). Wave 0 work is genuinely required and is
carried **inline** by the first TDD task of each implementation plan — no separate Wave 0 plan.

- [ ] `tests/test_sanitize.py` — SEC-05 redaction + bounding (created by 07-01 Task 1)
- [ ] `tests/test_llm_client.py` — SEC-02 validation + SEC-03 redirect (created by 07-01 Task 2)
- [ ] `tests/test_config_write.py` — SEC-01 atomicity + permissions (created by 07-02 Task 1)
- [ ] `tests/test_config_read.py` — SEC-04 corruption reporting (created by 07-02 Task 2)
- [ ] `tests/test_requirements_pinning.py` — SEC-06 pins (created by 07-02 Task 3)
- [ ] `tests/test_engine_config_error.py` — SEC-04/SEC-05 engine state (created by 07-03 Task 1)
- [ ] `tests/test_settings_validation.py` — SEC-02 dialog guard (created by 07-03 Task 2)
- [ ] `tests/test_app_error_display.py` — SEC-04/SEC-05 UI surfacing (created by 07-03 Task 3)
- [ ] framework install — **not required**: stdlib `unittest`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Corrupt `app_config.json` produces an explicit startup dialog and the app still transcribes | SEC-04 | Needs the real Tk window and a real `messagebox` | 07-04 Task 2, steps 2-4 (backup first, restore after) |
| The settings dialog visibly refuses `http://` and the stored config is unchanged | SEC-02 | Needs the real dialog widget and a real click | 07-04 Task 2, steps 5-7 (compare a hash of `app_config.json` before/after) |
| Owner-only permissions on the operator's real filesystem | SEC-01 | ACL semantics are platform-dependent and not portably assertable | 07-04 Task 2, step 8 (`icacls app_config.json` on Windows, `ls -l` on POSIX) |
| A live API error message contains no credential | SEC-05 | Only meaningful against a real provider round-trip | 07-04 Task 2, steps 9-11 |

*All other phase behaviours have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
