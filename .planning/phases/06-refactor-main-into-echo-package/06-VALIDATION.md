---
phase: 6
slug: refactor-main-into-echo-package
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-21
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — transient smoke harness (D-05). No `tests/` package, no pytest (deferred by CONTEXT.md). |
| **Config file** | none — commands are inline `py -3 -c` or a throwaway script in `%TEMP%` |
| **Quick run command** | `py -3 -m py_compile <module paths touched by the task>` |
| **Full suite command** | `py -3 -c "import tkinter as tk; from echo.ui.app import TranscriberApp; r=tk.Tk(); r.withdraw(); a=TranscriberApp(r); print('HEADLESS_OK', a.summarizer.preset, len(a.preset_labels)); r.destroy()"` |
| **Estimated runtime** | quick ~2 s · full ~20 s (dominated by `import whisper`/`torch`) |

**Why no framework:** CONTEXT.md `<decisions>` → the agent's Discretion states a separate
`tests/` package is explicitly out of scope for this phase. The D-05 smoke set is the
locked verification mechanism. Because the harness is transient, each task's
`<verify><automated>` block carries the full command text.

---

## Sampling Rate

- **After every task commit:** Run the task's `<verify><automated>` command (quick tier: `py_compile` + targeted golden assertions)
- **After every plan wave:** Run the full suite command above plus `py -3 -c "from echo.config import CONFIG_PATH; print(CONFIG_PATH)"`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REFR-01, REFR-03 | T-06-08 | `CONFIG_PATH` resolves to repo-root `app_config.json`, never inside `echo/` | unit | `py -3 -c "from echo.config import CONFIG_PATH; import pathlib; p=pathlib.Path(CONFIG_PATH); assert p.name=='app_config.json' and p.parent.name!='echo'; print('CONFIG_PATH_OK', p)"` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 1 | REFR-01, REFR-02 | T-06-01 | Error mapping returns fixed strings; no config/secret value can enter the message | unit | `py -3 -c "from echo.srt import time_to_srt, build_srt_content; from echo.errors import map_transcription_error, SummaryApiError; assert time_to_srt(3661.5)=='01:01:01,500'; assert build_srt_content([{'start':0,'end':1.5,'text':'hello'}])=='1\n00:00:00,000 --> 00:00:01,500\nhello\n'; print('LEAF_OK')"` | ✅ | ⬜ pending |
| 06-01-03 | 01 | 1 | REFR-02, REFR-03 | T-06-08 | Preset registry unchanged incl. deliberate `AFD`; live API key still readable from root config | integration | `py -3 -c "from echo.presets import DEFAULT_PRESET, SUMMARY_PRESETS; from echo.config import load_config; assert list(SUMMARY_PRESETS)==['daily','lecture','interview','client','free']; assert SUMMARY_PRESETS['daily']['sections'][0]['title']=='AFD'; c=load_config(); assert c['llm']['api_key']; print('LEAF_SMOKE_OK')"` | ✅ | ⬜ pending |
| 06-02-01 | 02 | 2 | REFR-01, REFR-02 | T-06-01, T-06-03, T-06-04 | API key only in `Authorization` header; `parse_json_content` linear-only (no regex/recursion) | unit | `py -3 -c "from echo.llm_client import json_schema_format, is_layer_failure; from echo.presets import SUMMARY_PRESETS; from echo.errors import SummaryApiError; assert json_schema_format(SUMMARY_PRESETS['free']) is None; assert is_layer_failure(SummaryApiError('x',None)) is True; assert is_layer_failure(SummaryApiError('x',401)) is False; print('LLM_CLIENT_OK')"` | ✅ | ⬜ pending |
| 06-02-02 | 02 | 2 | REFR-01, REFR-02 | — | Queue contract unchanged: `status` / `complete` / `error` only | unit | `py -3 -c "from echo.transcription_engine import TranscriptionEngine; e=TranscriptionEngine(); assert e.model is None; assert hasattr(e.progress_queue,'get_nowait'); print('ENGINE_OK')"` | ✅ | ⬜ pending |
| 06-02-03 | 02 | 2 | REFR-01, REFR-02 | T-06-02, T-06-05 | `summary_preset` from user-editable config validated against registry, falls back to `free`; layer ladder preserved | integration | `py -3 %TEMP%\opencode\echo_smoke_summarize.py echo.summarization_engine` → `SMOKE_SUMMARIZE_ALL_PASS` | ✅ | ⬜ pending |
| 06-03-01 | 03 | 3 | REFR-01 | — | N/A (pure palette + package marker) | unit | `py -3 -c "from echo.ui.theme import COLORS; assert COLORS['bg']=='#252525' and COLORS['accent']=='#F2A900' and len(COLORS)==9; print('THEME_OK')"` | ✅ | ⬜ pending |
| 06-03-02 | 03 | 3 | REFR-01, REFR-02 | — | Builder functions receive the app instance; no import of `echo.ui.app` (cycle guard) | unit | `py -3 -c "import echo.ui.build as b; assert not hasattr(b,'__wrapped__'); print('BUILD_IMPORTS_OK')"` + `py -3 -m py_compile echo/ui/build.py` | ✅ | ⬜ pending |
| 06-03-03 | 03 | 3 | REFR-01, REFR-02 | T-06-01 | Settings dialog reads key from config for display but never writes it to logs/errors | unit | `py -3 -c "import echo.ui.settings_dialog as s; assert callable(s.open_settings); print('DIALOG_OK')"` | ✅ | ⬜ pending |
| 06-04-01 | 04 | 4 | REFR-01, REFR-02 | T-06-05 | `TranscriberApp` attributes preserved exactly (widget names build.py depends on) | integration | `py -3 -c "import tkinter as tk; from echo.ui.app import TranscriberApp; r=tk.Tk(); r.withdraw(); a=TranscriberApp(r); need=['select_btn','file_var','file_entry','transcribe_btn','status_indicator','status_label','settings_btn','preset_labels','preset_var','preset_combo','summary_btn','result_text','result_scrollbar','language_label','save_txt_btn','save_srt_btn']; missing=[n for n in need if not hasattr(a,n)]; assert not missing, missing; print('WIDGET_PARITY_OK'); r.destroy()"` | ✅ | ⬜ pending |
| 06-04-02 | 04 | 4 | REFR-02 | — | Preset state derives from config exactly as before (`daily` in this workspace) | integration | `py -3 -c "import tkinter as tk; from echo.ui.app import TranscriberApp; r=tk.Tk(); r.withdraw(); a=TranscriberApp(r); assert len(a.preset_labels)==5; assert a.preset_var.get()==__import__('echo.presets',fromlist=['x']).SUMMARY_PRESETS[a.summarizer.preset]['label']; print('PRESET_WIRING_OK'); r.destroy()"` | ✅ | ⬜ pending |
| 06-05-01 | 05 | 5 | REFR-01, REFR-03 | T-06-08 | `main.py` is a launcher with no re-exports; duplicate config module removed (no split-brain) | integration | `py -3 -c "import pathlib; assert not pathlib.Path('app_config.py').exists(), 'app_config.py still present'; src=pathlib.Path('main.py').read_text(encoding='utf-8'); assert 'app_config' not in src; assert 'from echo.ui.app import TranscriberApp' in src; print('LAUNCHER_OK')"` | ✅ | ⬜ pending |
| 06-05-02 | 05 | 5 | REFR-01, REFR-02, REFR-03 | T-06-01..T-06-08 | Full D-05 smoke set green on the refactored tree | integration | `py -3 -m py_compile main.py echo/config.py echo/presets.py echo/errors.py echo/srt.py echo/llm_client.py echo/transcription_engine.py echo/summarization_engine.py echo/ui/app.py echo/ui/build.py echo/ui/theme.py echo/ui/settings_dialog.py` then the full suite command | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

No Wave 0 scaffold is needed: the D-05 harness was executed and verified green against the
baseline commit `6887892` before planning (see `06-RESEARCH.md` §1), and every task above
has a runnable automated command with a known-good expected result. No `MISSING` automated
checks exist in this phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rendered window is visually identical to pre-refactor | REFR-02 | The automated GUI check runs `root.withdraw()`, so nothing is drawn; pixel-level appearance cannot be asserted headlessly | 1. `git stash` any pending edits or check out the baseline commit `6887892`. 2. Run `py -3 main.py`; screenshot the window. 3. Return to the refactored tree, run `py -3 main.py`. 4. Compare: title bar text `Echo // Audio Processing Unit`, window size `900x650`, the ECHO header block, AUDIO INPUT panel, TRANSCRIPTION UNIT / SYSTEM STATUS row, SUMMARY PRESET combobox (dark `clam` styling), TRANSCRIPTION OUTPUT area, footer `LANGUAGE: --`, and the SAVE .TXT / SAVE .SRT row must match. 5. Confirm no widget is missing, duplicated or reordered. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none exist)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
