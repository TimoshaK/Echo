"""Whisper transcription engine with lazy model loading."""

import queue
import threading

import whisper


class TranscriptionEngine:
    """Whisper transcription engine with lazy model loading."""

    def __init__(self) -> None:
        self.model = None
        self.model_lock = threading.Lock()
        self.progress_queue: queue.Queue = queue.Queue()

    def load_model(self) -> None:
        """Load whisper base model (lazy, thread-safe)."""
        with self.model_lock:
            if self.model is None:
                self.progress_queue.put({"type": "status", "text": "Загрузка модели..."})
                self.model = whisper.load_model("base")
                self.progress_queue.put({"type": "status", "text": "Модель загружена"})

    def transcribe(self, file_path: str) -> dict:
        """Transcribe audio file. Returns whisper result dict."""
        self.load_model()
        self.progress_queue.put({"type": "status", "text": "Выполняется транскрипция..."})
        result = self.model.transcribe(file_path, task="transcribe")
        self.progress_queue.put({"type": "status", "text": "Транскрипция завершена"})
        return result

    def start_transcription(self, file_path: str) -> None:
        """Start transcription in background thread."""
        thread = threading.Thread(
            target=self._run_transcription,
            args=(file_path,),
            daemon=True,
        )
        thread.start()

    def _run_transcription(self, file_path: str) -> None:
        """Background thread worker for transcription."""
        try:
            result = self.transcribe(file_path)
            self.progress_queue.put({
                "type": "complete",
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []) or [],
            })
        except Exception as e:
            self.progress_queue.put({
                "type": "error",
                "error": str(e),
            })
