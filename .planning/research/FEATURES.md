# Feature Landscape

**Domain:** Desktop audio transcription application
**Researched:** 2026-09-03

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| File selection dialog | Users need to pick audio files | Low | Use tkinter.filedialog.askopenfilename |
| Supported format display | Users need to know what works | Low | whisper supports: mp3, wav, m4a, flac, ogg, webm |
| Transcription trigger | One-click to start process | Low | Simple button with command callback |
| Progress indicator | Users need feedback during processing | Medium | tqdm.tk provides tkinter-native progress bar |
| Results display | Users need to see transcription text | Low | tkinter.scrolledtext or Text widget |
| Error messages | Users need to know what went wrong | Low | tkinter.messagebox for errors |
| File save dialog | Users need to save results | Low | Use tkinter.filedialog.asksaveasfilename |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| SRT subtitle format | Video editors need timed subtitles | Medium | Use srt library for generation |
| Automatic language detection | No manual language selection needed | Low | Whisper's detect_language() method |
| GPU auto-detection | Faster transcription when available | Low | torch.cuda.is_available() check |
| Path display in UI | Visual confirmation of selected file | Low | Label widget with StringVar |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Language selection UI | Auto-detection works well for v1 | Use whisper's detect_language() |
| Translation to English | Out of scope per PROJECT.md | Focus on transcription only |
| Model selection UI | Fixed model "base" per requirements | Hardcode model choice |
| VTT/JSON export | Not needed per PROJECT.md | Only .txt and .srt |
| Real-time transcription | Complex, not required | Batch processing only |
| Multi-file batch processing | Adds complexity for v1 | Single file at a time |
| Audio recording | Out of scope | Only file-based input |
| Editing transcription | Not required | Display-only results |

## Feature Dependencies

```
File Selection → Transcription → Results Display
                                  ↓
                            File Save (txt/srt)

Progress Display → Transcription (parallel)
GPU Detection → Transcription (before)
Error Handling → All operations (cross-cutting)
```

## MVP Recommendation

Prioritize:
1. File selection dialog (required for any input)
2. Transcription with progress indicator (core value)
3. Results display in text area (user needs to see output)

Defer: SRT export - implement after basic transcription works; can be added in phase 3

## Sources

- PROJECT.md requirements (validated against user needs)
- Whisper documentation (API capabilities)
- tkinter documentation (available widgets)
