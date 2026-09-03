---
phase: 03-summarization
plan: 01
subsystem: api
tags: [llm, openrouter, summarization, tkinter, pluggable-api]
requires:
  - phase: 02-transcription-engine
    provides: transcription engine, queue-based threading pattern, TranscriberApp GUI
provides:
  - Pluggable LLM summarization engine (OpenAI-compatible, defaults to OpenRouter)
  - Persistent API config storage (app_config.json) independent of app code
  - GUI settings dialog for API key/base url/model/enabled
  - GUI summary generation flow via queue-based threading
affects: [04-output-storage]
tech-stack:
  added: [none - uses stdlib urllib.request]
  patterns:
    - Pluggable LLM provider via configurable base URL + API key
    - Config persistence via dedicated app_config.py module
    - Background thread + queue polling (reuses transcription pattern)
key-files:
  created: [app_config.py, .gitignore]
  modified: [main.py]
key-decisions:
  - "Use stdlib urllib.request instead of requests lib to keep dependencies minimal"
  - "OpenAI-compatible /chat/completions endpoint for provider independence (OpenRouter works out of the box)"
  - "API settings stored in app_config.json (gitignored to avoid committing secrets)"
  - "Summary button gated on existing transcription; settings always available"
patterns-established:
  - "Pattern: pluggable external-service client isolated in its own engine class"
  - "Pattern: config module (app_config.py) separate from UI code"
requirements-completed: [SUMR-01, SUMR-02]

# Metrics
duration: 20min
completed: 2026-09-04
---

# Phase 3: Summarization Summary

**Pluggable LLM summarization engine (OpenAI-compatible, OpenRouter-ready) with a GUI settings dialog and queue-based summary generation**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-04
- **Completed:** 2026-09-04
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- SummarizationEngine class that calls any OpenAI-compatible `/chat/completions` endpoint (defaults to OpenRouter) using only the standard library
- Persistent, independent API configuration (api_key, base_url, model, enabled) stored in gitignored `app_config.json`
- GUI settings dialog to configure the API without touching app code
- GENERATE SUMMARY button that becomes enabled after transcription and shows the конспект in the result area
- Queue-based threading reused from the transcription engine for safe UI updates

## Task Commits

1. **Task 1: SummarizationEngine + config module** - `4e28852` (feat)
2. **Task 2: GUI integration with settings dialog** - `4e28852` (feat)

**Plan metadata:** `4e28852` (feat: add pluggable LLM summarization via OpenRouter)

## Files Created/Modified
- `app_config.py` - Loads/saves persistent LLM API config (key, base url, model, enabled)
- `main.py` - Added SummarizationEngine, summary + settings GUI controls, poll handlers
- `.gitignore` - Ignore pycache, build/dist artifacts, app_config.json (contains API key)

## Decisions Made
- Used stdlib `urllib.request` instead of requests to avoid adding a dependency
- Targeted OpenAI-compatible `/chat/completions` for true provider independence (swap OpenRouter for anything compatible)
- Stored config in gitignored `app_config.json` to keep secrets out of the repo while staying user-editable
- Gated summary action on an existing transcript; API settings always accessible regardless of transcription state

## Deviations from Plan
- None - plan executed exactly as written.

## Issues Encountered
- None.

## User Setup Required
**External service requires manual configuration.** See `03-01-USER-SETUP.md` guidance:
- Get a free API key at `https://openrouter.ai/keys`
- In the app, open "API SETTINGS", paste the key, confirm model + base URL, tick "Enable LLM API", Save.

## Next Phase Readiness
- Summarization ready; Phase 4 (Output Storage) can save the transcript and summary to .txt and .srt
- `last_transcript` and summary text are available in the app for export
- No blockers.

---
*Phase: 03-summarization*
*Completed: 2026-09-04*
