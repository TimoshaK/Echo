# Project Research Summary

**Project:** Echo (Whisper Transcriber)
**Domain:** Desktop audio transcription application
**Researched:** 2026-09-03
**Confidence:** HIGH

## Executive Summary

Echo is a desktop application that transcribes audio files to text using OpenAI's Whisper model. It's a single-purpose utility tool — users select an audio file, click transcribe, and get text output (plus optional SRT subtitles). The experts in this domain build these apps with Python + tkinter for simplicity, threading for non-blocking UI, and queue-based communication between background workers and the GUI. This is a well-understood problem space with established patterns.

The recommended approach is straightforward: Python 3.10+ with tkinter for GUI, openai-whisper for transcription, and the srt library for subtitle generation. The key architectural insight is that tkinter is single-threaded — transcription MUST run in a background thread with results communicated via queue.Queue. This is the #1 pitfall in the domain and will cause crashes if violated. The app should use lazy model loading with progress feedback, and auto-detect GPU/CPU for optimal performance.

The main risks are: (1) tkinter threading violations causing crashes, (2) model loading delays on first use making users think the app is frozen, and (3) ffmpeg dependency management across platforms. All three are mitigatable with established patterns. The project has high confidence across all research areas — the technology choices are obvious (whisper + tkinter), the features are well-defined by the project requirements, the architecture follows standard desktop app patterns, and the pitfalls are well-documented.

## Key Findings

### Recommended Stack

The stack is minimal and purpose-built. Python 3.10+ provides the runtime, tkinter handles the GUI with zero dependencies, openai-whisper does the transcription, and the srt library generates subtitles. System-level ffmpeg is required for audio decoding. Development uses PyInstaller for distribution.

**Core technologies:**
- **openai-whisper** (20250625): Speech-to-text engine — official implementation, MIT license, automatic language detection, base model balances speed/quality
- **torch** (2.14.0): Neural network backend — automatic CUDA/MPS/CPU detection
- **tkinter** (stdlib): GUI framework — zero dependencies, sufficient for file picker + progress bar + text display
- **srt** (3.5.3): Subtitle generation — lightweight, 100% test coverage, handles broken SRT files
- **tqdm** (4.70.0): Progress tracking — has tkinter integration via tqdm.tk
- **ffmpeg** (system): Audio decoding — supports all major formats

**What NOT to use:** PyQt/PySide (massive dependency, licensing), customtkinter (unnecessary wrapper), faster-whisper (adds complexity for v1), pydub (unmaintained), pysrt (slower than srt library).

### Expected Features

**Must have (table stakes):**
- File selection dialog — users need to pick audio files
- Supported format display — show what formats work (mp3, wav, m4a, flac, ogg, webm)
- Transcription trigger — one-click to start
- Progress indicator — feedback during processing (tqdm.tk)
- Results display — show transcription text (ScrolledText widget)
- Error messages — clear feedback on failures
- File save dialog — save results to file

**Should have (competitive):**
- SRT subtitle format — video editors need timed subtitles
- Automatic language detection — whisper's detect_language()
- GPU auto-detection — faster transcription when available
- Path display in UI — visual confirmation of selected file

**Defer (v2+):**
- Language selection UI (auto-detection works well)
- Translation to English (out of scope)
- Model selection UI (hardcode "base" model)
- Multi-file batch processing (adds complexity)
- Real-time transcription (complex, not required)
- Audio recording (out of scope — file-based input only)

### Architecture Approach

Three-layer architecture: GUI Layer (tkinter) → Transcription Engine (whisper) → Output Formatter (txt/srt writers). Communication between GUI and background thread uses queue.Queue — this is the critical pattern that prevents crashes. The TranscriptionEngine class loads the whisper model lazily and reuses it across transcriptions (model loading takes 2-5 seconds, wasteful to reload). Progress updates flow from background thread → queue → GUI poll loop (100ms interval).

**Major components:**
1. **GUI Layer** — File selection, progress display, results display, action buttons
2. **Transcription Engine** — Whisper model wrapper with lazy loading and progress queue
3. **Output Formatter** — TXT and SRT file writers using srt library

### Critical Pitfalls

1. **tkinter Threading Violation** — Updating GUI from background thread causes crash/TclError. Prevention: Always use queue.Queue for thread→GUI communication; never call widget methods from threads.

2. **Model Loading Blocks GUI** — First transcription takes 10+ seconds with no feedback. Prevention: Show "Loading model..." status before load_model(); consider pre-loading on startup.

3. **Memory Leak with Large Files** — Transcribing 1+ hour files causes memory exhaustion. Prevention: Warn user for files > 30 minutes; whisper handles chunking internally.

4. **ffmpeg Not Found** — whisper throws error when audio can't be decoded. Prevention: Check for ffmpeg on startup; show clear error with installation instructions.

5. **Progress Bar Not Updating** — whisper doesn't provide granular progress callbacks. Prevention: Use indeterminate progress bar (marquee style); show segment count instead of percentage.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation & Core Transcription
**Rationale:** Must establish the threading pattern and basic transcription before anything else. The queue-based communication pattern is architecturally foundational — build it first.
**Delivers:** Working transcription app — select file, see progress, view results
**Addresses:** File selection, transcription trigger, progress indicator, results display, error messages
**Avoids:** tkinter threading violations (establish queue pattern immediately), model loading delay (show loading status)

### Phase 2: Output & Polish
**Rationale:** Once core transcription works, add output formats and polish the UX. SRT export can be layered on top without changing architecture.
**Delivers:** TXT save, SRT subtitle export, file path display, format display, overwrite confirmation
**Uses:** srt library, pathlib for file operations
**Implements:** Output Formatter component

### Phase 3: Platform & Distribution
**Rationale:** Get the app working on target platforms and create distributable builds. PyInstaller packaging, ffmpeg dependency checks, cross-platform testing.
**Delivers:** Standalone executables, platform-specific ffmpeg checks, memory warnings for large files
**Uses:** PyInstaller, platform detection

### Phase Ordering Rationale

- Phase 1 comes first because the threading pattern is architecturally foundational — everything else depends on it
- Phase 2 adds features on top of a working transcription pipeline — SRT export, save dialogs, and polish don't change the architecture
- Phase 3 is last because distribution/packaging can't be validated until the app works end-to-end
- This order avoids pitfalls by establishing the queue pattern first (preventing threading crashes), then handling edge cases (large files, SRT format), then cross-platform concerns

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 1:** Minimal — tkinter threading patterns and whisper API are well-documented
- **Phase 2:** SRT timestamp handling — need to verify whisper timestamp format vs srt library expectations
- **Phase 3:** PyInstaller packaging — whisper + torch bundling can be tricky; may need hidden imports configuration

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Queue-based threading is a standard tkinter pattern with extensive documentation
- **Phase 2:** File dialogs and save operations are well-established tkinter patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified on PyPI; official documentation checked; versions confirmed |
| Features | HIGH | Requirements clearly defined in PROJECT.md; feature set is standard for this app type |
| Architecture | HIGH | Threading patterns well-documented; component structure follows standard desktop app patterns |
| Pitfalls | HIGH | All pitfalls documented in official tkinter/whisper docs; community consensus on prevention |

**Overall confidence:** HIGH

### Gaps to Address

- **ffmpeg detection on startup:** Need to determine exact approach (shutil.which vs subprocess) — minor implementation detail
- **PyInstaller hidden imports:** torch + whisper bundling may require testing; common issue with ML libraries
- **SRT timestamp validation:** Need to test whisper output format against srt library expectations during implementation
- **Large file memory limits:** Need to determine exact threshold (30 min?) and warning UX during testing

## Sources

### Primary (HIGH confidence)
- PyPI: openai-whisper — https://pypi.org/project/openai-whisper/
- PyPI: torch — https://pypi.org/project/torch/
- PyPI: srt — https://pypi.org/project/srt/
- PyPI: tqdm — https://pypi.org/project/tqdm/
- Python docs: tkinter — https://docs.python.org/3/library/tkinter.html
- Python docs: threading — https://docs.python.org/3/library/threading.html
- tkinter threading model — https://docs.python.org/3/library/tkinter.html#threading-model
- whisper documentation — https://github.com/openai/whisper

### Secondary (MEDIUM confidence)
- PROJECT.md requirements — validated against user needs
- Community patterns for tkinter + threading — multiple Stack Overflow answers agree

### Tertiary (LOW confidence)
- PyInstaller + torch bundling — community reports vary; needs testing
- Large file memory behavior — theoretical; needs real-world validation

---
*Research completed: 2026-09-03*
*Ready for roadmap: yes*
