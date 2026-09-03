# Domain Pitfalls

**Domain:** Desktop audio transcription application
**Researched:** 2026-09-03

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: tkinter Threading Violation
**What goes wrong:** Updating GUI widgets from background thread causes crash or freeze
**Why it happens:** tkinter is single-threaded; developers assume threading "just works"
**Consequences:** Application crash, TclError, undefined behavior
**Prevention:** Always use queue.Queue for thread→GUI communication; never call widget methods from threads
**Detection:** Random crashes during transcription, TclError in console

```python
# WRONG - will crash
def transcribe_worker():
    result = model.transcribe(audio_path)
    status_label.config(text="Done!")  # CRASH!

# RIGHT - use queue
def transcribe_worker():
    result = model.transcribe(audio_path)
    progress_queue.put(("done", result))
```

### Pitfall 2: Model Loading Blocks GUI
**What goes wrong:** First transcription takes 10+ seconds with no feedback
**Why it happens:** whisper.load_model() downloads model (~150MB for base) on first run
**Consequences:** User thinks app is frozen, force-quits
**Prevention:** Show "Loading model..." status before calling load_model(); consider pre-loading on startup
**Detection:** User complaints about "freezing" on first use

### Pitfall 3: Memory Leak with Large Files
**What goes wrong:** Transcribing 1+ hour audio files causes memory exhaustion
**Why it happens:** whisper loads entire audio into memory as tensor
**Consequences:** Application crash, system slowdown
**Prevention:** Warn user for files > 30 minutes; process in chunks if needed (whisper handles internally)
**Detection:** System becomes unresponsive during transcription

## Moderate Pitfalls

### Pitfall 1: ffmpeg Not Found
**What goes wrong:** whisper throws error when trying to load audio
**Why it happens:** ffmpeg is not installed or not in PATH
**Consequences:** Transcription fails immediately
**Prevention:** Check for ffmpeg on startup; show clear error message with installation instructions
**Detection:** FileNotFoundError or "ffmpeg not found" error

### Pitfall 2: Progress Bar Not Updating
**What goes wrong:** Progress bar stays at 0% during transcription
**Why it happens:** whisper doesn't provide granular progress callbacks; only segment-level progress
**Consequences:** User thinks app is frozen
**Prevention:** Use indeterminate progress bar (marquee style) during transcription; show segment count
**Detection:** Progress bar stuck, user confusion

### Pitfall 3: SRT Timestamp Formatting
**What goes wrong:** Generated SRT files have incorrect timestamps
**Why it happens:** Whisper returns timestamps in different formats than expected
**Consequences:** Subtitles out of sync with video
**Prevention:** Use srt library for formatting; validate output format
**Detection:** Subtitles appear at wrong times

## Minor Pitfalls

### Pitfall 1: File Path Encoding
**What goes wrong:** Paths with non-ASCII characters (Cyrillic, CJK) cause errors
**Why it happens:** Windows path handling with unicode
**Consequences:** Cannot select or save files with international characters
**Prevention:** Use pathlib.Path for all path operations; test with unicode paths
**Detection:** UnicodeDecodeError on file operations

### Pitfall 2: Output File Overwrite
**What goes wrong:** User accidentally overwrites existing transcription
**Why it happens:** No confirmation dialog before saving
**Consequences:** Data loss
**Prevention:** Check if file exists; show confirmation dialog
**Detection:** User complaint about lost work

### Pitfall 3: Progress Queue Memory
**What goes wrong:** Queue grows unbounded during long transcriptions
**Why it happens:** Many small progress updates accumulate
**Consequences:** Minor memory increase
**Prevention:** Use queue.Queue with maxsize; clear processed messages
**Detection:** Slow memory growth (minor issue)

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| GUI Setup | Threading model confusion | Establish queue pattern immediately |
| Whisper Integration | Model loading delay | Show loading status, consider pre-load |
| Progress Display | No granular progress | Use indeterminate mode, show segment count |
| File Output | SRT format errors | Use srt library, validate output |
| Error Handling | Missing ffmpeg error | Check on startup, clear error message |

## Testing Checklist

- [ ] Transcription works with mp3, wav, m4a, flac
- [ ] Progress updates during transcription (or indeterminate animation)
- [ ] GUI remains responsive during transcription
- [ ] Error messages are clear and actionable
- [ ] File paths with spaces work correctly
- [ ] File paths with unicode characters work (if supported)
- [ ] Large files (>30 min) don't crash the app
- [ ] Model loads successfully on first run
- [ ] SRT output is valid and parseable
- [ ] TXT output contains full transcription

## Sources

- tkinter threading model: https://docs.python.org/3/library/tkinter.html#threading-model
- whisper limitations: https://github.com/openai/whisper#available-models-and-languages
- Python GIL documentation: https://docs.python.org/3/library/threading.html#gil-and-performance-considerations
