"""Error contracts: LLM API errors and transcription error message mapping."""


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


def map_transcription_error(error: str) -> str:
    """Map a raw transcription error string to a user-facing Russian message.

    Extracted verbatim from `TranscriberApp._handle_transcription_error` so the
    mapping stays a pure function. The status-widget updates and the messagebox
    stay in `echo/ui/app.py`.

    Branch ORDER is significant and must not be reordered: `ffmpeg` is tested
    before `format`, and the `model` branch is only reached when `format`/`codec`
    are absent.
    """
    error_lower = error.lower()

    if "ffmpeg" in error_lower or "avconv" in error_lower:
        return "Не установлен ffmpeg. Установите ffmpeg и попробуйте снова."
    elif "format" in error_lower or "codec" in error_lower:
        return "Неподдерживаемый формат файла. Используйте MP3, WAV, M4A, FLAC, OGG или WebM."
    elif "model" in error_lower or "download" in error_lower:
        return "Не удалось загрузить модель Whisper. Проверьте подключение к интернету."
    elif "memory" in error_lower or "allocat" in error_lower:
        return "Недостаточно памяти. Попробуйте файл меньшего размера."
    else:
        return "Ошибка при обработке аудио. Попробуйте другой файл."
