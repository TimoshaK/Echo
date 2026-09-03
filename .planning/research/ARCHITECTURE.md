# Architecture Patterns

**Domain:** Desktop audio transcription application
**Researched:** 2026-09-03

## Recommended Architecture

```
┌─────────────────────────────────────────────┐
│              Main Window (tkinter)           │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐   │
│  │  File Selection Area                 │   │
│  │  [Browse Button] [Path Display]      │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Progress Area                       │   │
│  │  [Progress Bar] [Status Label]       │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Results Area                        │   │
│  │  [ScrolledText Widget]               │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Action Buttons                      │   │
│  │  [Transcribe] [Save TXT] [Save SRT]  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│           Transcription Engine               │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │  Whisper     │  │  Progress Queue     │   │
│  │  (model)     │  │  (thread-safe)      │   │
│  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│           Output Formatter                   │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │  TXT Writer  │  │  SRT Writer         │   │
│  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| GUI Layer | User interaction, display | Transcription Engine (via queue) |
| Transcription Engine | Whisper model, audio processing | GUI (via queue), Output Formatter |
| Output Formatter | File writing (txt/srt) | Filesystem |

### Data Flow

1. User selects file → GUI stores path
2. User clicks "Transcribe" → GUI starts background thread
3. Background thread loads model (if needed) → updates progress queue
4. Background thread transcribes audio → updates progress queue
5. Background thread puts result in queue → signals completion
6. GUI polls queue → updates progress bar / displays results
7. User clicks "Save" → Output Formatter writes file

## Patterns to Follow

### Pattern 1: Queue-Based Thread Communication
**What:** Use queue.Queue for thread-safe communication between background thread and GUI
**When:** Always when tkinter needs to update from background thread
**Example:**
```python
import queue
import threading
from tkinter import ttk

class TranscriptionWorker:
    def __init__(self, progress_queue):
        self.progress_queue = progress_queue
    
    def transcribe(self, audio_path):
        """Run in background thread"""
        try:
            self.progress_queue.put(("status", "Loading model..."))
            model = whisper.load_model("base")
            
            self.progress_queue.put(("status", "Transcribing..."))
            result = model.transcribe(audio_path)
            
            self.progress_queue.put(("done", result))
        except Exception as e:
            self.progress_queue.put(("error", str(e)))

class App:
    def __init__(self):
        self.root = ttk.Tk()
        self.progress_queue = queue.Queue()
        # ... GUI setup ...
    
    def start_transcription(self):
        worker = TranscriptionWorker(self.progress_queue)
        thread = threading.Thread(
            target=worker.transcribe,
            args=(self.audio_path,),
            daemon=True
        )
        thread.start()
        self.poll_queue()
    
    def poll_queue(self):
        """Run in main thread"""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()
                if msg_type == "status":
                    self.status_label.config(text=data)
                elif msg_type == "progress":
                    self.progress_bar["value"] = data
                elif msg_type == "done":
                    self.display_results(data)
                    return
                elif msg_type == "error":
                    messagebox.showerror("Error", data)
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)
```

### Pattern 2: Graceful Model Loading
**What:** Load whisper model once, reuse for multiple transcriptions
**When:** Application stays open for multiple files
**Example:**
```python
class TranscriptionEngine:
    def __init__(self):
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            self._model = whisper.load_model("base")
        return self._model
    
    def transcribe(self, audio_path):
        return self.model.transcribe(audio_path)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct GUI Updates from Thread
**What:** Calling tkinter widget methods from background thread
**Why bad:** tkinter is not thread-safe; causes crashes or undefined behavior
**Instead:** Use queue-based communication pattern above

### Anti-Pattern 2: Blocking Main Thread
**What:** Running transcription in main thread
**Why bad:** GUI freezes, no progress updates, poor user experience
**Instead:** Always use daemon threads for long operations

### Anti-Pattern 3: Model Reload on Each Transcription
**What:** Calling whisper.load_model() for every file
**Why bad:** Model loading takes 2-5 seconds; wasteful
**Instead:** Load once, reuse (Pattern 2 above)

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| Model loading | 2-5 sec once | 2-5 sec once | 2-5 sec once |
| Memory usage | ~1GB (model) | ~1GB (model) | ~1GB (model) |
| Transcription speed | Depends on audio length | Same | Same |
| File I/O | Negligible | Negligible | Negligible |

Note: Desktop app scales linearly; each instance is independent.

## Sources

- tkinter documentation (threading model): https://docs.python.org/3/library/tkinter.html
- whisper documentation (API): https://pypi.org/project/openai-whisper/
- Python threading documentation: https://docs.python.org/3/library/threading.html
