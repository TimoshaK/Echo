---
phase: 04-output-storage
plan: 01
subsystem: ui
tags: [storage, srt, txt, tkinter, subtitles, export]
requires:
  - phase: 03-summarization
    provides: summary text and last_transcript available for export
provides:
  - User-chosen folder/location save of transcription to .txt
  - .srt subtitle export with timestamps from whisper segments
  - Optional summary inclusion in .txt output
affects: []
tech-stack:
  added: [none]
  patterns:
    - Save buttons enabled only after transcription completes
    - SRT generation from whisper segment timestamps
key-files:
  created: []
  modified: [main.py]
key-decisions:
  - "Use asksaveasfilename (file-level) rather than askdirectory for flexible naming"
  - "Include summary as a КОНСПЕКТ section appended to the .txt transcript"
  - "Carry whisper segments through the completion message for SRT generation"
patterns-established:
  - "Pattern: export enabled/gated on completion state in app controller"
  - "Pattern: deterministic SRT formatting via _time_to_srt helper"
requirements-completed: [STOR-01, STOR-02, STOR-03, STOR-04]

# Metrics
duration: 15min
completed: 2026-09-04
---

# Phase 4: Output Storage Summary

**User-chosen .txt and .srt export of transcription with optional summary, driven by whisper segment timestamps for subtitles**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-04
- **Completed:** 2026-09-04
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- SAVE .TXT and SAVE .SRT buttons appear and enable after transcription completes
- .txt export writes the full transcript, appending a КОНСПЕКТ section when a summary was generated
- .srt export generates valid subtitle files from whisper segment timestamps
- Save location chosen via native save dialog per file type
- UTF-8 encoding used for all output to preserve Cyrillic text

## Task Commits

1. **Task 1: segments + save buttons** - `bafc65e` (feat)
2. **Task 2: .txt/.srt saving** - `bafc65e` (feat)

**Plan metadata:** `bafc65e` (feat: add .txt and .srt output storage with folder selection)

## Files Created/Modified
- `main.py` - Added save buttons, _time_to_srt/_base_name/_srt_content helpers, save_transcription_txt, save_transcription_srt; carried segments through completion message; tracked last_segments and last_summary

## Decisions Made
- Chose `asksaveasfilename` per format so users name files flexibly (over a single directory picker)
- Appended summary to the transcript in .srt as a distinct КОНСПЕКТ section
- Exposed whisper segments via the completion message so the app can build SRT without re-analysis

## Deviations from Plan
- None - plan executed exactly as written.

## Issues Encountered
- None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both output mechanisms (transcription + summary) can be persisted to disk
- Feature set for v1.1 (summarization + storage) is complete; ready for milestone verification
- No blockers.

---
*Phase: 04-output-storage*
*Completed: 2026-09-04*
