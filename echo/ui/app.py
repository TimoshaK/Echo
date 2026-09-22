"""Echo main application window: state, event handlers and polling loops."""

import os
import queue
import tkinter as tk
from tkinter import filedialog, messagebox

from echo.errors import map_transcription_error, sanitize_error_detail
from echo.presets import DEFAULT_PRESET, SUMMARY_PRESETS
from echo.srt import build_srt_content
from echo.summarization_engine import SummarizationEngine
from echo.transcription_engine import TranscriptionEngine
from echo.ui import build as ui_build
from echo.ui import settings_dialog
from echo.ui import theme


class TranscriberApp:
    """Main application window for Whisper Transcription."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        # Industrial UI colours — palette lives in echo/ui/theme.py
        self.bg_color = theme.COLORS["bg"]
        self.panel_color = theme.COLORS["panel"]
        self.panel_dark = theme.COLORS["panel_dark"]
        self.accent_color = theme.COLORS["accent"]
        self.accent_dark = theme.COLORS["accent_dark"]
        self.text_color = theme.COLORS["text"]
        self.muted_color = theme.COLORS["muted"]
        self.success_color = theme.COLORS["success"]
        self.error_color = theme.COLORS["error"]

        self.root.title("Echo // Audio Processing Unit")
        self.root.geometry("900x650")
        self.root.minsize(750, 550)
        self.root.configure(bg=self.bg_color)

        self.selected_file: str | None = None
        self.engine = TranscriptionEngine()
        self.summarizer = SummarizationEngine()
        # SEC-04: если конфиг повреждён, показываем явное сообщение после того,
        # как окно построено (messagebox до построения UI блокирует старт).
        if self.summarizer.config_error:
            self.root.after(200, self._show_config_error)
        self.last_transcript = ""
        self.last_segments: list = []
        self.last_summary = ""

        ui_build.build_ui(self)

    def on_preset_change(self, event=None) -> None:
        """Сохранить выбранный пресет; без сетевых вызовов и перезапуска."""
        label = self.preset_var.get()
        preset_id = self.preset_labels.get(label, DEFAULT_PRESET)
        self.summarizer.set_preset(preset_id)
        self.status_label.configure(
            text=f"PRESET // {SUMMARY_PRESETS[preset_id]['title']}"
        )

    def _base_name(self) -> str:
        if not self.selected_file:
            return "transcript"
        return os.path.splitext(os.path.basename(self.selected_file))[0]

    def save_transcription_txt(self) -> None:
        """Save transcription (and optional summary) to a .txt file."""
        if not self.last_transcript:
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить как .txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=f"{self._base_name()}_transcription.txt",
        )
        if not path:
            return

        content = self.last_transcript
        if self.last_summary:
            content += f"\n\n{'='*40}\nКОНСПЕКТ\n{'='*40}\n\n{self.last_summary}"

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
        except OSError as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл.\n\n{e}")
            return

        messagebox.showinfo("Сохранено", f"Файл сохранён:\n{path}")

    def save_transcription_srt(self) -> None:
        """Save transcription as .srt subtitles with timestamps."""
        if not self.last_segments:
            messagebox.showinfo(
                "Нет данных",
                "Сначала выполните транскрипцию, чтобы сохранить субтитры.",
            )
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить как .srt",
            defaultextension=".srt",
            filetypes=[("Subtitle files", "*.srt")],
            initialfile=f"{self._base_name()}.srt",
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(build_srt_content(self.last_segments))
        except OSError as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл.\n\n{e}")
            return

        messagebox.showinfo("Сохранено", f"Файл сохранён:\n{path}")

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
            self.status_indicator.configure(
                text="● FILE READY",
                fg=self.success_color,
            )
            self.status_label.configure(
                text=f"INPUT ACCEPTED // {filename}"
            )
            self.transcribe_btn.configure(state="normal")

    def start_transcription(self) -> None:
        """Start transcription process."""
        if not self.selected_file:
            return

        # Disable button during processing
        self.transcribe_btn.configure(state="disabled")
        self.status_indicator.configure(
            text="● PROCESSING",
            fg=self.accent_color,
        )
        self.status_label.configure(
            text="WHISPER ENGINE // PROCESSING AUDIO..."
        )

        # Clear previous results
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.configure(state="disabled")

        # Start transcription in background thread
        self.engine.start_transcription(self.selected_file)

        # Start polling for progress
        self.poll_progress()

    def poll_progress(self) -> None:
        """Poll progress queue for updates."""
        try:
            while True:
                message = self.engine.progress_queue.get_nowait()

                if message["type"] == "status":
                    self.status_label.configure(text=message["text"])

                elif message["type"] == "complete":
                    self._handle_transcription_complete(message)
                    return

                elif message["type"] == "error":
                    self._handle_transcription_error(message["error"])
                    return

        except queue.Empty:
            # No messages yet, poll again after 100ms
            self.root.after(100, self.poll_progress)

    def _handle_transcription_complete(self, message: dict) -> None:
        """Handle successful transcription completion."""

        language = message.get("language", "unknown")

        self.status_indicator.configure(
            text="● COMPLETE",
            fg=self.success_color,
        )

        self.status_label.configure(
            text="PROCESSING COMPLETE"
        )

        self.language_label.configure(
            text=f"LANGUAGE: {language.upper()}"
        )

        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", message["text"])
        self.result_text.configure(state="disabled")

        self.last_transcript = message["text"]
        self.last_segments = message.get("segments", []) or []
        self.summary_btn.configure(state="normal")
        self.save_txt_btn.configure(state="normal")
        self.save_srt_btn.configure(state="normal")

        self.transcribe_btn.configure(state="normal")

    def _handle_summary_complete(self, message: dict) -> None:
        """Handle successful summary generation."""

        self.status_indicator.configure(
            text="● SUMMARY READY",
            fg=self.success_color,
        )
        self.status_label.configure(
            text="CONSPECT GENERATED"
        )
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", message["text"])
        self.result_text.configure(state="disabled")
        self.last_summary = message["text"]
        self.summary_btn.configure(state="normal")

    def _show_config_error(self) -> None:
        """Показать явное сообщение о повреждённом конфиге (SEC-04).

        Молчаливый откат к дефолтам скрывал от пользователя потерю ключа;
        теперь причина видна, а транскрибация продолжает работать.
        """
        messagebox.showerror(
            "Повреждённый конфиг",
            "Не удалось прочитать app_config.json.\n\n"
            f"{self.summarizer.config_error}\n\n"
            "Настройки LLM сброшены на значения по умолчанию. Транскрибация "
            "работает; конспект нужно настроить заново в API SETTINGS.",
        )

    def _handle_summary_error(self, error: str) -> None:
        """Handle summary generation error."""

        self.status_indicator.configure(
            text="● ERROR",
            fg=self.error_color,
        )
        self.status_label.configure(
            text="SUMMARY FAILED"
        )
        self.summary_btn.configure(state="normal")

        # SEC-05: второй барьер перед показом. Ключ передаём явно, а не полагаемся
        # только на шаблоны: так вырезается точное значение из конфига.
        llm = self.summarizer.config.get("llm") if isinstance(self.summarizer.config, dict) else None
        api_key = llm.get("api_key", "") if isinstance(llm, dict) else ""
        safe_error = sanitize_error_detail(error, secrets=(api_key,), limit=500)

        messagebox.showerror(
            "Ошибка конспекта",
            f"Не удалось сгенерировать конспект.\n\n{safe_error or 'нет деталей'}",
        )

    def generate_summary(self) -> None:
        """Generate a summary of the last transcript."""
        if not self.last_transcript:
            return

        self.summary_btn.configure(state="disabled")
        self.status_indicator.configure(
            text="● SUMMARIZING",
            fg=self.accent_color,
        )
        self.status_label.configure(
            text="GENERATING CONSPECT..."
        )
        self.summarizer.start_summary(self.last_transcript)
        self.poll_summary()

    def poll_summary(self) -> None:
        """Poll the summarizer's progress queue for updates."""
        try:
            while True:
                message = self.summarizer.progress_queue.get_nowait()

                if message["type"] == "summary_status":
                    self.status_label.configure(text=message["text"])

                elif message["type"] == "summary_complete":
                    self._handle_summary_complete(message)
                    return

                elif message["type"] == "summary_error":
                    self._handle_summary_error(message["error"])
                    return

        except queue.Empty:
            self.root.after(100, self.poll_summary)

    def open_settings(self) -> None:
        """Open the LLM API settings dialog."""
        settings_dialog.open_settings(self)

    def _handle_transcription_error(self, error: str) -> None:
        """Handle transcription error with appropriate message."""

        self.status_indicator.configure(
            text="● ERROR",
            fg=self.error_color,
        )

        error_msg = map_transcription_error(error)

        # Update status label with error message
        self.status_label.configure(
            text="PROCESSING FAILED"
        )

        # Show messagebox with details
        messagebox.showerror(
            "Ошибка транскрипции",
            f"Не удалось выполнить транскрипцию.\n\n{error_msg}\n\nДетали: {error}"
        )

        # Re-enable transcribe button
        self.transcribe_btn.configure(state="normal")
