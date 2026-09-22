"""LLM API settings modal for the Echo UI."""

import tkinter as tk
from tkinter import messagebox

from echo.errors import InvalidBaseUrlError
from echo.llm_client import validate_base_url


def validate_settings_base_url(raw: str) -> tuple[bool, str]:
    """Проверить введённый base_url (SEC-02).

    Возвращает (True, нормализованный_url) либо (False, текст ошибки).
    Никогда не бросает исключение: возврат пары делает функцию пригодной
    для тестов без Tk.
    """
    try:
        return True, validate_base_url(raw)
    except InvalidBaseUrlError as e:
        return False, str(e)


def open_settings(app) -> None:
    """Open the LLM API settings dialog."""
    settings = tk.Toplevel(app.root)
    settings.title("API Settings")
    settings.configure(bg=app.bg_color)
    settings.geometry("480x360")
    settings.resizable(False, False)
    settings.transient(app.root)
    settings.grab_set()

    pad = {"padx": 14, "pady": 8}

    tk.Label(
        settings,
        text="LLM API SETTINGS",
        font=("Consolas", 12, "bold"),
        fg=app.accent_color,
        bg=app.bg_color,
    ).pack(anchor="w", padx=14, pady=(14, 6))

    tk.Label(
        settings,
        text="API Key",
        font=("Consolas", 9, "bold"),
        fg=app.text_color,
        bg=app.bg_color,
    ).pack(anchor="w", **pad)

    key_var = tk.StringVar(value=app.summarizer.config["llm"]["api_key"])
    key_entry = tk.Entry(
        settings,
        textvariable=key_var,
        font=("Consolas", 10),
        fg=app.text_color,
        bg=app.panel_dark,
        insertbackground=app.text_color,
        relief="flat",
        show="*",
    )
    key_entry.pack(fill="x", **pad)

    tk.Label(
        settings,
        text="Base URL",
        font=("Consolas", 9, "bold"),
        fg=app.text_color,
        bg=app.bg_color,
    ).pack(anchor="w", **pad)

    url_var = tk.StringVar(value=app.summarizer.config["llm"]["base_url"])
    tk.Entry(
        settings,
        textvariable=url_var,
        font=("Consolas", 10),
        fg=app.text_color,
        bg=app.panel_dark,
        insertbackground=app.text_color,
        relief="flat",
    ).pack(fill="x", **pad)

    tk.Label(
        settings,
        text="Model",
        font=("Consolas", 9, "bold"),
        fg=app.text_color,
        bg=app.bg_color,
    ).pack(anchor="w", **pad)

    model_var = tk.StringVar(value=app.summarizer.config["llm"]["model"])
    tk.Entry(
        settings,
        textvariable=model_var,
        font=("Consolas", 10),
        fg=app.text_color,
        bg=app.panel_dark,
        insertbackground=app.text_color,
        relief="flat",
    ).pack(fill="x", **pad)

    enabled_var = tk.BooleanVar(value=app.summarizer.config["llm"]["enabled"])
    tk.Checkbutton(
        settings,
        text="Enable LLM API",
        variable=enabled_var,
        font=("Consolas", 9, "bold"),
        fg=app.text_color,
        bg=app.bg_color,
        activebackground=app.bg_color,
        activeforeground=app.text_color,
        selectcolor=app.panel_dark,
        relief="flat",
    ).pack(anchor="w", **pad)

    def save_settings() -> None:
        ok, result = validate_settings_base_url(url_var.get())
        if not ok:
            # SEC-02: не сохраняем и НЕ закрываем диалог — пользователь должен
            # увидеть причину и исправить адрес, а не потерять введённый ключ.
            messagebox.showerror("Ошибка настроек", result)
            return

        app.summarizer.update_config(
            api_key=key_var.get(),
            base_url=result,
            model=model_var.get(),
            enabled=enabled_var.get(),
        )
        settings.destroy()

    tk.Button(
        settings,
        text="SAVE",
        command=save_settings,
        font=("Consolas", 10, "bold"),
        fg="#111111",
        bg=app.accent_color,
        activebackground=app.accent_dark,
        activeforeground="#111111",
        relief="flat",
        bd=0,
        padx=16,
        pady=7,
        cursor="hand2",
    ).pack(anchor="w", padx=14, pady=(8, 14))
