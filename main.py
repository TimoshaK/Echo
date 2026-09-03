"""Whisper Transcriber — GUI application for audio transcription."""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import whisper


class TranscriptionEngine:
    """Whisper transcription engine with lazy model loading."""

    def __init__(self) -> None:
        self.model = None
        self.model_lock = threading.Lock()

    def load_model(self) -> None:
        """Load whisper base model (lazy, thread-safe)."""
        with self.model_lock:
            if self.model is None:
                self.model = whisper.load_model("base")

    def transcribe(self, file_path: str) -> dict:
        """Transcribe audio file. Returns whisper result dict."""
        self.load_model()
        return self.model.transcribe(file_path, task="transcribe")


class TranscriberApp:
    """Main application window for Whisper Transcriber."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whisper Transcriber")
        self.root.geometry("500x200")
        self.root.minsize(400, 150)

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

        # Row 1: Status label
        self.status_label = ttk.Label(
            self.root,
            text="Нажмите «Выбрать файл», чтобы выбрать аудиофайл для транскрипции",
            wraplength=460,
        )
        self.status_label.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8)
        )

        # Column 1 expands when window is resized
        self.root.grid_columnconfigure(1, weight=1)

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


def main() -> None:
    root = tk.Tk()
    TranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
