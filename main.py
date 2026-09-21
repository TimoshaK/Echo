"""Whisper Transcriber — GUI application for audio transcription."""

import json
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import urllib.request
import urllib.error

import whisper

import app_config


DEFAULT_PRESET = "free"

# Единственный источник истины по пресетам конспекта: порядок ключей dict =
# порядок пунктов в Combobox (Task 3). Ключи разделов — ASCII, потому что они
# уходят и в json_schema-слой, и в json_object-инструкцию; русские заголовки
# берутся из "title" при рендере.
SUMMARY_PRESETS = {
    "daily": {
        "label": "Дейли",
        "title": "ДЕЙЛИ",
        "hint": "дейли-встречи",
        "schema_name": "daily_conspect",
        "sections": [
            {"key": "tasks", "title": "AFD", "kind": "list"},
            {"key": "decisions", "title": "РЕШЕНИЯ", "kind": "list"},
            {"key": "blockers", "title": "БЛОКЕРЫ", "kind": "list"},
        ],
    },
    "lecture": {
        "label": "Лекция",
        "title": "ЛЕКЦИЯ",
        "hint": "лекции",
        "schema_name": "lecture_conspect",
        "sections": [
            {"key": "thesis", "title": "ТЕЗИС", "kind": "text"},
            {"key": "key_points", "title": "КЛЮЧЕВЫЕ ПУНКТЫ", "kind": "list"},
            {"key": "terms", "title": "ТЕРМИНЫ", "kind": "list"},
            {"key": "conclusions", "title": "ВЫВОДЫ", "kind": "list"},
        ],
    },
    "interview": {
        "label": "Интервью",
        "title": "ИНТЕРВЬЮ",
        "hint": "интервью",
        "schema_name": "interview_conspect",
        "sections": [
            {"key": "summary", "title": "РЕЗЮМЕ", "kind": "text"},
            {"key": "qa", "title": "ВОПРОСЫ И ОТВЕТЫ", "kind": "list"},
            {"key": "quotes", "title": "ЦИТАТЫ", "kind": "list"},
        ],
    },
    "client": {
        "label": "Клиент",
        "title": "КЛИЕНТ",
        "hint": "встречи с клиентом",
        "schema_name": "client_conspect",
        "sections": [
            {"key": "requirements", "title": "ТРЕБОВАНИЯ", "kind": "list"},
            {"key": "agreements", "title": "ДОГОВОРЁННОСТИ", "kind": "list"},
            {"key": "next_steps", "title": "СЛЕДУЮЩИЕ ШАГИ", "kind": "list"},
        ],
    },
    "free": {
        "label": "Свободный",
        "title": "СВОБОДНЫЙ",
        "hint": "свободного конспекта",
        "schema_name": None,
        "sections": [],
    },
}


class SummaryApiError(RuntimeError):
    """Ошибка обращения к LLM API.

    `code` — HTTP-статус, 0 — сетевая ошибка, None — некорректный/пустой
    ответ (провал слоя). Наследуемся от RuntimeError осознанно: существующие
    `_run_summary`/UI ловят `Exception`, а `summarize` умеет пробрасывать
    терминальные ошибки без потери кода (`_is_layer_failure`).
    """

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


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


class SummarizationEngine:
    """Pluggable LLM summarization via OpenAI-compatible API (OpenRouter)."""

    def __init__(self) -> None:
        self.config = app_config.load_config()

        # T-260921-01: значение пресета из файла используется только как ключ
        # реестра и обязательно валидируется — неизвестное значение -> дефолт.
        preset = self.config.get("llm", {}).get("summary_preset", DEFAULT_PRESET)
        if preset not in SUMMARY_PRESETS:
            preset = DEFAULT_PRESET
        self.preset = preset

        self.progress_queue: queue.Queue = queue.Queue()

    def is_configured(self) -> bool:
        llm = self.config.get("llm", {})
        return bool(llm.get("api_key")) and llm.get("enabled")

    def set_preset(self, preset_id: str) -> None:
        """Сохранить выбранный пресет конспекта в конфиг (T-260921-01)."""
        if preset_id not in SUMMARY_PRESETS:
            preset_id = DEFAULT_PRESET
        self.preset = preset_id
        self.config.setdefault("llm", {})["summary_preset"] = preset_id
        app_config.save_config(self.config)

    def update_config(self, api_key: str, base_url: str, model: str, enabled: bool) -> None:
        self.config["llm"] = {
            "api_key": api_key.strip(),
            "base_url": base_url.strip().rstrip("/"),
            "model": model.strip(),
            "enabled": enabled,
            # Сохраняем выбранный пресет: иначе SAVE в API SETTINGS затрёт его.
            "summary_preset": self.preset,
        }
        app_config.save_config(self.config)

    def _post_chat(self, payload: dict) -> str:
        """Единственное место с сетью: POST /chat/completions.

        Возвращает только `message["content"]` (T-260921-05: `reasoning_content`
        не читается и не рендерится). Ошибки всегда `SummaryApiError`, чтобы
        `code` не терялся по дороге; решение "повторять или остановиться"
        принимает `summarize` через `_is_layer_failure`.
        """
        llm = self.config["llm"]
        req = urllib.request.Request(
            f"{llm['base_url']}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                # T-260921-02: api_key уходит только в заголовок, не в тело и не
                # в текст ошибок.
                "Authorization": f"Bearer {llm['api_key']}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise SummaryApiError(f"Ошибка API ({e.code}): {detail}", code=e.code)
        except urllib.error.URLError as e:
            raise SummaryApiError(f"Сетевая ошибка: {e.reason}", code=0)

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            # Провал слоя, а не терминальная ошибка: следующий слой может спасти.
            raise SummaryApiError("Неожиданный ответ от API.", code=None)

        # reasoning-модель при truncation отдаёт content="" + finish_reason
        # "length" — это тоже провал слоя, идём на следующий.
        if not isinstance(content, str) or not content.strip():
            raise SummaryApiError("Пустой ответ от API.", code=None)

        return content.strip()

    @staticmethod
    def _json_schema_format(preset: dict) -> dict | None:
        """`response_format` для json_schema-слоя (None для free-пресета)."""
        name = preset.get("schema_name")
        if name is None:
            return None

        properties: dict = {}
        required: list = []
        for section in preset.get("sections") or []:
            if section.get("kind") == "list":
                properties[section["key"]] = {
                    "type": "array",
                    "items": {"type": "string"},
                }
            else:
                properties[section["key"]] = {"type": "string"}
            required.append(section["key"])

        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }

    @staticmethod
    def _json_instruction(preset: dict) -> str:
        """Текстовая JSON-инструкция для json_object-слоя."""
        lines = [
            "Верни ТОЛЬКО JSON-объект без markdown-ограждений и пояснений "
            "со следующими ключами:"
        ]
        for section in preset.get("sections") or []:
            kind = "массив строк" if section.get("kind") == "list" else "строка"
            lines.append(f'  "{section["key"]}": {kind} — {section["title"]}')
        return "\n".join(lines)

    def _build_messages(
        self, preset: dict, text: str, json_mode: str | None
    ) -> list[dict]:
        """Собрать messages для запроса; `json_mode` — тип response_format."""
        system = "Ты — ассистент для создания конспектов аудио."
        if json_mode is not None:
            system += " Отвечай строго в формате JSON, без markdown-ограждений."

        if preset["schema_name"] is None:
            # free-пресет: сохраняем текущий промпт дословно.
            instruction = (
                "Составь краткий конспект следующей транскрипции аудио: "
                "выдели основные темы и ключевые идеи."
            )
        else:
            hint = preset.get("hint") or preset["title"].lower()
            instruction = f"Составь конспект ({hint})."

        if json_mode is not None:
            instruction += " " + self._json_instruction(preset)

        user = (
            f"{instruction} Пиши на языке исходного аудио.\n\n"
            f"ТРАНСКРИПЦИЯ:\n{text}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    @staticmethod
    def _parse_json_content(content: str) -> dict | None:
        """Вернуть dict из ответа модели или None.

        Только линейные операции (T-260921-04): strip, срез по первой `{` и
        последней `}`, `json.loads`. Никаких regex и рекурсии.
        """
        if not isinstance(content, str):
            return None
        s = content.strip()
        if not s:
            return None

        # Снять markdown-ограждение ```json ... ```
        if s.startswith("```"):
            first_nl = s.find("\n")
            if first_nl != -1:
                body = s[first_nl + 1:]
                last_fence = body.rfind("```")
                if last_fence != -1:
                    body = body[:last_fence]
                s = body.strip()

        parsed = None
        try:
            parsed = json.loads(s)
        except (json.JSONDecodeError, ValueError, TypeError):
            parsed = None

        if not isinstance(parsed, dict):
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end > start:
                try:
                    parsed = json.loads(s[start:end + 1])
                except (json.JSONDecodeError, ValueError, TypeError):
                    parsed = None

        # T-260921-03: пригоден только dict; None/список/скаляр -> следующий слой.
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _render_sections(preset: dict, data: dict) -> str | None:
        """Отрендерить человекочитаемые разделы; None для непригодного JSON."""
        sections = preset.get("sections") or []

        # T-260921-03: рендерим только известные ключи реестра; если ни одного —
        # JSON непригоден, идём на следующий слой.
        if not any(section["key"] in data for section in sections):
            return None

        blocks = []
        for section in sections:
            value = data.get(section["key"])
            block = [section["title"]]
            if section.get("kind") == "list":
                items = []
                if isinstance(value, list):
                    items = [str(item).strip() for item in value if str(item).strip()]
                elif isinstance(value, str) and value.strip():
                    items = [value.strip()]
                if items:
                    block.extend(f"  • {item}" for item in items)
                else:
                    block.append("  — нет данных —")
            else:
                text = value.strip() if isinstance(value, str) else ""
                block.append(text if text else "— нет данных —")
            blocks.append("\n".join(block))

        rule = "=" * 40
        # Внутренний заголовок НЕ содержит слова «КОНСПЕКТ»: save_transcription_txt
        # добавляет свой блок, иначе в .txt получится двойной заголовок.
        return f"{rule}\n{preset['title']}\n{rule}\n\n" + "\n\n".join(blocks)

    def _request_content(
        self, preset: dict, text: str, response_format: dict | None
    ) -> str:
        """Один слой запроса: собрать payload и отправить (без повторов)."""
        llm = self.config["llm"]
        mode = response_format["type"] if response_format else None
        payload = {
            "model": llm["model"],
            "messages": self._build_messages(preset, text, mode),
            "temperature": 0.3,
            # max_tokens НЕ выставляем: reasoning-модель уходит в reasoning и
            # отдаёт пустой content.
        }
        if response_format is not None:
            payload["response_format"] = response_format
        return self._post_chat(payload)

    def _try_render(self, preset: dict, content: str | None) -> str | None:
        """None если контента нет или JSON непригоден, иначе разделы."""
        if content is None:
            return None
        data = self._parse_json_content(content)
        if data is None:
            return None
        return self._render_sections(preset, data)

    @staticmethod
    def _is_layer_failure(exc: "SummaryApiError") -> bool:
        """True, если ошибку можно вылечить следующим слоем.

        Терминальные (401/403/429/5xx/сеть=0) не повторяются: они не связаны с
        поддержкой `response_format` и повторный вызов только жжёт время/квоту.
        """
        if exc.code is None:          # пустой/неожиданный ответ -> провал слоя
            return True
        if exc.code in (400, 422):    # провайдер не принял response_format
            return True
        return False                  # остальное — терминально

    def summarize(self, text: str, preset_id: str | None = None) -> str:
        """Конспект текста через LLM.

        Лестница слоёв: `json_schema` -> `json_object` -> plain text. Провал
        слоя (400/422, пустой/неожиданный ответ, непригодный JSON) ведёт на
        следующий слой; терминальная ошибка (401/403/429/5xx/сеть) сразу
        уходит наверх как `SummaryApiError` без повторов. Для пресета `free`
        запрос уходит без `response_format` (текущее поведение).
        """
        if not self.is_configured():
            raise RuntimeError(
                "LLM API не настроен. Откройте настройки и укажите ключ API."
            )

        # T-260921-01: и аргумент, и self.preset валидируются по реестру.
        preset = SUMMARY_PRESETS.get(preset_id or self.preset) or SUMMARY_PRESETS[DEFAULT_PRESET]

        if preset["schema_name"] is None:
            # free: без response_format, терминальная ошибка уезжает наверх.
            return self._request_content(preset, text, None)

        # Слой 1: json_schema
        try:
            c1 = self._request_content(preset, text, self._json_schema_format(preset))
        except SummaryApiError as e:
            if not self._is_layer_failure(e):
                raise
            c1 = None
        rendered = self._try_render(preset, c1)
        if rendered is not None:
            return rendered

        # Слой 2: json_object + JSON-инструкция
        try:
            c2 = self._request_content(preset, text, {"type": "json_object"})
        except SummaryApiError as e:
            if not self._is_layer_failure(e):
                raise
            c2 = None
        rendered = self._try_render(preset, c2)
        if rendered is not None:
            return rendered

        # Слой 3: plain text — гарантированный финал. Пустой content здесь не
        # перехватываем: показывать пользователю нечего.
        return self._request_content(preset, text, None)

    def start_summary(self, text: str) -> None:
        thread = threading.Thread(
            target=self._run_summary,
            args=(text,),
            daemon=True,
        )
        thread.start()

    def _run_summary(self, text: str) -> None:
        try:
            self.progress_queue.put({"type": "summary_status", "text": "Генерация конспекта..."})
            summary = self.summarize(text)
            self.progress_queue.put({"type": "summary_complete", "text": summary})
        except Exception as e:
            self.progress_queue.put({"type": "summary_error", "error": str(e)})


class TranscriberApp:
    """Main application window for Whisper Transcription."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        # Industrial UI colors
        self.bg_color = "#252525"
        self.panel_color = "#303030"
        self.panel_dark = "#1D1D1D"
        self.accent_color = "#F2A900"
        self.accent_dark = "#B87900"
        self.text_color = "#E6E6E6"
        self.muted_color = "#929292"
        self.success_color = "#7DBE3C"
        self.error_color = "#D9534F"

        self.root.title("Echo // Audio Processing Unit")
        self.root.geometry("900x650")
        self.root.minsize(750, 550)
        self.root.configure(bg=self.bg_color)
        

        self.selected_file: str | None = None
        self.engine = TranscriptionEngine()
        self.summarizer = SummarizationEngine()
        self.last_transcript = ""
        self.last_segments: list = []
        self.last_summary = ""

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the industrial-style main window."""

        # ---------------------------------------------------------
        # Root layout
        # ---------------------------------------------------------

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------

        header = tk.Frame(
            self.root,
            bg=self.panel_dark,
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
            bg=self.panel_dark,
        )
        title_frame.pack(side="left", padx=18, pady=10)

        tk.Label(
            title_frame,
            text="ECHO",
            font=("Segoe UI", 22, "bold"),
            fg=self.accent_color,
            bg=self.panel_dark,
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="AUDIO PROCESSING UNIT",
            font=("Consolas", 9),
            fg=self.muted_color,
            bg=self.panel_dark,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="FICSIT // LOCAL TERMINAL",
            font=("Consolas", 9, "bold"),
            fg=self.text_color,
            bg=self.panel_dark,
        ).pack(side="right", padx=18)

        # ---------------------------------------------------------
        # Audio input panel
        # ---------------------------------------------------------

        input_panel = tk.Frame(
            self.root,
            bg=self.panel_color,
            highlightbackground=self.accent_dark,
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
            fg=self.accent_color,
            bg=self.panel_color,
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(10, 6),
        )

        self.select_btn = tk.Button(
            input_panel,
            text="SELECT FILE",
            command=self.select_file,
            font=("Consolas", 10, "bold"),
            fg="#111111",
            bg=self.accent_color,
            activebackground=self.accent_dark,
            activeforeground="#111111",
            relief="flat",
            bd=0,
            padx=18,
            pady=7,
            cursor="hand2",
        )
        self.select_btn.grid(
            row=1,
            column=0,
            padx=(14, 8),
            pady=(0, 12),
        )

        self.file_var = tk.StringVar(value="NO FILE SELECTED")

        self.file_entry = tk.Entry(
            input_panel,
            textvariable=self.file_var,
            font=("Consolas", 10),
            fg=self.text_color,
            bg=self.panel_dark,
            insertbackground=self.text_color,
            relief="flat",
            bd=0,
        )
        self.file_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 14),
            pady=(0, 12),
            ipady=7,
        )
        self.file_entry.configure(state="readonly")

        # ---------------------------------------------------------
        # Processing panel
        # ---------------------------------------------------------

        processing_panel = tk.Frame(
            self.root,
            bg=self.bg_color,
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
            bg=self.panel_color,
            highlightbackground=self.accent_dark,
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
            fg=self.accent_color,
            bg=self.panel_color,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        tk.Label(
            unit_panel,
            text="WHISPER ENGINE // BASE MODEL",
            font=("Consolas", 8),
            fg=self.muted_color,
            bg=self.panel_color,
        ).pack(anchor="w", padx=14)

        self.transcribe_btn = tk.Button(
            unit_panel,
            text="START TRANSCRIPTION",
            command=self.start_transcription,
            state="disabled",
            font=("Consolas", 11, "bold"),
            fg="#111111",
            bg=self.accent_color,
            activebackground=self.accent_dark,
            activeforeground="#111111",
            disabledforeground="#666666",
            relief="flat",
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
        )
        self.transcribe_btn.pack(
            anchor="w",
            padx=14,
            pady=(10, 12),
        )

        # System status

        status_panel = tk.Frame(
            processing_panel,
            bg=self.panel_color,
            highlightbackground=self.accent_dark,
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
            fg=self.accent_color,
            bg=self.panel_color,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.status_indicator = tk.Label(
            status_panel,
            text="● READY",
            font=("Consolas", 11, "bold"),
            fg=self.success_color,
            bg=self.panel_color,
        )
        self.status_indicator.pack(
            anchor="w",
            padx=14,
            pady=(3, 0),
        )

        self.status_label = tk.Label(
            status_panel,
            text="Select an audio file to begin",
            font=("Consolas", 8),
            fg=self.muted_color,
            bg=self.panel_color,
            anchor="w",
        )
        self.status_label.pack(
            fill="x",
            padx=14,
            pady=(3, 10),
        )

        self.settings_btn = tk.Button(
            status_panel,
            text="API SETTINGS",
            command=self.open_settings,
            font=("Consolas", 9, "bold"),
            fg=self.text_color,
            bg=self.panel_dark,
            activebackground=self.accent_dark,
            activeforeground="#111111",
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.settings_btn.pack(
            anchor="w",
            padx=14,
            pady=(0, 6),
        )

        # ---------------------------------------------------------
        # Summary preset selector
        # ---------------------------------------------------------

        self.preset_labels = {
            preset["label"]: preset_id
            for preset_id, preset in SUMMARY_PRESETS.items()
        }

        tk.Label(
            status_panel,
            text="SUMMARY PRESET",
            font=("Consolas", 8, "bold"),
            fg=self.muted_color,
            bg=self.panel_color,
        ).pack(anchor="w", padx=14, pady=(0, 2))

        self._configure_combobox_style()

        self.preset_var = tk.StringVar(
            value=SUMMARY_PRESETS[self.summarizer.preset]["label"]
        )
        self.preset_combo = ttk.Combobox(
            status_panel,
            textvariable=self.preset_var,
            values=list(self.preset_labels.keys()),
            state="readonly",
            width=24,
            style="Echo.TCombobox",
            font=("Consolas", 9),
        )
        self.preset_combo.pack(anchor="w", padx=14, pady=(0, 10))
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_change)

        self.summary_btn = tk.Button(
            status_panel,
            text="GENERATE SUMMARY",
            command=self.generate_summary,
            state="disabled",
            font=("Consolas", 10, "bold"),
            fg="#111111",
            bg=self.accent_color,
            activebackground=self.accent_dark,
            activeforeground="#111111",
            disabledforeground="#666666",
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            cursor="hand2",
        )
        self.summary_btn.pack(
            anchor="w",
            padx=14,
            pady=(0, 12),
        )

        # ---------------------------------------------------------
        # Output panel
        # ---------------------------------------------------------

        output_panel = tk.Frame(
            self.root,
            bg=self.panel_color,
            highlightbackground=self.accent_dark,
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
            fg=self.accent_color,
            bg=self.panel_color,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(10, 6),
        )

        text_frame = tk.Frame(
            output_panel,
            bg=self.panel_dark,
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

        self.result_text = tk.Text(
            text_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
            fg=self.text_color,
            bg=self.panel_dark,
            insertbackground=self.accent_color,
            selectbackground=self.accent_dark,
            selectforeground="#111111",
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
        )

        self.result_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.result_scrollbar = tk.Scrollbar(
            text_frame,
            command=self.result_text.yview,
            bg=self.panel_color,
            troughcolor=self.panel_dark,
            activebackground=self.accent_color,
            relief="flat",
            bd=0,
        )

        self.result_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.result_text.configure(
            yscrollcommand=self.result_scrollbar.set
        )

        self._build_save_buttons()

        # ---------------------------------------------------------
        # Footer
        # ---------------------------------------------------------

        footer = tk.Frame(
            self.root,
            bg=self.panel_dark,
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

        self.language_label = tk.Label(
            footer,
            text="LANGUAGE: --",
            font=("Consolas", 8, "bold"),
            fg=self.muted_color,
            bg=self.panel_dark,
        )
        self.language_label.pack(
            side="left",
            padx=14,
        )

        tk.Label(
            footer,
            text="ECHO // FICSIT AUDIO UNIT // ONLINE",
            font=("Consolas", 8),
            fg=self.muted_color,
            bg=self.panel_dark,
        ).pack(
            side="right",
            padx=14,
        )

    def _configure_combobox_style(self) -> None:
        """Тёмная палитра для ttk.Combobox; сбой темы не должен ломать UI."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Echo.TCombobox",
            fieldbackground=self.panel_dark,
            background=self.panel_dark,
            foreground=self.text_color,
            arrowcolor=self.accent_color,
        )
        style.map(
            "Echo.TCombobox",
            fieldbackground=[("readonly", self.panel_dark)],
            foreground=[("readonly", self.text_color)],
            selectbackground=[("readonly", self.panel_dark)],
            selectforeground=[("readonly", self.text_color)],
        )

    def on_preset_change(self, event=None) -> None:
        """Сохранить выбранный пресет; без сетевых вызовов и перезапуска."""
        label = self.preset_var.get()
        preset_id = self.preset_labels.get(label, DEFAULT_PRESET)
        self.summarizer.set_preset(preset_id)
        self.status_label.configure(
            text=f"PRESET // {SUMMARY_PRESETS[preset_id]['title']}"
        )

    def _build_save_buttons(self) -> None:
        """Build the output save buttons row."""
        save_frame = tk.Frame(self.root, bg=self.bg_color)
        save_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 6))

        btn_style = {
            "font": ("Consolas", 9, "bold"),
            "fg": self.text_color,
            "bg": self.panel_color,
            "activebackground": self.accent_dark,
            "activeforeground": "#111111",
            "disabledforeground": "#666666",
            "relief": "flat",
            "bd": 0,
            "padx": 14,
            "pady": 6,
            "cursor": "hand2",
        }

        self.save_txt_btn = tk.Button(
            save_frame,
            text="SAVE .TXT",
            command=self.save_transcription_txt,
            state="disabled",
            **btn_style,
        )
        self.save_txt_btn.pack(side="left", padx=(0, 8))

        self.save_srt_btn = tk.Button(
            save_frame,
            text="SAVE .SRT",
            command=self.save_transcription_srt,
            state="disabled",
            **btn_style,
        )
        self.save_srt_btn.pack(side="left")

    @staticmethod
    def _time_to_srt(seconds: float, offset: float = 0.0) -> str:
        total = int(seconds + offset)
        millis = int((seconds + offset - total) * 1000)
        hours, rem = divmod(total, 3600)
        minutes, secs = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _base_name(self) -> str:
        if not self.selected_file:
            return "transcript"
        return os.path.splitext(os.path.basename(self.selected_file))[0]

    def _srt_content(self) -> str:
        lines = []
        for idx, seg in enumerate(self.last_segments, start=1):
            start = self._time_to_srt(float(seg.get("start", 0)))
            end = self._time_to_srt(float(seg.get("end", 0)))
            text = str(seg.get("text", "")).strip()
            lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

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
                f.write(self._srt_content())
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
        messagebox.showerror(
            "Ошибка конспекта",
            f"Не удалось сгенерировать конспект.\n\n{error}",
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
        settings = tk.Toplevel(self.root)
        settings.title("API Settings")
        settings.configure(bg=self.bg_color)
        settings.geometry("480x360")
        settings.resizable(False, False)
        settings.transient(self.root)
        settings.grab_set()

        pad = {"padx": 14, "pady": 8}

        tk.Label(
            settings,
            text="LLM API SETTINGS",
            font=("Consolas", 12, "bold"),
            fg=self.accent_color,
            bg=self.bg_color,
        ).pack(anchor="w", padx=14, pady=(14, 6))

        tk.Label(
            settings,
            text="API Key",
            font=("Consolas", 9, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
        ).pack(anchor="w", **pad)

        key_var = tk.StringVar(value=self.summarizer.config["llm"]["api_key"])
        key_entry = tk.Entry(
            settings,
            textvariable=key_var,
            font=("Consolas", 10),
            fg=self.text_color,
            bg=self.panel_dark,
            insertbackground=self.text_color,
            relief="flat",
            show="*",
        )
        key_entry.pack(fill="x", **pad)

        tk.Label(
            settings,
            text="Base URL",
            font=("Consolas", 9, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
        ).pack(anchor="w", **pad)

        url_var = tk.StringVar(value=self.summarizer.config["llm"]["base_url"])
        tk.Entry(
            settings,
            textvariable=url_var,
            font=("Consolas", 10),
            fg=self.text_color,
            bg=self.panel_dark,
            insertbackground=self.text_color,
            relief="flat",
        ).pack(fill="x", **pad)

        tk.Label(
            settings,
            text="Model",
            font=("Consolas", 9, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
        ).pack(anchor="w", **pad)

        model_var = tk.StringVar(value=self.summarizer.config["llm"]["model"])
        tk.Entry(
            settings,
            textvariable=model_var,
            font=("Consolas", 10),
            fg=self.text_color,
            bg=self.panel_dark,
            insertbackground=self.text_color,
            relief="flat",
        ).pack(fill="x", **pad)

        enabled_var = tk.BooleanVar(value=self.summarizer.config["llm"]["enabled"])
        tk.Checkbutton(
            settings,
            text="Enable LLM API",
            variable=enabled_var,
            font=("Consolas", 9, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.text_color,
            selectcolor=self.panel_dark,
            relief="flat",
        ).pack(anchor="w", **pad)

        def save_settings() -> None:
            self.summarizer.update_config(
                api_key=key_var.get(),
                base_url=url_var.get(),
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
            bg=self.accent_color,
            activebackground=self.accent_dark,
            activeforeground="#111111",
            relief="flat",
            bd=0,
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(anchor="w", padx=14, pady=(8, 14))

    def _handle_transcription_error(self, error: str) -> None:
        """Handle transcription error with appropriate message."""

        self.status_indicator.configure(
            text="● ERROR",
            fg=self.error_color,
        )

        # Map common errors to user-friendly messages
        error_lower = error.lower()

        if "ffmpeg" in error_lower or "avconv" in error_lower:
            error_msg = "Не установлен ffmpeg. Установите ffmpeg и попробуйте снова."
        elif "format" in error_lower or "codec" in error_lower:
            error_msg = "Неподдерживаемый формат файла. Используйте MP3, WAV, M4A, FLAC, OGG или WebM."
        elif "model" in error_lower or "download" in error_lower:
            error_msg = "Не удалось загрузить модель Whisper. Проверьте подключение к интернету."
        elif "memory" in error_lower or "allocat" in error_lower:
            error_msg = "Недостаточно памяти. Попробуйте файл меньшего размера."
        else:
            error_msg = "Ошибка при обработке аудио. Попробуйте другой файл."

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


def main() -> None:
    root = tk.Tk()
    TranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
