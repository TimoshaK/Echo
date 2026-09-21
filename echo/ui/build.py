"""Widget construction for the Echo main window.

Every function receives the application instance as `app` and mutates it in place.
This module must NOT import the app module — that would create an import cycle;
the dependency only ever runs app → build.
"""

import tkinter as tk
from tkinter import ttk

from echo.presets import SUMMARY_PRESETS


def build_ui(app) -> None:
    """Construct the industrial-style main window."""

    app.root.grid_columnconfigure(0, weight=1)
    app.root.grid_rowconfigure(3, weight=1)

    build_header(app)
    build_input_panel(app)
    build_processing_panel(app)
    build_output_panel(app)
    build_save_buttons(app)
    build_footer(app)


def build_header(app) -> None:
    header = tk.Frame(
        app.root,
        bg=app.panel_dark,
        height=70,
    )
    header.grid(
        row=0,
        column=0,
        sticky="ew",
        padx=12,
        pady=(12, 6),
    )
    header.grid_propagate(False)

    title_frame = tk.Frame(
        header,
        bg=app.panel_dark,
    )
    title_frame.pack(side="left", padx=18, pady=10)

    tk.Label(
        title_frame,
        text="ECHO",
        font=("Segoe UI", 22, "bold"),
        fg=app.accent_color,
        bg=app.panel_dark,
    ).pack(anchor="w")

    tk.Label(
        title_frame,
        text="AUDIO PROCESSING UNIT",
        font=("Consolas", 9),
        fg=app.muted_color,
        bg=app.panel_dark,
    ).pack(anchor="w")

    tk.Label(
        header,
        text="FICSIT // LOCAL TERMINAL",
        font=("Consolas", 9, "bold"),
        fg=app.text_color,
        bg=app.panel_dark,
    ).pack(side="right", padx=18)


def build_input_panel(app) -> None:
    input_panel = tk.Frame(
        app.root,
        bg=app.panel_color,
        highlightbackground=app.accent_dark,
        highlightthickness=1,
    )
    input_panel.grid(
        row=1,
        column=0,
        sticky="ew",
        padx=12,
        pady=6,
    )

    input_panel.grid_columnconfigure(1, weight=1)

    tk.Label(
        input_panel,
        text="AUDIO INPUT",
        font=("Consolas", 10, "bold"),
        fg=app.accent_color,
        bg=app.panel_color,
    ).grid(
        row=0,
        column=0,
        columnspan=2,
        sticky="w",
        padx=14,
        pady=(10, 6),
    )

    app.select_btn = tk.Button(
        input_panel,
        text="SELECT FILE",
        command=app.select_file,
        font=("Consolas", 10, "bold"),
        fg="#111111",
        bg=app.accent_color,
        activebackground=app.accent_dark,
        activeforeground="#111111",
        relief="flat",
        bd=0,
        padx=18,
        pady=7,
        cursor="hand2",
    )
    app.select_btn.grid(
        row=1,
        column=0,
        padx=(14, 8),
        pady=(0, 12),
    )

    app.file_var = tk.StringVar(value="NO FILE SELECTED")

    app.file_entry = tk.Entry(
        input_panel,
        textvariable=app.file_var,
        font=("Consolas", 10),
        fg=app.text_color,
        bg=app.panel_dark,
        insertbackground=app.text_color,
        relief="flat",
        bd=0,
    )
    app.file_entry.grid(
        row=1,
        column=1,
        sticky="ew",
        padx=(0, 14),
        pady=(0, 12),
        ipady=7,
    )
    app.file_entry.configure(state="readonly")


def build_processing_panel(app) -> None:
    processing_panel = tk.Frame(
        app.root,
        bg=app.bg_color,
    )
    processing_panel.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=12,
        pady=6,
    )

    processing_panel.grid_columnconfigure(0, weight=1)
    processing_panel.grid_columnconfigure(1, weight=1)

    # Transcription unit

    unit_panel = tk.Frame(
        processing_panel,
        bg=app.panel_color,
        highlightbackground=app.accent_dark,
        highlightthickness=1,
    )
    unit_panel.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=(0, 6),
    )

    tk.Label(
        unit_panel,
        text="TRANSCRIPTION UNIT",
        font=("Consolas", 10, "bold"),
        fg=app.accent_color,
        bg=app.panel_color,
    ).pack(anchor="w", padx=14, pady=(10, 4))

    tk.Label(
        unit_panel,
        text="WHISPER ENGINE // BASE MODEL",
        font=("Consolas", 8),
        fg=app.muted_color,
        bg=app.panel_color,
    ).pack(anchor="w", padx=14)

    app.transcribe_btn = tk.Button(
        unit_panel,
        text="START TRANSCRIPTION",
        command=app.start_transcription,
        state="disabled",
        font=("Consolas", 11, "bold"),
        fg="#111111",
        bg=app.accent_color,
        activebackground=app.accent_dark,
        activeforeground="#111111",
        disabledforeground="#666666",
        relief="flat",
        bd=0,
        padx=20,
        pady=9,
        cursor="hand2",
    )
    app.transcribe_btn.pack(
        anchor="w",
        padx=14,
        pady=(10, 12),
    )

    # System status

    status_panel = tk.Frame(
        processing_panel,
        bg=app.panel_color,
        highlightbackground=app.accent_dark,
        highlightthickness=1,
    )
    status_panel.grid(
        row=0,
        column=1,
        sticky="nsew",
        padx=(6, 0),
    )

    tk.Label(
        status_panel,
        text="SYSTEM STATUS",
        font=("Consolas", 10, "bold"),
        fg=app.accent_color,
        bg=app.panel_color,
    ).pack(anchor="w", padx=14, pady=(10, 4))

    app.status_indicator = tk.Label(
        status_panel,
        text="● READY",
        font=("Consolas", 11, "bold"),
        fg=app.success_color,
        bg=app.panel_color,
    )
    app.status_indicator.pack(
        anchor="w",
        padx=14,
        pady=(3, 0),
    )

    app.status_label = tk.Label(
        status_panel,
        text="Select an audio file to begin",
        font=("Consolas", 8),
        fg=app.muted_color,
        bg=app.panel_color,
        anchor="w",
    )
    app.status_label.pack(
        fill="x",
        padx=14,
        pady=(3, 10),
    )

    app.settings_btn = tk.Button(
        status_panel,
        text="API SETTINGS",
        command=app.open_settings,
        font=("Consolas", 9, "bold"),
        fg=app.text_color,
        bg=app.panel_dark,
        activebackground=app.accent_dark,
        activeforeground="#111111",
        relief="flat",
        bd=0,
        padx=14,
        pady=6,
        cursor="hand2",
    )
    app.settings_btn.pack(
        anchor="w",
        padx=14,
        pady=(0, 6),
    )

    # Summary preset selector

    app.preset_labels = {
        preset["label"]: preset_id
        for preset_id, preset in SUMMARY_PRESETS.items()
    }

    tk.Label(
        status_panel,
        text="SUMMARY PRESET",
        font=("Consolas", 8, "bold"),
        fg=app.muted_color,
        bg=app.panel_color,
    ).pack(anchor="w", padx=14, pady=(0, 2))

    configure_combobox_style(app)

    app.preset_var = tk.StringVar(
        value=SUMMARY_PRESETS[app.summarizer.preset]["label"]
    )
    app.preset_combo = ttk.Combobox(
        status_panel,
        textvariable=app.preset_var,
        values=list(app.preset_labels.keys()),
        state="readonly",
        width=24,
        style="Echo.TCombobox",
        font=("Consolas", 9),
    )
    app.preset_combo.pack(anchor="w", padx=14, pady=(0, 10))
    app.preset_combo.bind("<<ComboboxSelected>>", app.on_preset_change)

    app.summary_btn = tk.Button(
        status_panel,
        text="GENERATE SUMMARY",
        command=app.generate_summary,
        state="disabled",
        font=("Consolas", 10, "bold"),
        fg="#111111",
        bg=app.accent_color,
        activebackground=app.accent_dark,
        activeforeground="#111111",
        disabledforeground="#666666",
        relief="flat",
        bd=0,
        padx=18,
        pady=8,
        cursor="hand2",
    )
    app.summary_btn.pack(
        anchor="w",
        padx=14,
        pady=(0, 12),
    )


def build_output_panel(app) -> None:
    output_panel = tk.Frame(
        app.root,
        bg=app.panel_color,
        highlightbackground=app.accent_dark,
        highlightthickness=1,
    )
    output_panel.grid(
        row=3,
        column=0,
        sticky="nsew",
        padx=12,
        pady=6,
    )

    output_panel.grid_columnconfigure(0, weight=1)
    output_panel.grid_rowconfigure(1, weight=1)

    tk.Label(
        output_panel,
        text="TRANSCRIPTION OUTPUT",
        font=("Consolas", 10, "bold"),
        fg=app.accent_color,
        bg=app.panel_color,
    ).grid(
        row=0,
        column=0,
        sticky="w",
        padx=14,
        pady=(10, 6),
    )

    text_frame = tk.Frame(
        output_panel,
        bg=app.panel_dark,
    )
    text_frame.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=14,
        pady=(0, 14),
    )

    text_frame.grid_columnconfigure(0, weight=1)
    text_frame.grid_rowconfigure(0, weight=1)

    app.result_text = tk.Text(
        text_frame,
        wrap="word",
        state="disabled",
        font=("Consolas", 10),
        fg=app.text_color,
        bg=app.panel_dark,
        insertbackground=app.accent_color,
        selectbackground=app.accent_dark,
        selectforeground="#111111",
        relief="flat",
        bd=0,
        padx=12,
        pady=12,
    )

    app.result_text.grid(
        row=0,
        column=0,
        sticky="nsew",
    )

    app.result_scrollbar = tk.Scrollbar(
        text_frame,
        command=app.result_text.yview,
        bg=app.panel_color,
        troughcolor=app.panel_dark,
        activebackground=app.accent_color,
        relief="flat",
        bd=0,
    )

    app.result_scrollbar.grid(
        row=0,
        column=1,
        sticky="ns",
    )

    app.result_text.configure(
        yscrollcommand=app.result_scrollbar.set
    )


def build_save_buttons(app) -> None:
    """Build the output save buttons row."""
    save_frame = tk.Frame(app.root, bg=app.bg_color)
    save_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 6))

    btn_style = {
        "font": ("Consolas", 9, "bold"),
        "fg": app.text_color,
        "bg": app.panel_color,
        "activebackground": app.accent_dark,
        "activeforeground": "#111111",
        "disabledforeground": "#666666",
        "relief": "flat",
        "bd": 0,
        "padx": 14,
        "pady": 6,
        "cursor": "hand2",
    }

    app.save_txt_btn = tk.Button(
        save_frame,
        text="SAVE .TXT",
        command=app.save_transcription_txt,
        state="disabled",
        **btn_style,
    )
    app.save_txt_btn.pack(side="left", padx=(0, 8))

    app.save_srt_btn = tk.Button(
        save_frame,
        text="SAVE .SRT",
        command=app.save_transcription_srt,
        state="disabled",
        **btn_style,
    )
    app.save_srt_btn.pack(side="left")


def build_footer(app) -> None:
    footer = tk.Frame(
        app.root,
        bg=app.panel_dark,
        height=32,
    )
    footer.grid(
        row=4,
        column=0,
        sticky="ew",
        padx=12,
        pady=(6, 12),
    )
    footer.grid_propagate(False)

    app.language_label = tk.Label(
        footer,
        text="LANGUAGE: --",
        font=("Consolas", 8, "bold"),
        fg=app.muted_color,
        bg=app.panel_dark,
    )
    app.language_label.pack(
        side="left",
        padx=14,
    )

    tk.Label(
        footer,
        text="ECHO // FICSIT AUDIO UNIT // ONLINE",
        font=("Consolas", 8),
        fg=app.muted_color,
        bg=app.panel_dark,
    ).pack(
        side="right",
        padx=14,
    )


def configure_combobox_style(app) -> None:
    """Тёмная палитра для ttk.Combobox; сбой темы не должен ломать UI."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Echo.TCombobox",
        fieldbackground=app.panel_dark,
        background=app.panel_dark,
        foreground=app.text_color,
        arrowcolor=app.accent_color,
    )
    style.map(
        "Echo.TCombobox",
        fieldbackground=[("readonly", app.panel_dark)],
        foreground=[("readonly", app.text_color)],
        selectbackground=[("readonly", app.panel_dark)],
        selectforeground=[("readonly", app.text_color)],
    )
