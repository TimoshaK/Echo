# Roadmap: Whisper Transcriber

## Overview

A focused two-phase build that delivers a complete desktop transcription tool. Phase 1 establishes the GUI and file selection workflow. Phase 2 integrates Whisper for transcription, result display, and error handling. The result is a working app where users pick an audio file, click one button, and get their transcription text.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: GUI & File Selection** - Project setup, tkinter interface, and audio file selection dialog
- [x] **Phase 2: Transcription Engine** - Whisper integration, transcription execution, result display, and error handling
- [x] **Phase 3: Summarization** - Generate brief summary of transcription via OpenRouter LLM API
- [x] **Phase 4: Output Storage** - Choose storage location and save results in .txt and .srt formats
- [ ] **Phase 5: Packaging & Distribution** - Document dependencies (Python, FFmpeg), install process, and optional standalone executable
- [ ] **Phase 6: Refactor main.py into echo package** - Split the monolithic main.py into the echo/ package with a UI subpackage, without changing behavior

## Phase Details

### Phase 1: GUI & File Selection
**Goal**: Users can launch the application and select audio files for transcription
**Depends on**: Nothing (first phase)
**Requirements**: FILE-01, FILE-02
**Success Criteria** (what must be TRUE):
  1. User can launch the application and see a window with a "Select File" button and area to display the file path
  2. User can click "Select File" to open a file browser and choose an audio file
  3. User sees the full path of the selected file displayed in the interface
**Plans**: 1 plan
**UI hint**: yes

Plans:
- [ ] 01-01-PLAN.md — Project setup + tkinter GUI with file selection

### Phase 2: Transcription Engine
**Goal**: Users can transcribe selected audio files to text with one click
**Depends on**: Phase 1
**Requirements**: TRNS-01, TRNS-02, RESL-01, ERRR-01
**Success Criteria** (what must be TRUE):
  1. User can click a "Transcribe" button to start processing the selected file
  2. User sees the complete transcription text displayed in the interface after processing
  3. Application automatically detects the audio language without user input
  4. User sees clear error messages via messagebox when transcription fails
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 02-01-PLAN.md — Transcription engine core with threading pattern
- [x] 02-02-PLAN.md — GUI integration with error handling

### Phase 3: Summarization
**Goal**: User can generate a brief summary (конспект) of the transcription using a pluggable OpenRouter LLM API
**Depends on**: Phase 2
**Requirements**: SUMR-01, SUMR-02
**Success Criteria** (what must be TRUE):
  1. User can generate a summary of the transcription text with one action
  2. LLM provider is pluggable (configurable base URL + API key), independent from the app
  3. User sees the summary displayed in the interface
**Plans**: 1 plan
**UI hint**: yes

Plans:
- [x] 03-01-PLAN.md — OpenRouter summarization integration with pluggable API config

### Phase 4: Output Storage
**Goal**: User can choose a storage location and save the transcription + summary in .txt and .srt formats
**Depends on**: Phase 3
**Requirements**: STOR-01, STOR-02, STOR-03, STOR-04
**Success Criteria** (what must be TRUE):
  1. User can choose a save location via dialog
  2. User can save transcription to a .txt file
  3. User can save transcription to a .srt subtitle file
  4. Summary can be included in the saved output
**Plans**: 1 plan
**UI hint**: yes

Plans:
- [x] 04-01-PLAN.md — Save results in .txt and .srt formats with folder selection

### Phase 5: Packaging & Distribution
**Goal**: A user can install and run the app on another PC with all dependencies documented, and optionally build a standalone executable
**Depends on**: Phase 4
**Requirements**: DIST-01, DIST-02, DIST-03, DIST-04
**Success Criteria** (what must be TRUE):
  1. Required software/repositories are listed with sources
  2. The role of FFmpeg (and alternatives) is explained
  3. A step-by-step install and usage process is documented
  4. A standalone executable can be built with PyInstaller
**Plans**: 1 plan
**UI hint**: no

Plans:
- [ ] 05-01-PLAN.md — Dependency documentation + PyInstaller packaging

### Phase 6: Refactor main.py into echo package
**Goal**: Split the monolithic main.py (1467 lines) into an `echo/` package with an `echo/ui/` subpackage, preserving behavior exactly
**Depends on**: Phase 4 (code refactor; independent of packaging)
**Requirements**: REFR-01, REFR-02, REFR-03
**Success Criteria** (what must be TRUE):
  1. Application behavior is unchanged (same UI, same features, same queue contracts)
  2. main.py is a thin launcher; logic lives in echo/ modules (config, presets, errors, llm_client, srt, engines, ui)
  3. The existing root app_config.json (including the API key) is still found and loaded
**Plans**: 6 plans
**UI hint**: no

Plans:
- [x] 06-01-PLAN.md — Package skeleton + leaf modules (config with re-anchored CONFIG_PATH, presets, errors, srt)
- [x] 06-02-PLAN.md — LLM client + engines (llm_client, transcription_engine, summarization_engine)
- [x] 06-03-PLAN.md — UI foundation (ui/theme, ui/build, ui/settings_dialog)
- [ ] 06-04-PLAN.md — UI application window (ui/app: TranscriberApp)
- [ ] 06-05-PLAN.md — Thin launcher, delete app_config.py, end-to-end smoke
- [ ] 06-06-PLAN.md — Widget-construction parity proof + human visual verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. GUI & File Selection | 1/1 | Completed | 2026-09-03 |
| 2. Transcription Engine | 2/2 | Completed | 2026-09-03 |
| 3. Summarization | 1/1 | Completed | 2026-09-04 |
| 4. Output Storage | 1/1 | Completed | 2026-09-04 |
| 5. Packaging & Distribution | 0/1 | Not started | - |
| 6. Refactor main.py into echo package | 0/6 | Not started | - |
