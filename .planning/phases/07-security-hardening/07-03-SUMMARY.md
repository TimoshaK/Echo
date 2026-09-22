---
phase: 07-security-hardening
plan: 03
subsystem: ui
tags: [tkinter, config-corruption, base-url-validation, redaction, messagebox, unittest, tdd]

# Dependency graph
requires:
  - phase: 07-security-hardening
    provides: "07-01: sanitize_error_detail + InvalidBaseUrlError (echo/errors.py), validate_base_url (echo/llm_client.py)"
  - phase: 07-security-hardening
    provides: "07-02: ConfigCorruptError(path, detail) raised by load_config on any unusable existing file"
provides:
  - "echo/summarization_engine.py: config_error state captured from ConfigCorruptError, DEFAULT_CONFIG fallback, fail-fast summarize, sanitized summary_error queue payload (SEC-04, SEC-05)"
  - "echo/ui/settings_dialog.py: validate_settings_base_url + save_settings guard that never persists a non-https base_url (SEC-02 UX half)"
  - "echo/ui/app.py: deferred _show_config_error startup dialog naming app_config.json and _handle_summary_error with a second sanitization barrier (SEC-04, SEC-05)"
  - "durable tests/test_engine_config_error.py, test_settings_validation.py, test_app_error_display.py"
affects: [07-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Capture-at-construction: the engine records a typed failure into config_error instead of raising, and every consumer degrades to defaults"
    - "Two-barrier redaction: sanitize the queue payload at the source AND again with an explicit secret right before the messagebox"
    - "Pure validation seam: validate_settings_base_url returns (ok, value_or_message) and never raises, so the Tk shell is untested but the contract is fully tested"
    - "Deferred modal: root.after(200, handler) so a startup messagebox cannot block Tk's initial layout"

key-files:
  created:
    - tests/test_engine_config_error.py
    - tests/test_settings_validation.py
    - tests/test_app_error_display.py
  modified:
    - echo/summarization_engine.py
    - echo/ui/settings_dialog.py
    - echo/ui/app.py

key-decisions:
  - "Kept the plan's implementations byte-for-byte in all three tasks; no deviations were needed"
  - "config_error is a plain str built from ConfigCorruptError.__str__, so the dialog already names app_config.json without the UI importing echo.config"
  - "is_configured() short-circuits on config_error rather than inspecting the config, so a stale in-memory key can never be sent while corruption is recorded"
  - "The queue payload carries the sanitized text (sanitize_error_detail at the source) and the UI sanitizes again with limit=500 — defence in depth against a future unsanitized caller"
  - "The settings dialog stays open on a rejected URL (returns before settings.destroy()) so the typed API key is not lost"
  - "_handle_transcription_error was deliberately left untouched (accepted risk T-07-03-05: local whisper/ffmpeg diagnostics, no network text)"

patterns-established:
  - "Pattern: corruption is a state (self.config_error), not an exception — the Tk main thread must never see ConfigCorruptError"
  - "Pattern: a TDD task's test module is created in the same task that its <verify> command runs, so no test file ever dangles"

requirements-completed: [SEC-02, SEC-04, SEC-05]

# Metrics
duration: 16min
completed: 2026-09-22
---

# Phase 7 Plan 3: Corrupt-Config Surfacing, base_url Dialog Guard and Sanitized Error Display Summary

**A corrupt app_config.json now produces an explicit startup dialog naming the file while the app keeps transcribing, the settings dialog refuses a non-https base_url without persisting it, and the summary error dialog shows redacted, bounded, never-blank text**

## Performance

- **Duration:** 16 min
- **Started:** 2026-09-22T08:54:12Z
- **Completed:** 2026-09-22T09:09:49Z
- **Tasks:** 3
- **Files modified:** 6 (3 modified, 3 created)

## Accomplishments

- `SummarizationEngine.__init__` no longer propagates `ConfigCorruptError`: it stores the reason in `config_error`, deep-copies `DEFAULT_CONFIG` and keeps running, so a damaged config disables only the summary — transcription is unaffected and the window always opens.
- `is_configured()` returns `False` whenever a corruption is recorded (a stale in-memory key can never be used), and `summarize()` fails fast with a message naming `app_config.json` instead of leaking a Python-version-specific JSON parser fragment.
- The `summary_error` queue payload is sanitized at the source with the configured key as an explicit secret, so no future consumer of the queue can observe a credential; the UI adds a second barrier (`limit=500`) and renders `нет деталей` when the sanitized text is empty, so the dialog is never blank.
- `TranscriberApp` schedules a deferred `_show_config_error` dialog (200 ms after construction) that names `app_config.json` and explains the fallback to defaults — replacing the silent key loss with a user-visible cause.
- The settings dialog runs every typed `base_url` through `validate_base_url` before `update_config`: a non-https/empty/userinfo URL shows the reason, keeps the dialog (and the typed key) on screen, and persists nothing; a valid URL is normalized (`https://openrouter.ai/api/v1/` → `https://openrouter.ai/api/v1`) before it is written.
- 22 new stdlib-unittest assertions across three modules, including two headless-Tk integration tests that drive the real SAVE button and the real app construction.

## Task Commits

Each TDD task was committed atomically (test → feat):

1. **Task 1: Engine captures config corruption + sanitized queue payload (SEC-04, SEC-05)** - `06173f3` (test, RED) → `b96e515` (feat, GREEN)
2. **Task 2: Settings-dialog base_url guard (SEC-02)** - `70eb5fe` (test, RED) → `7dd7b4f` (feat, GREEN)
3. **Task 3: Startup corruption dialog + sanitized summary error (SEC-04, SEC-05)** - `0a5e685` (test, RED) → `135ef11` (feat, GREEN)

**Plan metadata:** (docs: complete corrupt-config surfacing plan) — recorded by the final metadata commit

## Files Created/Modified

- `echo/summarization_engine.py` - Added `json` + `DEFAULT_CONFIG`/`ConfigCorruptError`/`sanitize_error_detail` imports; `__init__` captures corruption into `self.config_error: str | None` and falls back to a deep copy of `DEFAULT_CONFIG`; `is_configured()` short-circuits on `config_error`; `summarize()` gained a fail-fast block above the existing `is_configured` check; `_run_summary`'s `except` builds the sanitized payload. The preset validation and the `json_schema → json_object → plain` ladder are unchanged.
- `echo/ui/settings_dialog.py` - Added `messagebox` import, `InvalidBaseUrlError`/`validate_base_url` imports and the `validate_settings_base_url` helper; `save_settings` validates first, shows `messagebox.showerror("Ошибка настроек", result)` and returns without destroying the dialog on failure, and passes `base_url=result`. The widget construction, labels, geometry and colours are byte-identical.
- `echo/ui/app.py` - Import extended to `map_transcription_error, sanitize_error_detail`; `__init__` schedules `self.root.after(200, self._show_config_error)` when `self.summarizer.config_error` is set; new `_show_config_error`; `_handle_summary_error` sanitizes with `secrets=(api_key,), limit=500` and falls back to `'нет деталей'`. `_handle_transcription_error` is untouched.
- `tests/test_engine_config_error.py` - 9 tests: corruption captured (JSON garbage, array root, invalid UTF-8), defaults fallback, `is_configured()` False, fail-fast naming the file, missing file is not corruption, valid config clean, and two `_run_summary` payload tests (redaction present, quoted only once).
- `tests/test_settings_validation.py` - 8 tests: 6 pure `validate_settings_base_url` cases (live URL, trailing-slash normalization, http, empty, userinfo, never-raises loop) + 2 headless-Tk integration tests driving the real SAVE button (invalid refused and not persisted, valid persisted normalized).
- `tests/test_app_error_display.py` - 5 tests: construction survives corruption with `transcribe_btn` present, `_show_config_error` names `app_config.json`, healthy config schedules no dialog, displayed summary error is redacted and non-empty, and the summary button returns to `normal`.

## Decisions Made

- The plan (`<action>`) was implemented exactly as written in all three tasks — including the comment wording, the `is_configured` ordering and the `'нет деталей'` placeholder.
- `config_error` is stored as `str(e)` (not the exception object) because `ConfigCorruptError.__str__` already interpolates the path, which is what lets `_show_config_error` name `app_config.json` without the UI importing `echo.config`.
- The deep copy `json.loads(json.dumps(DEFAULT_CONFIG))` is used instead of `copy.deepcopy` to match `echo/config.py`'s established no-alias idiom.
- Redaction happens twice by design: at the queue boundary (T-07-03-02) so any consumer is safe, and again at the display boundary with `limit=500` (T-07-03-04) so a future caller pushing an unsanitized string still cannot leak.
- The dialog returns before `settings.destroy()` on validation failure (T-07-03-03) — the priority is not losing the typed API key.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `.planning/config.json` shows as `M` in `git status`, but `git diff --numstat` reports zero changed lines (a stale-index / line-ending artifact with a file mtime predating both 07-02 and this plan). It was left untouched and deliberately **not** staged, since it has no content change.
- The full-suite run prints the benign, already-documented `_FakeResponse` deallocator message from 07-01's `tests/test_llm_client.py` at interpreter shutdown; `Ran 93 tests / OK`, exit 0.
- `py -3 -m unittest ...` writes progress to stderr, which Windows PowerShell surfaces as a `NativeCommandError`-styled block even on success; the `Ran N tests ... OK` line and exit code 0 confirm success. The `<automated>` commands were run as written.
- `tests/test_app_error_display.py` imports `echo.ui.app` (→ `whisper`), so it is the slowest module (~2.4 s warm, ~8.2 s cold). Expected and documented in the plan; the pure-unit modules stay fast.

## Stub Tracking

None. No hardcoded empty values flowing to UI, no placeholder/TODO text, no unwired data sources were introduced. The `safe_error or 'нет деталей'` fallback is an intentional user-facing placeholder for an already-sanitized-to-empty error, not a stub.

## Threat Flags

None beyond the plan's `<threat_model>`. The three new behaviours map to T-07-03-01…T-07-03-04 (mitigated) and the two deliberate non-changes to T-07-03-05/T-07-03-06 (accepted). No new network endpoint, auth path, file-access pattern or schema change at a trust boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 07-04 can now run the full suite as its integration gate: `py -3 -m unittest discover -s tests -v` → **93 tests, OK, 3.36 s**, exit 0 (was 71 before this plan).
- Live-config safety confirmed: `app_config.json` is byte-identical before and after the entire suite (sha256 prefix `bd409a7290c56008`), because every new test monkeypatches `echo.config.CONFIG_PATH` into a `TemporaryDirectory` and no test opens a socket.
- Static invariants hold for the wave audit: `import re` absent from `echo/llm_client.py` (0 matches), `os.replace(tmp_path, path)` present in `echo/config.py` (1 match), no plain `open(CONFIG_PATH, "w")` (0 matches), and `echo/summarization_engine.py`'s ladder (`is_layer_failure`, `json_schema` → `json_object` → plain) is textually unchanged.
- The four manual-only verifications remain for 07-04's blocking `checkpoint:human-verify` (corrupt-config dialog, `http://` refusal with a byte-identical file, owner-only permissions on the real filesystem, live error text free of credentials).
- Phase 6 parity preserved: `echo/ui/settings_dialog.py` gained no widgets and `echo/ui/app.py` no layout changes — only the deferred dialog and the validation/error text.

---
*Phase: 07-security-hardening*
*Completed: 2026-09-22*

## Self-Check: PASSED

- Files: all 7 artifacts found on disk (echo/summarization_engine.py, echo/ui/settings_dialog.py, echo/ui/app.py, tests/test_engine_config_error.py, tests/test_settings_validation.py, tests/test_app_error_display.py, 07-03-SUMMARY.md)
- Commits: all 6 task commits verified present (06173f3, b96e515, 70eb5fe, 7dd7b4f, 0a5e685, 135ef11)
