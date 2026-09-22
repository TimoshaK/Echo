"""HTTP transport and pure helpers for the pluggable LLM summarization ladder.

This module is the ONLY place in the application that performs network I/O.
It is stateless: every function takes what it needs as an argument. The stateful
orchestration (config, preset, progress queue) lives in `echo.summarization_engine`.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from echo.errors import InvalidBaseUrlError, SummaryApiError, sanitize_error_detail

MSG_BASE_URL_EMPTY = "Base URL не задан. Укажите адрес вида https://openrouter.ai/api/v1"
MSG_BASE_URL_SCHEME = (
    "Base URL должен использовать https:// (получено: {scheme}). "
    "Незащищённый http:// и другие схемы запрещены."
)
MSG_BASE_URL_HOST = "Base URL не содержит имени хоста: {url}"
MSG_BASE_URL_USERINFO = "Base URL не должен содержать логин/пароль (@)."


def validate_base_url(url: str) -> str:
    """Проверить base_url: только https, только с хостом, без userinfo (SEC-02).

    Возвращает нормализованный адрес (без завершающего слэша). Бросает
    `InvalidBaseUrlError` — НЕ `SummaryApiError`, чтобы лестница слоёв не приняла
    это за провал слоя и не повторила заведомо неверный запрос.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidBaseUrlError(MSG_BASE_URL_EMPTY)

    candidate = url.strip()
    parts = urllib.parse.urlsplit(candidate)
    scheme = parts.scheme.lower()

    if scheme != "https":
        raise InvalidBaseUrlError(MSG_BASE_URL_SCHEME.format(scheme=scheme or "(нет)"))

    if not parts.netloc or not parts.hostname or parts.netloc != parts.netloc.strip():
        raise InvalidBaseUrlError(MSG_BASE_URL_HOST.format(url=candidate))

    if "@" in parts.netloc:
        raise InvalidBaseUrlError(MSG_BASE_URL_USERINFO)

    return candidate.rstrip("/")


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Редирект без утечки учётных данных (SEC-03).

    Штатный HTTPRedirectHandler копирует ВСЕ заголовки, кроме content-length и
    content-type, поэтому Authorization уезжает на чужой хост. Здесь заголовок
    снимается, если меняется origin: схема, хост или порт.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and _is_cross_origin(req.full_url, newurl):
            new_req.headers.pop("Authorization", None)
        return new_req


def _is_cross_origin(origin_url: str, target_url: str) -> bool:
    """True, если цель редиректа — другой origin (схема, хост или порт)."""
    origin = urllib.parse.urlsplit(origin_url)
    target = urllib.parse.urlsplit(target_url)
    if target.scheme.lower() != origin.scheme.lower():
        return True
    return target.netloc.lower() != origin.netloc.lower()


_OPENER = None


def _http_opener() -> urllib.request.OpenerDirector:
    """Отдельный opener только с SafeRedirectHandler.

    Глобальную установку opener через `urllib.request` НЕ выполняем: она мутирует
    состояние всего процесса и задела бы любую другую библиотеку.
    """
    global _OPENER
    if _OPENER is None:
        _OPENER = urllib.request.build_opener(SafeRedirectHandler)
    return _OPENER


def post_chat(config: dict, payload: dict) -> str:
    """Единственное место с сетью: POST /chat/completions.

    Возвращает только `message["content"]` (T-260921-05: `reasoning_content`
    не читается и не рендерится). Ошибки всегда `SummaryApiError`, чтобы
    `code` не терялся по дороге; решение "повторять или остановиться"
    принимает `summarize` через `is_layer_failure`.
    """
    llm = config["llm"]
    base_url = validate_base_url(llm.get("base_url", ""))
    api_key = llm.get("api_key", "")
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            # T-260921-02: api_key уходит только в заголовок, не в тело и не
            # в текст ошибок.
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with _http_opener().open(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = sanitize_error_detail(
            e.read().decode("utf-8", errors="replace"),
            secrets=(api_key,),
        )
        raise SummaryApiError(
            f"Ошибка API ({e.code}): {detail or 'нет деталей'}", code=e.code
        )
    except urllib.error.URLError as e:
        raise SummaryApiError(
            f"Сетевая ошибка: {sanitize_error_detail(e.reason, secrets=(api_key,)) or 'нет деталей'}",
            code=0,
        )

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


def json_schema_format(preset: dict) -> dict | None:
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


def json_instruction(preset: dict) -> str:
    """Текстовая JSON-инструкция для json_object-слоя."""
    lines = [
        "Верни ТОЛЬКО JSON-объект без markdown-ограждений и пояснений "
        "со следующими ключами:"
    ]
    for section in preset.get("sections") or []:
        kind = "массив строк" if section.get("kind") == "list" else "строка"
        lines.append(f'  "{section["key"]}": {kind} — {section["title"]}')
    return "\n".join(lines)


def build_messages(preset: dict, text: str, json_mode: str | None) -> list[dict]:
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
        instruction += " " + json_instruction(preset)

    user = (
        f"{instruction} Пиши на языке исходного аудио.\n\n"
        f"ТРАНСКРИПЦИЯ:\n{text}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_json_content(content: str) -> dict | None:
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


def render_sections(preset: dict, data: dict) -> str | None:
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


def try_render(preset: dict, content: str | None) -> str | None:
    """None если контента нет или JSON непригоден, иначе разделы."""
    if content is None:
        return None
    data = parse_json_content(content)
    if data is None:
        return None
    return render_sections(preset, data)


def is_layer_failure(exc: SummaryApiError) -> bool:
    """True, если ошибку можно вылечить следующим слоем.

    Терминальные (401/403/429/5xx/сеть=0) не повторяются: они не связаны с
    поддержкой `response_format` и повторный вызов только жжёт время/квоту.
    """
    if exc.code is None:          # пустой/неожиданный ответ -> провал слоя
        return True
    if exc.code in (400, 422):    # провайдер не принял response_format
        return True
    return False                  # остальное — терминально
