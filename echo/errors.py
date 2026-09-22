"""Error contracts: LLM API errors and transcription error message mapping."""

import re

REDACTED = "[REDACTED]"

# Вход обрезается ДО первого regex-прохода: это и есть защита от ReDoS
# (T-07-01-05). Все шаблоны ниже используют простые квантификаторы — вложенных нет.
MAX_SANITIZE_INPUT = 4000

_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{4,}")
_SK_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{4,}")
_USERINFO_RE = re.compile(r"(?i)\b(https?)://[^/\s:@]+:[^/\s@]+@")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{40,}\b")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WS_RE = re.compile(r"\s+")


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


class InvalidBaseUrlError(ValueError):
    """base_url не прошёл проверку (SEC-02).

    Наследуемся от ValueError, а НЕ от SummaryApiError, осознанно: `is_layer_failure`
    возвращает True для `code is None`, поэтому ошибка-наследник SummaryApiError
    заставила бы лестницу слоёв повторить заведомо неверный запрос три раза.
    """


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


def sanitize_error_detail(detail, secrets=(), limit: int = 300) -> str:
    """Обезвредить текст ошибки перед показом пользователю (SEC-05).

    Порядок операций важен и не должен меняться:
      1. обрезать вход до MAX_SANITIZE_INPUT (защита от ReDoS);
      2. вырезать известные секреты длиной >= 4 символов (короткий секрет вырезал бы
         половину сообщения);
      3. вырезать шаблоны: Bearer-токены, `sk-` ключи, логин/пароль внутри URL,
         длинные (>= 40 символов) опейк-токены;
      4. схлопнуть управляющие символы и пробелы в один пробел;
      5. обрезать до `limit` с многоточием.

    Пустая строка на выходе означает "в деталях не осталось ничего полезного";
    решение о тексте-заглушке принимает вызывающий код.
    """
    if detail is None:
        return ""
    text = detail if isinstance(detail, str) else str(detail)
    text = text[:MAX_SANITIZE_INPUT]

    for secret in secrets or ():
        if isinstance(secret, str) and len(secret) >= 4:
            text = text.replace(secret, REDACTED)

    text = _BEARER_RE.sub("Bearer " + REDACTED, text)
    text = _SK_RE.sub("sk-" + REDACTED, text)
    text = _USERINFO_RE.sub(r"\1://" + REDACTED + "@", text)
    text = _LONG_TOKEN_RE.sub(REDACTED, text)
    text = _CONTROL_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()

    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text
