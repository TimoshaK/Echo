---
phase: quick-260922-esl
plan: 01
subsystem: docs
tags: [readme, setup-guide, documentation, echo-package, openrouter, ffmpeg, privacy]

# Dependency graph
requires:
  - phase: 06-refactor-main-into-echo-package
    provides: echo/ package (config, presets, errors, llm_client, srt, engines, ui/), thin main.py launcher, CONFIG_PATH to repo-root app_config.json, py -3 -m echo entry point
provides:
  - README.md updated for Phase 6 (summary/preсets, echo/ + echo/ui/ architecture, FFmpeg install step, Configuration section, privacy disclosure)
  - SETUP_GUIDE.txt updated for Phase 6 (echo/config.py CONFIG_PATH, echo/ package tree, py -3 entry points, stale dist/ note)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Surgical in-place docs edit: preserve author voice, section order, ASCII diagrams, tables, plain-text box style"
    - "Docs-only change: no code, no new files, no behavior change"

key-files:
  created: []
  modified: [README.md, SETUP_GUIDE.txt]

key-decisions:
  - "Docs-only scope: exactly README.md and SETUP_GUIDE.txt touched; no new doc files created"
  - "README edited in-place preserving author voice/structure; SETUP_GUIDE.txt box style (# ==== / ---- separators, section numbers) preserved and new section numbered 11"
  - "Environment fact honored: Windows runs use py / py -3 because the python alias is broken; Linux/macOS keep python3"
  - "Privacy disclosure (T-260922-01): optional GENERATE SUMMARY sends transcription TEXT to OpenRouter while audio and base transcription stay local"
  - "app_config.json is gitignored and holds a live API key — only its location (repo root) is documented; never printed or committed"

requirements-completed: [REFR-01, REFR-02]

# Metrics
duration: 40min
completed: 2026-09-22
---

# Quick 260922-esl: README and SETUP_GUIDE updates for Phase 6 Echo package

**Readme and setup guide realigned to the Phase 6 `echo/` package refactor: document OpenRouter summarization and presets, mandatory FFmpeg install, `py -3` entry points, repo-root `app_config.json`, and an explicit privacy disclosure that only transcription text leaves the machine.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-09-22T03:41:59Z
- **Completed:** 2026-09-22T04:21:28Z
- **Tasks:** 2 of 2
- **Files modified:** 2

## Accomplishments
- README.md now documents the optional LLM summary (OpenRouter), the five presets, JSON-schema structured output, the **API SETTINGS** dialog and `.txt`/`.srt` saving, with an `### Summarization flow` subsection and an extended ASCII diagram showing the summarization branch separate from local transcription.
- README.md Architecture now describes `SummarizationEngine` (layer ladder `json_schema` → `json_object` → plain text, terminal errors not retried), `llm_client` (single network point, stdlib `urllib.request`) and the `echo/` + `echo/ui/` package layout; Tech Stack gains an OpenRouter LLM row and marks `srt` as declared-but-unused.
- README.md Installation adds a mandatory FFmpeg step and switches Windows venv/pip to `py -3`; Run shows `py -3 main.py` and `py -3 -m echo`; Project structure shows the real tree; a new **Configuration** section documents `app_config.json` keys/presets; Privacy now discloses that summary text goes to OpenRouter; Roadmap marks summary, presets and architecture improvements done.
- SETUP_GUIDE.txt now points to `echo/config.py` (with `CONFIG_PATH` re-anchored to the repo root via `Path(__file__).resolve().parent.parent / "app_config.json"`), states the whisper call site is `echo/transcription_engine.py`, marks `dist/` as STALE (built from the old monolith; rebuild needed; `build/` ~150 MB, `dist/` ~3 GB), adds a section 11 with the `echo/` package tree, and uses `py -3 main.py` / `py -3 -m echo` throughout.
- Cross-document consistency verified: no `app_config.py` module reference, no `python main.py` / `py main.py`, both docs agree on package name, entry points, config path and FFmpeg role.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update README.md for Phase 6** - `4053e57` (docs)
2. **Task 2: Update SETUP_GUIDE.txt + cross-check** - `e30cdc2` (docs)

**Plan metadata:** committed by orchestrator (docs: complete plan)

## Files Created/Modified
- `README.md` - Features, How it works (summarization branch + flow), Architecture (`SummarizationEngine`, `llm_client`, package layout), Tech Stack row for OpenRouter LLM, Installation FFmpeg step + `py -3`, Run entry points, Project structure tree, new Configuration section, Privacy disclosure, Roadmap ticks.
- `SETUP_GUIDE.txt` - Section 3 (`echo/` + `py -3`), Section 4.1 (call site), Section 7 (config module + stale `dist/` rebuild note with sizes), new Section 11 (`echo/` package tree), Section 8 scenarios (`py -3 main.py`).

## Decisions Made
- Kept the docs change strictly surgical: edits are insertions/point replacements in the author's existing Russian voice and formatting; no sections regenerated from scratch.
- Set the new SETUP_GUIDE structure section as number 11, placed before the ИСТОЧНИКИ block, to avoid renumbering existing sections 1–10.
- Described `app_config.json` only by its location (repository root) and keys; the file is gitignored and was neither read, printed nor committed.

## Deviations from Plan

None - plan executed exactly as written. Minor wording in the SETUP_GUIDE section 3 "python alias" warning was preserved in spirit (now also recommends `py -3`); this was explicitly requested by the plan.

## Issues Encountered
- `rg` (ripgrep) is not installed on this machine; verification greps were run with the Grep tool and PowerShell `Select-String` instead, with equivalents covering every required present/absent pattern.

## User Setup Required

None - documentation only; no external service configuration required.

## Next Phase Readiness
- Docs now match the Phase 6 `echo/` package, so readers are no longer pointed at the deleted monolithic `main.py` or the removed `app_config.py` module.
- Threat mitigations satisfied: T-260922-01 (privacy disclosure of summary text to OpenRouter) and T-260922-02 (mandatory FFmpeg step with `ffmpeg -version` check and `py`/`py -3` guidance).
- No blockers.

---
*Quick task: 260922-esl*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: README.md
- FOUND: SETUP_GUIDE.txt
- FOUND: .planning/quick/260922-esl-readme-md-setup-guide-txt-phase-6-echo-c/260922-esl-SUMMARY.md
- FOUND: 4053e57 (Task 1)
- FOUND: e30cdc2 (Task 2)
