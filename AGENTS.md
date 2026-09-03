<!-- GSD:project-start source:PROJECT.md -->
## Project

**Whisper Transcriber**

Приложение с графическим интерфейсом для транскрипции аудиофайлов с помощью модели Whisper от OpenAI. Простой и удобный инструмент для преобразования аудио в текст.

**Core Value:** Быстрая и точная транскрипция аудиофайлов в удобном интерфейсе с сохранением результатов в читаемых форматах.

### Constraints

- **Tech stack**: Python, tkinter, whisper, torch
- **Platform**: Desktop (Windows/macOS/Linux)
- **Model**: Фиксированная модель base
- **Formats**: Только .txt и .srt
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.10+ | Runtime | Required by whisper and torch; 3.10 is minimum for torch 2.14.0; 3.12+ recommended for best performance |
| tkinter | stdlib | GUI framework | Built into Python, zero dependencies, sufficient for simple desktop app; no need for PyQt/PySide complexity |
### Transcription Engine
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openai-whisper | 20250625 | Speech-to-text model | Official OpenAI implementation; MIT license; automatic language detection; base model provides good speed/quality balance |
| torch | 2.14.0 | GPU acceleration | Whisper's backend for neural network inference; automatic CUDA detection; supports CPU fallback |
### Audio Processing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ffmpeg | system | Audio decoding | Required by whisper for audio file loading; supports all major formats (mp3, wav, m4a, flac, etc.) |
### Output Formatting
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| srt | 3.5.3 | SRT subtitle generation | Lightweight, 100% test coverage, handles broken SRT files, no dependencies |
| pathlib | stdlib | File path handling | Modern Python path manipulation, cross-platform compatible |
### Progress & UI Feedback
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| tqdm | 4.70.0 | Progress tracking | Has tkinter integration (`tqdm.tk`), thread-safe, minimal overhead |
### Development Dependencies
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pyinstaller | 6.x | App distribution | Creates standalone executable for distribution without Python installation |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| GUI | tkinter | PyQt6/PySide6 | Adds ~50MB+ dependency, GPL/commercial licensing, overkill for simple file picker + progress bar |
| GUI | tkinter | customtkinter | Wrapper around tkinter; adds dependency for minimal visual improvement; unnecessary for v1 |
| Transcription | whisper | faster-whisper | CTranslate2 backend; faster but adds complexity; whisper is simpler and officially supported |
| Transcription | whisper | whisper.cpp | C++ port; requires separate compilation; Python binding adds complexity |
| Audio | ffmpeg | pydub | Last updated 2021; wraps ffmpeg anyway; adds unnecessary abstraction layer |
| SRT | srt | pysrt | srt is ~30% faster, better test coverage, handles more edge cases |
| Progress | tqdm | rich | Heavier dependency; tqdm has native tkinter support via `tqdm.tk` |
## Architecture Notes
### Threading Model
# Pattern: Thread + Queue for GUI updates
### GPU Detection
## Installation
# Core dependencies
# Development
# System requirement (not pip)
# ffmpeg must be installed separately:
# Windows: choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
### Complete requirements.txt
## Platform Notes
| Platform | Notes |
|----------|-------|
| Windows | ffmpeg via `choco install ffmpeg` or `scoop install ffmpeg`; CUDA requires NVIDIA drivers |
| macOS | ffmpeg via `brew install ffmpeg`; Apple Silicon uses MPS backend automatically |
| Linux | ffmpeg via `sudo apt install ffmpeg`; CUDA requires NVIDIA drivers + cuDNN |
## What NOT to Use
| Don't Use | Why |
|-----------|-----|
| `whisper` CLI for production | Python API provides better control and error handling |
| `pydub` | Unmaintained (2021), wraps ffmpeg anyway |
| `pysrt` | Slower than `srt`, worse edge case handling |
| `customtkinter` | Adds dependency for cosmetic improvement; tkinter ttk is sufficient |
| `PyQt6/PySide6` | Massive dependency for simple UI; licensing complexity |
| `faster-whisper` for v1 | Adds CTranslate2 complexity; optimize later if needed |
## Sources
- PyPI: openai-whisper (verified: https://pypi.org/project/openai-whisper/)
- PyPI: torch (verified: https://pypi.org/project/torch/)
- PyPI: numpy (verified: https://pypi.org/project/numpy/)
- PyPI: tqdm (verified: https://pypi.org/project/tqdm/)
- PyPI: srt (verified: https://pypi.org/project/srt/)
- Python docs: tkinter (verified: https://docs.python.org/3/library/tkinter.html)
- Python docs: threading (verified: https://docs.python.org/3/library/threading.html)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
