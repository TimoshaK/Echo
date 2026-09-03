# Technology Stack

**Project:** Whisper Transcriber
**Researched:** 2026-09-03
**Overall Confidence:** HIGH

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
**Critical:** tkinter is single-threaded. Long-running operations (transcription) MUST run in separate threads.

```python
# Pattern: Thread + Queue for GUI updates
import threading
import queue

class TranscriberApp:
    def __init__(self):
        self.progress_queue = queue.Queue()
    
    def start_transcription(self, audio_path):
        """Called from GUI button click"""
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(audio_path,),
            daemon=True
        )
        thread.start()
        self._poll_progress()
    
    def _transcribe_worker(self, audio_path):
        """Runs in background thread"""
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        self.progress_queue.put(("done", result))
    
    def _poll_progress(self):
        """Runs in main thread, checks queue periodically"""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                if msg_type == "done":
                    self._display_results(data)
                    return
        except queue.Empty:
            pass
        # Re-schedule check (100ms interval)
        self.root.after(100, self._poll_progress)
```

### GPU Detection
```python
import torch

def get_device():
    """Auto-detect best available device"""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon
    return "cpu"
```

## Installation

```bash
# Core dependencies
pip install openai-whisper torch numpy tqdm srt

# Development
pip install pyinstaller

# System requirement (not pip)
# ffmpeg must be installed separately:
# Windows: choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

### Complete requirements.txt
```
openai-whisper>=20250625
torch>=2.14.0
numpy>=2.5.0
tqdm>=4.70.0
srt>=3.5.3
```

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
