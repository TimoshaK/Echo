"""Whisper Transcriber — GUI application for audio transcription."""

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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
            })
        except Exception as e:
            self.progress_queue.put({
                "type": "error",
                "error": str(e),
            })


class TranscriberApp:
    """Main application window for Whisper Transcriber."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whisper Transcriber")
        self.root.geometry("600x450")
        self.root.minsize(500, 350)

        self.selected_file: str | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the main window widgets."""
        # Row 0: Select File button + File path display
        self.select_btn = ttk.Button(
            self.root, text="Выбрать файл", command=self.select_file
        )
        self.select_btn.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        self.file_var = tk.StringVar(value="Файл не выбран")
        self.file_entry = ttk.Entry(
            self.root, textvariable=self.file_var, width=40
        )
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        self.file_entry.configure(state="readonly")

        # Row 1: Transcribe button + Status label
        self.transcribe_btn = ttk.Button(
            self.root, text="Транскрибировать", command=self.start_transcription,
            state="disabled"
        )
        self.transcribe_btn.grid(row=1, column=0, sticky="w", padx=8, pady=8)

        self.status_label = ttk.Label(
            self.root,
            text="Нажмите «Выбрать файл», чтобы выбрать аудиофайл для транскрипции",
            wraplength=560,
        )
        self.status_label.grid(row=1, column=1, sticky="w", padx=8, pady=8)

        # Row 2: Result text area + scrollbar
        result_frame = ttk.Frame(self.root)
        result_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=(8, 8))

        self.result_text = tk.Text(
            result_frame, wrap="word", state="disabled", height=15
        )
        self.result_scrollbar = ttk.Scrollbar(result_frame, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=self.result_scrollbar.set)

        self.result_text.pack(side="left", fill="both", expand=True)
        self.result_scrollbar.pack(side="right", fill="y")

        # Column and row weights
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

    def select_file(self) -> None:
        """Open file dialog and handle selection."""
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите аудиофайл",
                filetypes=[
                    ("Аудиофайлы", "*.mp3 *.wav *.m4a *.flac *.ogg *.webm"),
                    ("Все файлы", "*.*"),
                ],
                defaultextension=".mp3",
                initialdir=os.path.expanduser("~"),
            )
        except Exception:
            messagebox.showerror(
                "Ошибка",
                "Не удалось открыть файл. Проверьте формат файла и попробуйте снова.",
            )
            return

        if file_path:
            self.selected_file = file_path
            self.file_var.set(file_path)
            self.file_entry.configure(state="readonly")
            filename = os.path.basename(file_path)
            self.status_label.configure(text=f"Выбран: {filename}")
            self.transcribe_btn.configure(state="normal")

    def start_transcription(self) -> None:
        """Start transcription process."""
        pass  # Will be implemented in Task 2

    def poll_progress(self) -> None:
        """Poll progress queue for updates."""
        pass  # Will be implemented in Task 2


def main() -> None:
    root = tk.Tk()
    TranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
