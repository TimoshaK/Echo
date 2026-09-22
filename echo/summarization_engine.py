"""Stateful LLM summarization engine (config + preset + progress queue).

All network I/O and all pure message/schema/parse/render helpers live in
`echo.llm_client`; this module owns the mutable state and the request ladder.
"""

import json
import queue
import threading

from echo import llm_client
from echo.config import DEFAULT_CONFIG, ConfigCorruptError, load_config, save_config
from echo.errors import SummaryApiError, sanitize_error_detail
from echo.presets import DEFAULT_PRESET, SUMMARY_PRESETS


class SummarizationEngine:
    """Pluggable LLM summarization via OpenAI-compatible API (OpenRouter)."""

    def __init__(self) -> None:
        # SEC-04: повреждённый конфиг НЕ должен убивать приложение на старте.
        # `__init__` работает в главном потоке Tk, поэтому исключение здесь значит,
        # что окно вообще не откроется. Сохраняем причину для UI и живём на
        # дефолтах: транскрибация продолжает работать, отключается только конспект.
        self.config_error: str | None = None
        try:
            self.config = load_config()
        except ConfigCorruptError as e:
            self.config_error = str(e)
            self.config = json.loads(json.dumps(DEFAULT_CONFIG))

        # T-260921-01: значение пресета из файла используется только как ключ
        # реестра и обязательно валидируется — неизвестное значение -> дефолт.
        preset = self.config.get("llm", {}).get("summary_preset", DEFAULT_PRESET)
        if preset not in SUMMARY_PRESETS:
            preset = DEFAULT_PRESET
        self.preset = preset

        self.progress_queue: queue.Queue = queue.Queue()

    def is_configured(self) -> bool:
        if self.config_error:
            return False
        llm = self.config.get("llm", {})
        return bool(llm.get("api_key")) and llm.get("enabled")

    def set_preset(self, preset_id: str) -> None:
        """Сохранить выбранный пресет конспекта в конфиг (T-260921-01)."""
        if preset_id not in SUMMARY_PRESETS:
            preset_id = DEFAULT_PRESET
        self.preset = preset_id
        self.config.setdefault("llm", {})["summary_preset"] = preset_id
        save_config(self.config)

    def update_config(self, api_key: str, base_url: str, model: str, enabled: bool) -> None:
        self.config["llm"] = {
            "api_key": api_key.strip(),
            "base_url": base_url.strip().rstrip("/"),
            "model": model.strip(),
            "enabled": enabled,
            # Сохраняем выбранный пресет: иначе SAVE в API SETTINGS затрёт его.
            "summary_preset": self.preset,
        }
        save_config(self.config)

    def _request_content(
        self, preset: dict, text: str, response_format: dict | None
    ) -> str:
        """Один слой запроса: собрать payload и отправить (без повторов)."""
        llm = self.config["llm"]
        mode = response_format["type"] if response_format else None
        payload = {
            "model": llm["model"],
            "messages": llm_client.build_messages(preset, text, mode),
            "temperature": 0.3,
            # max_tokens НЕ выставляем: reasoning-модель уходит в reasoning и
            # отдаёт пустой content.
        }
        if response_format is not None:
            payload["response_format"] = response_format
        return llm_client.post_chat(self.config, payload)

    def summarize(self, text: str, preset_id: str | None = None) -> str:
        """Конспект текста через LLM.

        Лестница слоёв: `json_schema` -> `json_object` -> plain text. Провал
        слоя (400/422, пустой/неожиданный ответ, непригодный JSON) ведёт на
        следующий слой; терминальная ошибка (401/403/429/5xx/сеть) сразу
        уходит наверх как `SummaryApiError` без повторов. Для пресета `free`
        запрос уходит без `response_format` (текущее поведение).
        """
        if self.config_error:
            raise RuntimeError(
                "Конфигурация повреждена: не удалось прочитать app_config.json. "
                "Исправьте файл или сохраните настройки заново в API SETTINGS."
            )

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
            c1 = self._request_content(preset, text, llm_client.json_schema_format(preset))
        except SummaryApiError as e:
            if not llm_client.is_layer_failure(e):
                raise
            c1 = None
        rendered = llm_client.try_render(preset, c1)
        if rendered is not None:
            return rendered

        # Слой 2: json_object + JSON-инструкция
        try:
            c2 = self._request_content(preset, text, {"type": "json_object"})
        except SummaryApiError as e:
            if not llm_client.is_layer_failure(e):
                raise
            c2 = None
        rendered = llm_client.try_render(preset, c2)
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
            # SEC-05: санитизируем ДО очереди, а не только на показе, чтобы
            # секрет не оказался в payload для любого будущего потребителя.
            llm = self.config.get("llm") if isinstance(self.config, dict) else None
            api_key = llm.get("api_key", "") if isinstance(llm, dict) else ""
            self.progress_queue.put(
                {
                    "type": "summary_error",
                    "error": sanitize_error_detail(str(e), secrets=(api_key,)),
                }
            )
