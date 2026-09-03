"""Whisper Transcriber — GUI application for audio transcription."""

import tkinter as tk
from tkinter import ttk


class TranscriberApp:
    """Main application window for Whisper Transcriber."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whisper Transcriber")
        self.root.geometry("500x200")
        self.root.minsize(400, 150)


def main() -> None:
    root = tk.Tk()
    app = TranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
