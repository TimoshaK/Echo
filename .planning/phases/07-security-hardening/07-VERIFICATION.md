---
phase: 07-security-hardening
verified: 2026-09-22T21:14:57Z
status: passed
score: 6/6 must-haves verified
re_verification:
  previous_status: none
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 7: Security Hardening Verification Report

**Phase Goal:** Eliminate the security weaknesses found in the audit — plaintext secret exposure, unvalidated base_url/SSRF, redirect credential leak, silent config fallback, unsanitized API error details, and unpinned dependencies
**Verified:** 2026-09-22T21:14:57Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Roadmap success criteria (the contract) plus plan-level truths, all verified against the actual codebase — not the summaries.

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `app_config.json` is written owner-only and atomically (no partial writes) | ✓ VERIFIED | `echo/config.py:110-138` uses `tempfile.mkstemp(dir=parent)` → `flush` + `os.fsync` → `os.chmod(tmp, 0o600)` → `os.replace(tmp, path)`; on any pre-rename failure the temp file is unlinked and the previous file is byte-identical. Independently reproduced: after a forced `os.replace` failure the old content was unchanged and no `.tmp` residue existed; `CONFIG_FILE_MODE = 0o600`. Windows `icacls /inheritance:r /grant:r` fallback is non-fatal. |
| 2 | `base_url` is validated https-only; http/non-standard schemes rejected with a clear message | ✓ VERIFIED | `echo/llm_client.py:24-47` `validate_base_url`; independently confirmed it accepts `https://api.dslab.tech/v1` unchanged and rejects `http://`, `ftp://`, `file://`, `//host`, `""`, `"   "`, `None`, `https://` (no host) and `https://user:pass@…`. The refusal message names the offending scheme and contains `https://`. `post_chat` calls it before building the request (`echo/llm_client.py:98`), and `settings_dialog.save_settings` validates before `update_config` (`echo/ui/settings_dialog.py:116-130`). |
| 3 | HTTP redirects do not forward the `Authorization` header to a different host | ✓ VERIFIED | `SafeRedirectHandler` (`echo/llm_client.py:50-62`) subclasses `HTTPRedirectHandler` and pops `Authorization` when `_is_cross_origin` (scheme or lowercased `netloc`, port included) differs. Independently reproduced the real `redirect_request` flow: cross-host/port/scheme → header absent; same-origin → header kept. Hardening uses a private cached opener (`_http_opener`, `build_opener`); `install_opener` and bare `urllib.request.urlopen(` are absent from the module. |
| 4 | A corrupted config produces an explicit user-visible message instead of a silent default fallback | ✓ VERIFIED | `load_config` (`echo/config.py:44-79`) returns defaults only on `FileNotFoundError`; truncated JSON, array root, non-object `llm`, invalid UTF-8 and `OSError` raise `ConfigCorruptError(path, detail)` naming the file. `SummarizationEngine.__init__` (`echo/summarization_engine.py:25-30`) captures it into `self.config_error`, and `TranscriberApp` schedules `_show_config_error` (`echo/ui/app.py:44-45, 248-260`), which names `app_config.json`. Independently reproduced the typed raise and the missing-file default. |
| 5 | API error details shown in the UI are sanitized | ✓ VERIFIED | `sanitize_error_detail` (`echo/errors.py:67-100`) redacts the configured key, `Bearer …`, `sk-…`, URL userinfo and long opaque tokens, flattens whitespace, bounds to `limit` (input capped at 4000 before any regex). Applied in both `post_chat` error branches (`echo/llm_client.py:115-127`), in the engine queue payload (`echo/summarization_engine.py:157`) and again before the messagebox with `limit=500` (`echo/ui/app.py:276-283`). Independently confirmed each redaction shape. |
| 6 | Dependency versions are pinned and the unused `srt` dependency is removed | ✓ VERIFIED | `requirements.txt` is exactly `openai-whisper==20250625`, `torch==2.14.0`, `numpy==2.4.4`, `tqdm==4.70.0` — four `==` pins, no `>=`, no `srt`. `README.md:203` and `SETUP_GUIDE.txt:280-289` no longer claim `srt` is declared while still documenting the project's own `echo/srt.py`. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `echo/errors.py` | `sanitize_error_detail` + `InvalidBaseUrlError` + `REDACTED` + `MAX_SANITIZE_INPUT` | ✓ VERIFIED | All present; `SummaryApiError` and `map_transcription_error` intact. `InvalidBaseUrlError(ValueError)` is deliberately not a `SummaryApiError`. |
| `echo/llm_client.py` | `validate_base_url`, `SafeRedirectHandler`, `_is_cross_origin`, `_http_opener` | ✓ VERIFIED | All present and wired into `post_chat`; module stays free of `import re` (T-260921-04) and of `[:500]`. |
| `echo/config.py` | `CONFIG_FILE_MODE`, `ConfigCorruptError`, `_atomic_write_secure`, `_restrict_windows_acl`, rewritten read/write | ✓ VERIFIED | All present; `CONFIG_PATH`/`DEFAULT_CONFIG` unchanged (REFR-03); no `open(CONFIG_PATH, "w")`. |
| `echo/summarization_engine.py` | `self.config_error`, sanitized queue payload, fail-fast `summarize` | ✓ VERIFIED | `config_error` captured in `__init__`; `is_configured()` short-circuits; `summarize()` fails fast naming `app_config.json`; `_run_summary` sanitizes at source. Ladder (`is_layer_failure`, json_schema→json_object→plain) unchanged. |
| `echo/ui/settings_dialog.py` | `validate_settings_base_url` + guarded `save_settings` | ✓ VERIFIED | Helper returns `(ok, value_or_message)` and never raises; `save_settings` refuses and returns without `destroy()`; old `base_url=url_var.get()` gone. |
| `echo/ui/app.py` | `_show_config_error` + sanitized summary error | ✓ VERIFIED | Deferred startup dialog on `config_error`; `_handle_summary_error` sanitizes with `limit=500` and falls back to `'нет деталей'`; `_handle_transcription_error` deliberately untouched (accepted risk T-07-03-05). |
| `requirements.txt` | Fully pinned runtime set | ✓ VERIFIED | Four exact pins, no `srt`, no `>=`. |
| `README.md`, `SETUP_GUIDE.txt` | Docs made truthful | ✓ VERIFIED | No `declared, but unused`; SETUP_GUIDE §4.4 renamed; `echo/srt.py` still documented. |
| `tests/test_sanitize.py` … `tests/test_app_error_display.py` (8 modules) | Durable regression suite | ✓ VERIFIED | All 8 present and substantive (93 tests total); no skips on this desktop session. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `llm_client.post_chat` | `errors.sanitize_error_detail` | import used in both error branches | ✓ WIRED | `sanitize_error_detail(` appears in the `HTTPError` and `URLError` branches (`llm_client.py:116,125`). |
| `llm_client.post_chat` | `SafeRedirectHandler` | `_http_opener().open(req, timeout=60)` | ✓ WIRED | Private cached opener built with `build_opener(SafeRedirectHandler)`; global opener untouched. |
| `ui.settings_dialog` | `llm_client.validate_base_url` | import used inside `save_settings` | ✓ WIRED | `validate_settings_base_url` calls it; result is what gets persisted. |
| `summarization_engine` | `config.ConfigCorruptError` | caught in `__init__` | ✓ WIRED | `except ConfigCorruptError as e:` sets `config_error`. |
| `ui.app` | `errors.sanitize_error_detail` | before `messagebox.showerror` | ✓ WIRED | `safe_error = sanitize_error_detail(error, secrets=(api_key,), limit=500)`. |
| `ui.app` | `summarization_engine.config_error` | read at startup | ✓ WIRED | `if self.summarizer.config_error: self.root.after(200, self._show_config_error)`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `ui/app._handle_summary_error` | `error` → `safe_error` | `summarizer.progress_queue` (`summary_error["error"]`, already sanitized) | Yes — real exception text from `_run_summary`, not a hardcoded stub | ✓ FLOWING |
| `ui/app.__init__` → `_show_config_error` | `summarizer.config_error` | `load_config` → `ConfigCorruptError.__str__` | Yes — real corruption reason, conditional (only set on failure) | ✓ FLOWING |
| `ui/settings_dialog.save_settings` | `result` (normalized URL) | `validate_base_url(url_var.get())` | Yes — real entry value, not a constant | ✓ FLOWING |
| `llm_client.post_chat` | `api_key` | `config["llm"]["api_key"]` | Yes — operator's live key read at call time; only ever placed in the `Authorization` header and passed as a redaction secret | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite green on the finished tree | `py -3 -m unittest discover -s tests -v` | `Ran 93 tests in 2.097s` → `OK`; no skips | ✓ PASS |
| http/non-https refused, live URL accepted | inline `validate_base_url(...)` probe | live URL returned unchanged; all 8 bad forms raised `InvalidBaseUrlError` | ✓ PASS |
| Cross-origin redirect strips `Authorization` | inline `SafeRedirectHandler.redirect_request` probe | cross-host/port/scheme → absent; same-origin → kept; POST 307 refused by stdlib | ✓ PASS |
| Atomic write + failure isolation + no residue | inline `save_config` probe with forced `os.replace` failure | one file after save; prior content byte-identical after failure; no `.tmp`; `0600` requested | ✓ PASS |
| Corrupt config raises typed error; missing file defaults | inline `load_config` probe | corrupt → `ConfigCorruptError` naming `app_config.json`; missing → defaults; no aliasing | ✓ PASS |
| Redactor neutralizes every secret shape | inline `sanitize_error_detail` probe | `Bearer`, `sk-`, URL userinfo, configured key all redacted; empty/None → `""` | ✓ PASS |
| Static invariant audit (34 checks) | inline pathlib check of the 7 shipped files | 34/34 PASS | ✓ PASS |
| REFR-03: root config still read, healthy | inline `load_config`/app probe | `app_config.json` present, `llm` keys complete, `enabled: True`, https base_url | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SEC-01 | 07-02, 07-04 | `app_config.json` owner-only (0600) and atomic | ✓ SATISFIED | `_atomic_write_secure` + `CONFIG_FILE_MODE` + `_restrict_windows_acl`; tests `test_config_write.py`; real-filesystem `(I)`-free assertion ran (not skipped). |
| SEC-02 | 07-01, 07-03, 07-04 | `base_url` https-only validation | ✓ SATISFIED | `validate_base_url` + dialog guard; `test_llm_client.py`/`test_settings_validation.py`; `post_chat` revalidates before any socket. |
| SEC-03 | 07-01 | Redirects do not forward `Authorization` cross-host | ✓ SATISFIED | `SafeRedirectHandler` + `_is_cross_origin` + private opener; `test_llm_client.py` redirect matrix. |
| SEC-04 | 07-02, 07-03, 07-04 | Corrupt config → explicit user message | ✓ SATISFIED | `ConfigCorruptError` + engine `config_error` + `_show_config_error`; `test_config_read.py`/`test_engine_config_error.py`/`test_app_error_display.py`. |
| SEC-05 | 07-01, 07-03, 07-04 | API error details sanitized before UI | ✓ SATISFIED | Redactor applied at request layer, queue payload and display; `test_sanitize.py`/`test_llm_client.py`/`test_engine_config_error.py`/`test_app_error_display.py`. |
| SEC-06 | 07-02, 07-04 | Versions pinned; unused `srt` removed | ✓ SATISFIED | Four `==` pins, no `srt`; `test_requirements_pinning.py` (incl. installed-version match); docs corrected. |

**Orphaned requirements:** None. `REQUIREMENTS.md` maps SEC-01…SEC-06 to Phase 7, all marked Complete; the union of plan frontmatter (`07-01: SEC-02/03/05`, `07-02: SEC-01/04/06`, `07-03: SEC-02/04/05`, `07-04: SEC-01/02/04/05`) accounts for all six IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TODO`/`FIXME`/placeholder markers, no empty-return stubs, no hardcoded-empty data flowing to UI in `echo/` | ℹ️ Info | None. The `safe_error or 'нет деталей'` fallback is an intentional user-facing placeholder for an already-sanitized-to-empty error, not a stub. |

### Human Verification (Attested — completed in 07-04)

The four behaviours below are inherently non-portable (real dialog rendering, platform ACL semantics, live provider round-trip). They are **not pending**: plan `07-04` Task 2 was a blocking `checkpoint:human-verify` gate and the operator recorded `approved`. They are listed here to distinguish the machine-verified wiring from the human attestation, not as open items.

| # | Attested behaviour | Requirement | Machine-side corroboration | Attestation |
| - | ------------------ | ----------- | -------------------------- | ----------- |
| 1 | Corrupt config shows a `Повреждённый конфиг` dialog naming `app_config.json` while transcription stays usable | SEC-04 | `test_app_error_display.py` drives `_show_config_error` with a mocked `messagebox` (ran, not skipped); code path verified | 07-04 operator `approved` |
| 2 | `http://example.com/v1` refused in the real API SETTINGS dialog, window stays open, file unchanged | SEC-02 | `test_settings_validation.py` drives the real SAVE button on a real Tk dialog (ran, not skipped) | 07-04 operator `approved` |
| 3 | `icacls app_config.json` shows a single owner-only `(F)` entry, no `(I)` inherited, no `Users`/`Everyone` | SEC-01 | `test_config_write.py::test_windows_acl_has_no_inherited_entries` ran against a real temp file on this NTFS volume (not skipped) | 07-04 operator `approved` |
| 4 | A live summary error against a bogus key contains no credential, no `Bearer` token, and is not blank | SEC-05 | Redaction proven by unit tests; the live round-trip is the only part that requires an external provider | 07-04 operator `approved` |

No human verification items remain pending. The `human_verification` frontmatter key is intentionally omitted because the phase's own blocking human gate was executed and approved before this verification.

### Gaps Summary

No gaps. Every roadmap success criterion is verified against the shipped code; all eight test modules exist and are substantive; all key links are wired; the 93-test suite is green with no skips; the 34-check static invariant audit passes; REFR-03 is intact (the root `app_config.json` is still read and is healthy); and no anti-pattern or stub was found. The four non-portable behaviours rest on the recorded 07-04 operator approval, corroborated on the machine side by integration tests that actually ran.

---

_Verified: 2026-09-22T21:14:57Z_
_Verifier: the agent (gsd-verifier)_
