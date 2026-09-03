# Roadmap: Whisper Transcriber

## Overview

A focused two-phase build that delivers a complete desktop transcription tool. Phase 1 establishes the GUI and file selection workflow. Phase 2 integrates Whisper for transcription, result display, and error handling. The result is a working app where users pick an audio file, click one button, and get their transcription text.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: GUI & File Selection** - Project setup, tkinter interface, and audio file selection dialog
- [ ] **Phase 2: Transcription Engine** - Whisper integration, transcription execution, result display, and error handling

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
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. GUI & File Selection | 0/1 | Not started | - |
| 2. Transcription Engine | 0/TBD | Not started | - |
