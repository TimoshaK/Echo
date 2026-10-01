---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: Completed 08-04-SUMMARY.md
last_updated: "2026-09-23T16:09:19.276Z"
last_activity: 2026-09-23
progress:
  total_phases: 8
  completed_phases: 7
  total_plans: 19
  completed_plans: 19
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-03)

**Core value:** Быстрая и точная транскрипция аудиофайлов в удобном интерфейсе с сохранением результатов в читаемых форматах.
**Current focus:** Phase 08 — supply-chain-hardening

## Current Position

Phase: 8
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-09-23

Progress: ██████████ 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 16
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 2 | - | - |
| 6 | 6 | - | - |
| 7 | 4 | - | - |
| 8 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 06 P01 | 2min | 3 tasks | 5 files |
| Phase 06 P02 | 3min | 3 tasks | 3 files |
| Phase 06 P03 | 4min | 3 tasks | 4 files |
| Phase 06 P04 | 93min | 2 tasks | 1 files |
| Phase 06 P05 | 3min | 2 tasks | 3 files |
| Phase 06 P06 | 1min | 2 tasks | 0 files |
| Phase 07 P01 | 5min | 3 tasks | 4 files |
| Phase 07 P02 | 3min | 3 tasks | 7 files |
| Phase 07 P03 | 16min | 3 tasks | 6 files |
| Phase 07 P04 | 5min | 2 tasks | 0 files |
| Phase 08 P01 | 4min | 3 tasks | 4 files |
| Phase 08 P02 | 2min | 3 tasks | 2 files |
| Phase 08 P03 | 3min | 3 tasks | 3 files |
| Phase 08 P04 | 1min | 3 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Split into 2 phases — file selection first, then transcription engine
- [Phase 06]: CONFIG_PATH re-anchored to repo root via Path(__file__).resolve().parent.parent (D-01); naive move would silently break REFR-03
- [Phase 06]: echo/__init__.py stays import-free to keep import echo cheap and avoid a cycle with echo.ui.app
- [Phase 06]: map_transcription_error preserves exact branch order (ffmpeg before format; model only when format/codec absent)
- [Phase 06]: echo.llm_client is stateless: config is passed explicitly into post_chat, and the seven pure helpers moved as module-level functions
- [Phase 06]: parse_json_content kept linear-only (strip + first-{/last-} slice + json.loads); import re asserted absent (T-260921-04)
- [Phase 06]: is_layer_failure truth table preserved exactly (None/400/422 True; 401/403/429/5xx/0 False) so terminal errors never retry
- [Phase 06]: SummarizationEngine no longer owns the eight moved helpers; only _request_content + summarize remain as ladder members delegating to echo.llm_client
- [Phase 06]: echo/ui/build.py header docstring omits the literal echo.ui.app token because the plan's own cycle-guard verify forbids it in source
- [Phase 06]: build.py keeps baseline literals #111111/#666666 (no COLORS key exists for them); only the nine palette colours route through theme.COLORS
- [Phase 06]: configure_combobox_style(app) must run before app.preset_var is created; builder call order preserved from baseline (save_buttons 938 before footer 944)
- [Phase 06]: echo.ui builders take the app instance as a parameter (never import echo.ui.app) breaking the would-be app<->build import cycle
- [Phase 06]: echo.ui.app __init__ maps theme.COLORS into the legacy *_color attributes and constructs self.summarizer BEFORE build_ui(self), because build.py reads both
- [Phase 06]: open_settings stays a one-line delegate to settings_dialog.open_settings(app) so command=app.open_settings keeps binding; the dialog body is single-sourced
- [Phase 06]: TranscriberApp._handle_transcription_error delegates to map_transcription_error; save_transcription_srt delegates to build_srt_content(self.last_segments); _build_ui/_configure_combobox_style/_build_save_buttons/_time_to_srt/_srt_content are deleted
- [Phase 06]: main.py reduced to a 9-line thin launcher (TranscriberApp import + 4-line main()); no re-exports (CONTEXT clean-structure rule)
- [Phase 06]: Root app_config.py deleted atomically with the launcher rewrite; echo/config.py is the only config module (no split-brain, T-06-08)
- [Phase 06]: echo/__main__.py added so py -3 -m echo works; main.spec set hiddenimports=['echo'] (gitignored, non-blocking)
- [Phase 06]: D-05 Check 2 substring assertion corrected to import-intent: echo/config.py must name app_config.json (REFR-03), so the bare 'app_config' substring test was unpassable as written
- [Quick 260922-esl]: Docs-only — README.md и SETUP_GUIDE.txt приведены к пакету echo/; код не менялся, новых доков не создавалось (scope строго два файла)
- [Quick 260922-esl]: Privacy-раскрытие — опциональный конспект (GENERATE SUMMARY) отправляет ТЕКСТ транскрипции в OpenRouter, аудио и транскрибация остаются локальными (T-260922-01)
- [Phase 06]: REFR-02 mechanical proof: 50/50 tkinter constructors textually identical to baseline 6887892 (WIDGET_PARITY_EXACT); comparator kept transient in temp (not committed, D-05 convention)
- [Phase 06]: 06-06 human-verify checkpoint (blocking) resolved by operator typing approved; visual parity + select-transcribe-summarize-save + root app_config.json all confirmed (T-06-26 named attestation)
- [Phase 06]: 06-06 has files_modified=[] so no per-task commits: Task 1 wrote only temp, Task 2 changed no files; plan contributes a single metadata commit
- [Phase 07]: sanitize_error_detail order: cap input to 4000 -> remove configured secrets (>=4 chars) -> Bearer/sk-/userinfo/long-token regex -> flatten whitespace -> bound with ellipsis; InvalidBaseUrlError derives from ValueError so is_layer_failure does not retry a bad base_url (T-07-01-01)
- [Phase 07]: SafeRedirectHandler strips Authorization whenever the redirect changes scheme, host or port; requests go through a private cached build_opener and the process-global urllib opener is never mutated (T-07-01-02/06)
- [Phase 07]: Plan 07-01 deviations were plan-internal contradictions: two sanitize tests corrected (x*300 is swallowed by the long-token rule; .rstrip() yields 302 not 303) and the _http_opener docstring reworded to omit the forbidden install_opener literal
- [Phase 07]: SEC-01/04: save_config is atomic (mkstemp+fsync+os.replace) and owner-only (0600 + non-fatal Windows icacls ACL); load_config raises ConfigCorruptError(path, detail) for any unusable existing file while a missing file still yields defaults, and DEFAULT_CONFIG is no longer aliasable
- [Phase 07]: SEC-06: requirements.txt pinned to the installed versions (numpy corrected DOWN to 2.4.4 from the unmet >=2.5.0 floor; torch pinned 2.14.0 without the +cu130 local tag); unused srt removed and README/SETUP_GUIDE made truthful
- [Phase 07]: SEC-04 engine half: SummarizationEngine captures ConfigCorruptError into config_error (str) and runs on a deep copy of DEFAULT_CONFIG, is_configured() returns False while corruption is recorded, summarize() fails fast naming app_config.json, and the summary_error queue payload is sanitized at the source
- [Phase 07]: SEC-02 UX half: settings_dialog.validate_settings_base_url returns (ok, url_or_message) and never raises; save_settings shows the reason and keeps the dialog open (typed key not lost) instead of persisting a non-https base_url, and a valid URL is normalized before update_config
- [Phase 07]: SEC-04/05 UI half: TranscriberApp defers _show_config_error via root.after(200, ...) naming app_config.json, and _handle_summary_error sanitizes again with secrets=(api_key,), limit=500 with a 'нет деталей' placeholder so the dialog is never blank; _handle_transcription_error stays unsanitized (accepted T-07-03-05)
- [Phase 07]: 07-04 verification-only plan: full suite 93/93 OK plus 34/34 static invariants prove the hardening primitives are CALLED in the shipped paths (validate_base_url in post_chat and before the dialog persists, sanitize_error_detail at request/queue/display, os.replace replacing in-place truncation, ConfigCorruptError surfaced); no source files changed (files_modified: [])
- [Phase 07]: 07-04 blocking human-verify checkpoint resolved by operator typing approved: corrupt-config dialog naming app_config.json (SEC-04), refused http://example.com/v1 with the dialog staying open (SEC-02), owner-only icacls with no (I)/Users/Everyone entries (SEC-01), and a live summary error containing no key/Bearer and not blank (SEC-05)
- [Phase 07]: 07-04 live-config note: current app_config.json sha256 is d827c34a… (250 bytes, trailing newline from the 07-02 atomic writer) vs the 07-02/07-03 snapshot bd409a72…; the app re-saved it in the interim. Hash stable across the suite run, mtime unchanged, gitignored, never printed/committed
- [Phase 08]: Phase 08-01: requirements.txt is now a pip-compile CPU lock (24 packages, 634 sha256 hashes); requirements-dev.txt pins pip-tools/pip-audit/pyinstaller + transitive (391 hashes). The four SEC-06 direct pins are unchanged
- [Phase 08]: Phase 08-01: --allow-unsafe is mandatory (torch declares setuptools>=77.0.3); without it pip-tools drops setuptools and --require-hashes fails. CUSTOM_COMPILE_COMMAND yields a truthful header with no spurious --no-index
- [Phase 08]: Phase 08-01: pure-PyPI --generate-hashes sources every digest from the PyPI JSON API (zero wheel downloads). Negative control must tamper ALL hashes of a requirement: pip accepts a package if any single listed hash matches
- [Phase 08]: Phase 08-02: requirements-cuda.txt pins torch==2.14.0+cu130 from https://download.pytorch.org/whl/cu130 with all 24 index-published sha256 hashes — a separate lock because the +cu130 build is not on PyPI
- [Phase 08]: Phase 08-02: the CUDA lock is a copy of the CPU lock with only the torch block swapped, compiled with pip-compile --generate-hashes --reuse-hashes so every hash is reused and ZERO CUDA wheels download; --emit-index-url stays ON (unlike 08-01's --no-emit-index-url) so --require-hashes can reach the cu130 wheel
- [Phase 08]: Phase 08-02: proven parity — every non-torch package has identical version AND hash set in both locks, and the locked torch hashes equal the live cu130 index; the hash-checking mechanism accepts the file (Would install tqdm-4.70.0)
- [Phase 08]: Phase 08-03: tests/test_requirements_pinning.py rewritten to the hashed-lock contract (20 tests: 12 lock-contract + 8 doc) — parses pip-compile syntax, asserts every requirement pinned+hashed, no line silently skipped, CUDA torch swap + single cu130 index + CPU/CUDA parity, dev lock pins pip-tools/pip-audit/pyinstaller==6.19.0
- [Phase 08]: Phase 08-03: installed-version assertion scoped to the four DIRECT deps only; transitive lock pins float above installed (typing-extensions 4.15.0->4.16.0, urllib3 2.7.0->2.8.0, setuptools 82.0.1->84.0.0) so an all-pins assertion is unpassable. installed.split('+')[0] keeps torch valid (installed 2.14.0+cu130 vs CPU lock 2.14.0)
- [Phase 08]: Phase 08-03: docs teach hash verification by default — README/SETUP_GUIDE install with --require-hashes for requirements.txt + requirements-cuda.txt (+ dev lock), README gains lock-regeneration and local pip-audit (no CI) sections; echo/srt.py mention preserved and no srt dependency re-asserted
- [Phase 08]: Phase 08-03: non-vacuity proven by two monkey-patch mutation controls — stripping hashes from a CPU-lock copy yields 24 failures; a bogus numpy hash in a CUDA-lock copy yields 1 parity failure; full suite 106 tests OK. Both docs remain UTF-8 CRLF-only
- [Phase 08]: Phase 08-04: verification-only plan (files_modified=[]) — no repo file changed; proven installability separately from well-formedness. Clean venv installed requirements.txt under --require-hashes (exit 0), installed tree matched the lock for all 24 packages on the CPU build (torch 2.14.0, not +cu130), pip check clean
- [Phase 08]: Phase 08-04: pip-audit clean on both locks (No known vulnerabilities found); torch==2.14.0+cu130 is skipped because the +cu130 build is not on PyPI — expected, not a finding. Full suite 106 tests OK
- [Phase 08]: Phase 08-04: blocking CUDA human-verify checkpoint (Task 3) resolved by operator typing approved; no torch.cuda.is_available() value was supplied, so none is recorded (False would have been acceptable for install verification on a non-GPU machine)

### Roadmap Evolution

- Phase 6 added: Рефакторинг main.py (1467 строк) в пакет echo/ с подпакетом echo/ui/ (config, presets, errors, llm_client, srt, engines, ui); main.py — тонкий лаунчер; CONFIG_PATH указывает на корневой app_config.json; поведение не меняется
- Phase 7 added: Security Hardening — chmod 0600 + атомарная запись app_config.json; валидация base_url (https-only); безопасные редиректы (без переноса Authorization); явное сообщение при повреждённом конфиге; санитизация деталей ошибок API; пины версий + удаление неиспользуемого srt
- Phase 8 added: Supply-chain hardening — requirements.in + pip-tools --generate-hashes; CPU-lock requirements.txt и отдельный CUDA-lock requirements-cuda.txt (torch +cu130); dev-lock (pip-tools, pip-audit); установка через --require-hashes; обновление invariant-теста и README/SETUP_GUIDE; локальный гайд pip-audit без CI
- Phase 9 added: Containerized GUI delivery — VNC (x11vnc + noVNC + websockify) в Docker-образе, GUI в браузере на :6080; entrypoint поднимает Xvfb + python -m echo + x11vnc + websockify; корпоративный OpenAI-совместимый https LLM через монтируемый app_config.json; инструкция развёртывания на другом ПК

### Pending Todos

- [Consider Docker for headless CLI batch transcription](./todos/pending/2026-09-22-consider-docker-for-headless-cli-batch-transcription.md)

### Blockers/Concerns

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260921-ofx | Пресеты конспектов: Combobox в панели SYSTEM STATUS + JSON response_format | 2026-09-21 | 7ac7418 | Needs Review | [260921-ofx-combobox-system-status-json-response-for](./quick/260921-ofx-combobox-system-status-json-response-for/) |
| 260922-esl | README.md и SETUP_GUIDE.txt под рефактор Phase 6 (пакет echo/, конспект OpenRouter + пресеты, FFmpeg, py -3) | 2026-09-22 | 4053e57, e30cdc2 | Needs Review | [260922-esl-readme-md-setup-guide-txt-phase-6-echo-c](./quick/260922-esl-readme-md-setup-guide-txt-phase-6-echo-c/) |

Last activity: 2026-09-22 - Completed quick task 260922-esl: README.md и SETUP_GUIDE.txt обновлены под рефактор Phase 6 (echo/ package)

## Session Continuity

Last session: 2026-09-23T16:04:01.262Z
Stopped at: Completed 08-04-SUMMARY.md
Resume file: None
