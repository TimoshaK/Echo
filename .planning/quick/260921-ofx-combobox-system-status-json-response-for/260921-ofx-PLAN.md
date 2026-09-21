---
phase: quick-260921-ofx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [main.py, app_config.py]
autonomous: true
requirements: [SUMR-01, SUMR-02]
must_haves:
  truths:
    - "В панели SYSTEM STATUS рядом с кнопкой GENERATE SUMMARY есть ttk.Combobox (readonly) с 5 пресетами: Дейли / Лекция / Интервью / Клиент / Свободный"
    - "Выбор пресета сохраняется в app_config.json в llm.summary_preset и восстанавливается при следующем запуске"
    - "Для daily/lecture/interview/client запрос уходит с response_format json_schema; провал слоя (HTTP 400/422, пустой/неожиданный ответ с code=None или непригодный JSON) ведёт на json_object; при неудаче обоих JSON-слоёв — plain text без response_format"
    - "Терминальные ошибки (401/403/429/5xx/сеть code=0) показываются пользователю сразу, без повторов; провал слоя (400/422/пустой ответ/неожиданная форма) лестницу НЕ прерывает"
    - "Пресет free отправляет запрос БЕЗ response_format (текущее поведение сохраняется)"
    - "JSON-ответ рендерится в человекочитаемые разделы (заголовки + списки/абзацы) и этот же текст кладётся в self.last_summary, поэтому экспорт .txt с блоком КОНСПЕКТ работает без изменений"
    - "Существующий app_config.json без ключа summary_preset загружается с дефолтом free; сохранение API-настроек (SAVE в API SETTINGS) не затирает выбранный пресет"
  artifacts:
    - path: "app_config.py"
      provides: "Дефолт llm.summary_preset = free + обратно-совместимый backfill"
      contains: "summary_preset"
    - path: "main.py"
      provides: "Реестр пресетов SUMMARY_PRESETS + слоистый fallback summarize + рендер разделов + Combobox в status_panel"
      contains: "SUMMARY_PRESETS"
    - path: "main.py"
      provides: "Класс ошибки API с кодом для управления fallback-лестницей"
      contains: "class SummaryApiError"
    - path: "main.py"
      provides: "Единственное место классификации провал-слоя vs терминальной ошибки"
      contains: "_is_layer_failure"
    - path: "main.py"
      provides: "Пресет-селектор, привязанный к движку и сохранению конфига"
      contains: "self.preset_combo"
  key_links:
    - from: "main.py:TranscriberApp.on_preset_change"
      to: "app_config.save_config"
      via: "SummarizationEngine.set_preset"
      pattern: "set_preset|save_config"
    - from: "main.py:SummarizationEngine.summarize"
      to: "{base_url}/chat/completions"
      via: "payload['response_format']"
      pattern: "response_format"
    - from: "main.py:TranscriberApp._handle_summary_complete"
      to: "self.last_summary"
      via: "rendered text from summary_complete message"
      pattern: "last_summary"
    - from: "main.py:TranscriberApp._build_ui"
      to: "SUMMARY_PRESETS"
      via: "ttk.Combobox values"
      pattern: "preset_labels|preset_combo"
    - from: "main.py:SummarizationEngine.update_config"
      to: "llm.summary_preset"
      via: "preserving preset when rewriting the llm dict"
      pattern: "summary_preset"
---

<objective>
Добавить пресеты конспектов: Combobox в панели SYSTEM STATUS (дейли / лекция / интервью / клиент / свободный), собственную JSON-схему на каждый тип через `response_format`, слоистый fallback `json_schema -> json_object -> plain text`, рендер JSON в читаемые разделы и персист выбранного пресета в `app_config.json`.

Purpose: сейчас конспект всегда генерируется одним "свободным" промптом. Пользователю нужны типовые структуры (задачи/решения/блокеры у дейли, вопросы-ответы у интервью и т.д.) и предсказуемый формат на выходе, при этом без привязки к конкретному LLM-провайдеру.

Output: обновлённые `main.py` и `app_config.py`; выбранный пресет сохраняется между запусками; для структурированных пресетов модель возвращает JSON, который рендерится в разделы и попадает в `self.last_summary` (экспорт .txt не меняется).
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
@$HOME/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/quick/260921-ofx-combobox-system-status-json-response-for/260921-ofx-PLAN.md
@main.py
@app_config.py

## Решения пользователя (ЗАЛОЧЕНЫ — не пересматривать)

1. **UI:** `ttk.Combobox` (readonly) в существующей панели `status_panel` в `main.py`, рядом с кнопкой GENERATE SUMMARY.
2. **Структура:** у каждого пресета СВОЯ схема/разделы (не одна универсальная):
   - daily: задачи / решения / блокеры
   - lecture: тезис / ключевые пункты / термины / выводы
   - interview: резюме / вопросы-ответы / цитаты
   - client: требования / договорённости / следующие шаги
   - free: plain text, БЕЗ `response_format` (текущее поведение)
3. **response_format (слоистый fallback):** сначала `{"type":"json_schema", ...}`; при HTTP 400/422 — повтор с `{"type":"json_object"}` + JSON-инструкция; если и это не удалось или JSON не парсится — fallback на plain text (без `response_format`). Провайдер-независимо (OpenAI-compatible / OpenRouter).
4. **Рендер и сохранение:** распарсенный JSON рендерится в человекочитаемые разделы (заголовки + bullets/key-value). ТОТ ЖЕ отрендеренный текст кладётся в `self.last_summary`, поэтому экспорт .txt работает без изменений.
5. **Персист:** выбранный пресет хранится в `app_config.json` в новом ключе `llm.summary_preset`, дефолт `"free"`, обратно-совместимый backfill для существующих конфигов.

## Проверено эмпирически (2026-09-21, реальный конфиг из app_config.json)

Выполнен один живой запрос к `https://api.dslab.tech/v1/chat/completions` (модель `deepseek-v4.1-flash`) с `response_format = json_schema` (strict, `additionalProperties: false`, ASCII-ключи):

- HTTP 200 — провайдер **принимает** `json_schema` (первый слой реально работает, 400/422 не гарантированы — поэтому fallback всё равно нужен для других провайдеров).
- Ответ приходит в `choices[0].message.content` как чистый JSON (русские значения НЕ экранированы): `{"tasks": [...], "decisions": [...]}`.
- В `message` ТАКЖЕ есть `reasoning_content` — это внутренние рассуждения модели. **Никогда не рендерить `reasoning_content`** и не считать его ответом.
- При малом `max_tokens` модель отдаёт `content: ""` + `finish_reason: "length"`. Поэтому: пустой/пробельный `content` = провал слоя (переход на следующий), и `max_tokens` не выставлять.

Вывод по ключам: используем ASCII-ключи (`tasks`, `decisions`, ...) в схеме/JSON-инструкции и маппим их на русские заголовки разделов при рендере — это совместимо и с `json_schema`, и с `json_object`.

Уточнение к решению №3 (классификация кодов, устраняет противоречие в лестнице): **провал слоя** = `code in {None, 400, 422}` (не поддержан `response_format`, пустой/неожиданный ответ) → идём на следующий слой. **Терминальная ошибка** = всё остальное, в т.ч. `code=0` (сеть), `401`, `403`, `429`, любой `5xx` → показываем пользователю сразу, повторных вызовов нет. Единственная реализация этого правила — `SummarizationEngine._is_layer_failure`.

<interfaces>
<!-- Ключевые контракты из текущего кода. Использовать напрямую, не исследовать кодовую базу. -->

Из app_config.py:
```python
CONFIG_PATH: str  # <repo>/app_config.json
DEFAULT_CONFIG = {
    "llm": {
        "api_key": "",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "enabled": False,
        # ДОБАВИТЬ: "summary_preset": "free",
    }
}

def load_config() -> dict:
    # FileNotFoundError/JSONDecodeError -> deep copy DEFAULT_CONFIG
    # иначе: setdefault по DEFAULT_CONFIG и по DEFAULT_CONFIG["llm"] (это и есть backfill)
def save_config(cfg: dict) -> None:
    # normalized = deep copy DEFAULT_CONFIG; normalized["llm"].update(cfg.get("llm", {}))
    # -> ключи, которых нет в cfg["llm"], берутся из дефолта
```

Из main.py (ТЕКУЩИЙ код, который меняем):
```python
# импорты уже есть: from tkinter import ttk, filedialog, messagebox  (ttk пока не использовался)

class SummarizationEngine:
    def __init__(self) -> None:            # self.config = app_config.load_config()
    def is_configured(self) -> bool:
    def update_config(self, api_key: str, base_url: str, model: str, enabled: bool) -> None:
        # ВНИМАНИЕ: полностью ПЕРЕЗАПИСЫВАЕТ self.config["llm"] 4 ключами -> сейчас затрёт summary_preset
    def summarize(self, text: str) -> str:
        # payload = {"model", "messages", "temperature": 0.3}; POST {base_url}/chat/completions
        # return data["choices"][0]["message"]["content"].strip()
        # HTTPError -> RuntimeError(f"Ошибка API ({e.code}): {detail[:500]}")
        # URLError  -> RuntimeError(f"Сетевая ошибка: {e.reason}")
    def start_summary(self, text: str) -> None:      # поток daemon
    def _run_summary(self, text: str) -> None:
        # queue: {"type":"summary_status","text":...}
        #        {"type":"summary_complete","text": summary}
        #        {"type":"summary_error","error": str(e)}

class TranscriberApp:
    # self.summarizer = SummarizationEngine(); self.last_summary = ""
    # _build_ui(): status_panel -> settings_btn("API SETTINGS") -> summary_btn("GENERATE SUMMARY")
    # generate_summary(): self.summarizer.start_summary(self.last_transcript); self.poll_summary()
    # _handle_summary_complete(): result_text <- message["text"]; self.last_summary = message["text"]
    # save_transcription_txt(): content = self.last_transcript + "КОНСПЕКТ" + self.last_summary
```

## Ограничения окружения

- Запуск Python: `py -3` (алиас `python` сломан). `import main` тянет `whisper` (~1.5 c), это нормально.
- GUI-проверки: только headless-safe — `root = tk.Tk(); root.withdraw(); ...; root.destroy()`. Проверено, что так работает и `ttk.Combobox` со стилем `clam`.
- Консоль PowerShell портит кириллицу. В проверочных скриптах печатать ТОЛЬКО ASCII-результаты и ставить `$env:PYTHONIOENCODING="utf-8"`.
- Одноразовые проверочные скрипты писать в `C:\Users\898F~1\AppData\Local\Temp\opencode\` (вне репозитория), запускать с рабочей директорией `A:\Repos\Echo`, чтобы `import main`/`import app_config` резолвились. В репозитории: только `main.py` и `app_config.py`.
- Тестовой инфраструктуры (pytest) в проекте нет — не создавать; проверки = скрипты с `assert` + `sys.exit(1)`.
</interfaces>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| transcript → LLM prompt | Текст транскрипции недоверенный: может содержать инструкции (prompt injection) |
| LLM response → renderer | `choices[0].message.content` недоверенный: произвольный текст/JSON |
| app_config.json → runtime | Значение `llm.summary_preset` из файла используется как ключ реестра |
| app_config.json → disk | API-ключ хранится в открытом виде (существующее поведение) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260921-01 | Tampering | `SummarizationEngine.summarize` (значение пресета из конфига) | mitigate | Валидировать `preset_id` по ключам `SUMMARY_PRESETS`; неизвестное значение → `DEFAULT_PRESET` ("free"). Никогда не использовать значение из файла как индекс/атрибут напрямую (Task 1). |
| T-260921-02 | Information Disclosure | сообщения об ошибках API | mitigate | В текст исключения попадает только `e.code` и обрезанный до 500 символов `detail`; `Authorization`/`api_key` не логировать и не включать в сообщения (Task 2). |
| T-260921-03 | Tampering (Injection) | рендер ответа LLM | mitigate | Рендерить ТОЛЬКО известные ключи разделов из реестра; никакого `eval`/`exec`; JSON через `json.loads`; непарсящийся/нерелевантный JSON → plain text. Разделы с отсутствующими ключами → "нет данных" (Task 2). |
| T-260921-04 | Denial of Service | `_parse_json_content` на недоверенном контенте | mitigate | Только линейные операции: `str.strip`, срез по `find("{")`/`rfind("}")`, `json.loads`. Без рекурсивных/катастрофических regex (Task 2). |
| T-260921-05 | Information Disclosure | `reasoning_content` в ответе модели | mitigate | Читать только `message["content"]`; `reasoning_content` не рендерить и не сохранять в `last_summary` (Task 2). |
| T-260921-06 | Information Disclosure | API-ключ в `app_config.json` plaintext | accept | Локальное desktop-приложение, поведение существует с Phase 3 и не входит в объём задачи; хранение в OS keychain — отдельная задача. |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Реестр пресетов + персист llm.summary_preset (контракт)</name>
  <files>app_config.py, main.py</files>
  <action>
    Этот таск фиксирует КОНТРАКТ (реестр пресетов + класс ошибки + методы сохранения), который реализуют Task 2 и Task 3.

    **app_config.py** — одна правка: в `DEFAULT_CONFIG["llm"]` добавить ключ `"summary_preset": "free",` (после `"enabled"`). Больше НИЧЕГО не менять: существующие циклы `setdefault` в `load_config` и `save_config` уже дают обратно-совместимый backfill для старых конфигов. НЕ дублировать список ID пресетов в app_config.py — единственный источник истины это `main.SUMMARY_PRESETS`.

    **main.py** — модульные константы сразу после импортов (перед `class TranscriptionEngine`):

    ```python
    DEFAULT_PRESET = "free"

    SUMMARY_PRESETS = {
        "daily": {
            "label": "Дейли",
            "title": "ДЕЙЛИ",
            "schema_name": "daily_conspect",
            "sections": [
                {"key": "tasks", "title": "ЗАДАЧИ", "kind": "list"},
                {"key": "decisions", "title": "РЕШЕНИЯ", "kind": "list"},
                {"key": "blockers", "title": "БЛОКЕРЫ", "kind": "list"},
            ],
        },
        "lecture": {
            "label": "Лекция",
            "title": "ЛЕКЦИЯ",
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
            "schema_name": None,
            "sections": [],
        },
    }
    ```

    Порядок ключей dict = порядок в Combobox (daily, lecture, interview, client, free). ASCII-ключи разделов выбраны осознанно: они работают и в `json_schema`, и в `json_object` слое; русские заголовки берутся из `title` при рендере.

    **main.py** — в модуле (рядом с константами) добавить класс ошибки API, чтобы Task 2 мог различать коды:
    ```python
    class SummaryApiError(RuntimeError):
        """Ошибка обращения к LLM API. `code` — HTTP-статус, 0 — сетевая ошибка, None — некорректный/пустой ответ (провал слоя)."""
        def __init__(self, message: str, code: int | None = None) -> None:
            super().__init__(message)
            self.code = code
    ```
    Наследование от `RuntimeError` осознанное: существующие `_run_summary`/UI ловят `Exception`, а `summarize` умеет пробрасывать терминальные ошибки без потери кода (`_is_layer_failure` в Task 2).

    **main.py** — `SummarizationEngine.__init__`: после `self.config = app_config.load_config()` добавить чтение и валидацию пресета (T-260921-01):
    ```python
    preset = self.config.get("llm", {}).get("summary_preset", DEFAULT_PRESET)
    if preset not in SUMMARY_PRESETS:
        preset = DEFAULT_PRESET
    self.preset = preset
    ```
    `self.progress_queue` оставить как есть.

    **main.py** — добавить метод `set_preset(self, preset_id: str) -> None`: валидировать `preset_id` по `SUMMARY_PRESETS` (неизвестный → `DEFAULT_PRESET`), присвоить `self.preset`, записать в `self.config["llm"]["summary_preset"]` (через `self.config.setdefault("llm", {})[...] = ...`) и вызвать `app_config.save_config(self.config)`.

    **main.py** — исправить `update_config`: сейчас он заменяет `self.config["llm"]` четырьмя ключами и затрёт пресет. В новый dict добавить `"summary_preset": self.preset`. Сигнатуру (4 параметра) и порядок ключей не менять — её вызывает `open_settings`/`save_settings`.

    Ничего не удалять и не переименовывать в существующем коде; `summarize` в этом таске ещё не трогаем.
  </action>
  <verify>
    <automated>Создать `C:\Users\898F~1\AppData\Local\Temp\opencode\q1_presets.py` (не в репозитории), запустить `py -3` из `A:\Repos\Echo`:

    ```python
    import json, os, sys, app_config, main
    F = lambda m: (print("FAIL:", m), sys.exit(1))
    assert list(main.SUMMARY_PRESETS) == ["daily", "lecture", "interview", "client", "free"], "order"
    assert main.SUMMARY_PRESETS["daily"]["sections"][0]["key"] == "tasks"
    assert main.SUMMARY_PRESETS["free"]["schema_name"] is None
    cfg = app_config.load_config()
    assert cfg["llm"]["summary_preset"] == "free", cfg["llm"].get("summary_preset")
    e = main.SummarizationEngine()
    key = cfg["llm"]["api_key"]
    e.set_preset("daily")
    saved = json.load(open(app_config.CONFIG_PATH, encoding="utf-8"))
    assert saved["llm"]["summary_preset"] == "daily", saved["llm"].get("summary_preset")
    assert saved["llm"]["api_key"] == key, "api_key lost on set_preset"
    e.update_config(api_key=key, base_url=e.config["llm"]["base_url"], model=e.config["llm"]["model"], enabled=e.config["llm"]["enabled"])
    saved = json.load(open(app_config.CONFIG_PATH, encoding="utf-8"))
    assert saved["llm"]["summary_preset"] == "daily", "update_config wiped preset"
    assert saved["llm"]["api_key"] == key, "api_key lost"
    e.set_preset("nonsense"); assert e.preset == "free", e.preset
    e.set_preset("free")
    saved = json.load(open(app_config.CONFIG_PATH, encoding="utf-8"))
    assert saved["llm"]["summary_preset"] == "free", "restore failed"
    assert isinstance(main.SummaryApiError("x", 400).code, int)
    print("OK task1")
    ```
    Скрипт ОБЯЗАН вернуть файл конфига в `summary_preset = "free"` (последний `set_preset("free")`). После прогона — удалить временный скрипт.
    Дополнительно: `py -3 -m py_compile main.py app_config.py</automated>
  </verify>
  <done>
    `SUMMARY_PRESETS` содержит 5 пресетов в порядке daily/lecture/interview/client/free с залоченными разделами; `app_config.DEFAULT_CONFIG["llm"]["summary_preset"] == "free"`; существующий app_config.json получает ключ через backfill без потери api_key/base_url/model; `set_preset` и `update_config` сохраняют ключ в файл и не затирают друг друга; неизвестный пресет приводит к `free`; конфиг возвращён в `free`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Слоистый fallback json_schema -> json_object -> plain text + рендер JSON в разделы</name>
  <files>main.py</files>
  <behavior>
    Случаи 1–10 и 13 проверяются с подменённым `SummarizationEngine._post_chat` (без сети). Случаи 11–12 дополнительно проверяются на РЕАЛЬНОМ `_post_chat` с подменённым `urllib.request.urlopen` (часть B в `<verify>`), потому что пустой `content` и `reasoning_content` живут внутри data-path самого `_post_chat`.

    1. free: payload НЕ содержит ключ `response_format`; результат = сырой `content`.
    2. daily: payload содержит `response_format["type"] == "json_schema"`, `json_schema["name"] == "daily_conspect"`, `json_schema["strict"] is True`, `schema["required"] == ["tasks","decisions","blockers"]`, `schema["additionalProperties"] is False`; типы: список → `{"type":"array","items":{"type":"string"}}`.
    3. 200 + чистый JSON `{"tasks":["a"],"decisions":["b"],"blockers":[]}` → текст содержит заголовки `ЗАДАЧИ`, `РЕШЕНИЯ`, `БЛОКЕРЫ` и строку `• a`; пустой список → `нет данных`; заголовок содержит `ДЕЙЛИ` и НЕ содержит слова `КОНСПЕКТ` (двойной заголовок в .txt исключён — INFO 5).
    4. 200 + JSON в ```json-ограждении → парсится и рендерится (ровно 1 вызов API).
    5. 200 + не-JSON текст ("Вот конспект: ...") → второй вызов уже с `response_format["type"] == "json_object"`; если он вернул валидный JSON → рендер (итого 2 вызова).
    6. `json_schema` вернул `SummaryApiError(code=400)` → второй вызов с `json_object`; успех → рендер (итого 2 вызова, первый с json_schema, второй с json_object). То же для `code=422`.
    7. `json_object` тоже провалился (400/422, ЛИБО пустой content, ЛИБО не-JSON) → третий вызов БЕЗ `response_format`, результат = сырой текст (итого 3 вызова; каждый payload проверен).
    8. ТЕРМИНАЛЬНЫЕ ошибки: первый слой бросает `SummaryApiError` с `code` из {401, 403, 429, 500, 0} → исключение пробрасывается наружу как `SummaryApiError` (подкласс `RuntimeError`), повторных вызовов НЕТ (итого 1 вызов на каждый код). Для `free` — то же самое (ошибка уходит из единственного вызова).
    9. JSON без единого известного ключа (`{"foo":"bar"}`) → JSON считается непригодным → переход на следующий слой (не рендерится как разделы).
    10. JSON-список (`[1,2]`) вместо объекта → непригоден → следующий слой.
    11. Провал слоя по пустому ответу: пустой/пробельный `content` (reasoning-модель при truncation) и неожиданная форма ответа (`choices: []`, нет `message.content`) дают `SummaryApiError(code=None)` и классифицируются как ПРОВАЛ СЛОЯ (`_is_layer_failure` → True), а НЕ как ошибка пользователю:
        11a. слой 1 (json_schema) → `code=None` → второй вызов с `json_object`; успех → рендер (итого 2 вызова);
        11b. слой 1 и слой 2 оба вернули пустой content → третий вызов без `response_format` вернул нормальный текст → результат = сырой текст (итого 3 вызова);
        11c. все три слоя пусты (сценарий 11 на реальном `_post_chat`: `content: ""` + `finish_reason: "length"`) → `SummaryApiError` с `code is None` пробрасывается наружу (итого 3 вызова) — показывать пользователю нечего.
    12. `reasoning_content` игнорируется внутри `_post_chat`: ответ с `message = {"content": "<валидный JSON>", "reasoning_content": "SECRET_REASONING"}` → `_post_chat` возвращает РОВНО строку `content` (без reasoning), а `summarize(text, "daily")` возвращает рендер, в котором НЕТ подстроки `SECRET_REASONING`; при этом `Authorization` ушёл в headers, и api_key НЕ попал в `messages`.
    13. Все разделы пресета отсутствуют/пусты по отдельности, но хотя бы один ключ присутствует → рендерятся все 4 (или 3) заголовка, у пустых — `нет данных`.
  </behavior>
  <action>
    Реализовать в `SummarizationEngine` (main.py) стек слоёв и рендер. `start_summary` / `_run_summary` / формат queue-сообщений НЕ менять — UI полагается на `summary_status` / `summary_complete` / `summary_error`.

    1. `_post_chat(self, payload: dict) -> str` — единственное место с сетью. Как текущий код: `urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={Content-Type, Authorization: Bearer <api_key>}, method="POST")`, `urlopen(..., timeout=60)`, `json.loads(resp.read().decode("utf-8"))`. Ошибки: `urllib.error.HTTPError` → `raise SummaryApiError(f"Ошибка API ({e.code}): {detail[:500]}", code=e.code)`; `urllib.error.URLError` → `raise SummaryApiError(f"Сетевая ошибка: {e.reason}", code=0)`; отсутствие `choices[0].message.content` → `raise SummaryApiError("Неожиданный ответ от API.", code=None)`. Извлечь строку `content` из `message`, и если `content.strip()` пуст → `raise SummaryApiError("Пустой ответ от API.", code=None)`. **Читать только `message["content"]`; `reasoning_content` не трогать (T-260921-05).** В сообщения об ошибках не попадают api_key и полный ответ (T-260921-02).

       `code=None` здесь означает ПРОВАЛ СЛОЯ (ответ пустой или не той формы), а НЕ терминальную ошибку: сам `_post_chat` лестницу не реализует, решение «повторять или остановиться» принимает `summarize` через `_is_layer_failure` (шаг 8). Никакого `RuntimeError` внутри `_post_chat` — только `SummaryApiError`, чтобы код не терялся (INFO 4).

    2. `_json_schema_format(preset: dict) -> dict | None` (static) — `None`, если `schema_name is None`; иначе
       `{"type": "json_schema", "json_schema": {"name": preset["schema_name"], "strict": True, "schema": {"type": "object", "properties": {...}, "required": [...], "additionalProperties": False}}}`,
       где для каждого раздела `properties[key] = {"type": "array", "items": {"type": "string"}}` при `kind == "list"`, иначе `{"type": "string"}`; `required` = все ключи в порядке `sections`.

    3. `_json_instruction(preset: dict) -> str` — текст для json_object-слоя:
       ```
       Верни ТОЛЬКО JSON-объект без markdown-ограждений и пояснений со следующими ключами:
         "tasks": массив строк — ЗАДАЧИ
         "decisions": массив строк — РЕШЕНИЯ
         ...
       ```
       («массив строк» для `kind == "list"`, «строка» для `kind == "text"`).

    4. `_build_messages(self, preset: dict, text: str, json_mode: str | None) -> list[dict]` — базовое system-сообщение `"Ты — ассистент для создания конспектов аудио."`; при `json_mode is not None` дописать к нему `" Отвечай строго в формате JSON, без markdown-ограждений."`. User-сообщение: инструкция по пресету (для `free` — ТЕКУЩИЙ текст промпта из существующего `summarize` дословно: «Составь краткий конспект следующей транскрипции аудио: выдели основные темы и ключевые идеи.»), при `json_mode is not None` — дополнительно `_json_instruction(preset)`; далее `"Пиши на языке исходного аудио."` и `f"\n\nТРАНСКРИПЦИЯ:\n{text}"`. Для не-free пресетов в инструкции явно назвать тип конспекта (дейли / лекция / интервью / встреча с клиентом) — взять из `title`, но без капса: добавить в реестр ключи не требуется, достаточно сформировать фразу вида `f"Составь конспект ({preset['title'].lower()})..."`. **Если фраза выглядит криво на капсе — разрешено добавить в реестр поле `"hint"` с человекочитаемым названием типа конспекта (например `"дейли-встречи"`), но НЕ менять ключи/разделы/порядок пресетов.**

    5. `_parse_json_content(content: str) -> dict | None` (static) — вернуть `dict` или `None`. Порядок: `s = content.strip()`; снять ограждение, если начинается с ``` (```json / ```): взять текст после первой строки и до последнего ```; попробовать `json.loads`; при неудаче — `start = s.find("{")`, `end = s.rfind("}")`, если `start != -1 and end > start` → `json.loads(s[start:end+1])`; все исключения (`json.JSONDecodeError`, `ValueError`, `TypeError`) → `None`. Вернуть `None`, если результат не `isinstance(parsed, dict)` (T-260921-03, T-260921-04 — только линейные операции, без regex).

    6. `_render_sections(preset: dict, data: dict) -> str | None` (static) — `None`, если НИ ОДИН `section["key"]` не присутствует в `data` (признак непригодного JSON). Иначе собрать строки в порядке `sections`:
       ```
       ========================================
       {preset['title']}
       ========================================

       {title}
         • {item}          # kind == "list": по строке на элемент, "  • " префикс, элементы через str()
       {title}
       {paragraph}         # kind == "text": значение как есть, без буллетов, многострочное ок
       ```
       Внутренний заголовок содержит ТОЛЬКО `{preset['title']}` (например `ДЕЙЛИ`) и НЕ содержит слова «КОНСПЕКТ»: `save_transcription_txt` уже добавляет блок `======\nКОНСПЕКТ\n======`, иначе в .txt получится двойной заголовок (INFO 5 из ревью).
       Разделы соединять через `"\n\n"`. Пустое/отсутствующее значение, пустой список или список только из пустых строк → `  — нет данных —` (для `kind == "text"` — `— нет данных —` без отступа). Неизвестные ключи из `data` игнорировать (защита от инъекции в разметку).

    7. `_request_content(self, preset: dict, text: str, response_format: dict | None) -> str` — собрать `payload = {"model": llm["model"], "messages": self._build_messages(preset, text, mode), "temperature": 0.3}` (`mode` = `response_format["type"]` или `None`); добавить `payload["response_format"] = response_format` ТОЛЬКО если он не `None`; вернуть `self._post_chat(payload)`. **НЕ выставлять `max_tokens`** (reasoning-модель уходит в reasoning и отдаёт пустой content).

    8. Переписать `summarize(self, text: str, preset_id: str | None = None) -> str` — лестница. Классификация «провал слоя vs терминальная ошибка» живёт РОВНО в одном месте:

       ```python
       @staticmethod
       def _is_layer_failure(exc: "SummaryApiError") -> bool:
           """True, если ошибку можно вылечить следующим слоем."""
           if exc.code is None:          # пустой/неожиданный ответ -> провал слоя
               return True
           if exc.code in (400, 422):    # провайдер не принял response_format -> провал слоя
               return True
           return False                  # 401/403/429/5xx/сеть(0)/прочее -> терминальная
       ```

       Плюс маленький хелпер, чтобы проверка «JSON пригоден» не дублировалась:
       ```python
       def _try_render(self, preset: dict, content: str | None) -> str | None:
           """None, если контента нет или JSON непригоден; иначе отрендеренные разделы."""
           if content is None:
               return None
           data = self._parse_json_content(content)
           if data is None:
               return None
           return self._render_sections(preset, data)
       ```

       Сам `summarize`:
       - `preset = SUMMARY_PRESETS.get(preset_id or self.preset) or SUMMARY_PRESETS[DEFAULT_PRESET]` (значение из аргумента тоже валидируется — T-260921-01).
       - Оставить проверку `if not self.is_configured(): raise RuntimeError("LLM API не настроен. Откройте настройки и укажите ключ API.")`.
       - `if preset["schema_name"] is None:` → `return self._request_content(preset, text, None)` (слой free, БЕЗ `response_format`; терминальная ошибка уезжает наверх как `SummaryApiError`).
       - **Слой 1 (`json_schema`):**
         `try: c1 = self._request_content(preset, text, self._json_schema_format(preset))`
         `except SummaryApiError as e: if not self._is_layer_failure(e): raise` (терминальная — повторных вызовов нет); `c1 = None`.
         `r = self._try_render(preset, c1); if r is not None: return r` — иначе идём на слой 2. Сюда попадают ВСЕ провалы слоя 1: 400/422, `code=None` (пустой `content` / неожиданная форма) и непригодный JSON.
       - **Слой 2 (`json_object`):**
         `try: c2 = self._request_content(preset, text, {"type": "json_object"})`
         `except SummaryApiError as e: if not self._is_layer_failure(e): raise`; `c2 = None`.
         `r = self._try_render(preset, c2); if r is not None: return r`.
       - **Слой 3 (plain text, гарантированный финал):** `return self._request_content(preset, text, None)` — сырой текст. Пустой `content` на этом слое НЕ перехватывается: показывать пользователю нечего, `SummaryApiError("Пустой ответ от API.")` доедет до `_run_summary` как обычная `RuntimeError`-совместимая ошибка.
       - Итог: структурированный пресет всегда возвращает либо отрендеренные разделы, либо plain text; исключение пользователю показывается ТОЛЬКО при терминальной ошибке (401/403/429/5xx/сеть). Ошибки между слоями не превращаются в `RuntimeError(str(e))` — наверх уходит исходный `SummaryApiError` (INFO 4), поэтому `code` не теряется.

    Обновить докстринг `summarize` (описать лестницу слоёв). Добавить/поправить комментарии-пояснения рядом с нетривиальными местами (почему терминальные коды не ретраятся, почему провал слоя ими не считается, почему `max_tokens` не задаётся, почему игнорируется `reasoning_content`).
    INFO 3 из ревью (риск-концентрация Task 2): таск оставлен единым — split не даёт выигрыша, потому что весь риск (`_post_chat` + `_is_layer_failure`) уже изолирован и покрыт частью B `<verify>`; дробление разорвало бы пары «слой → проверка».
  </action>
  <verify>
    <automated>Создать `C:\Users\898F~1\AppData\Local\Temp\opencode\q2_layers.py` (вне репозитория) и запустить `py -3` из `A:\Repos\Echo`. Скрипт состоит из ДВУХ частей.

    **Часть A — лестница слоёв (patch `_post_chat`, без сети).** `from unittest.mock import patch`; фабрика `engine()` — `main.SummarizationEngine()` с подменёнными `config["llm"]` (`api_key="test"`, `base_url="http://x/v1"`, `model="m"`, `enabled=True`); фейковый `_post_chat(payload)`, который пишет `payload` в общий список `calls` и возвращает/бросает по заранее заданному сценарию (`content` из `route(payload)` или `main.SummaryApiError(msg, code=...)`).
    Проверить случаи 1–10 и 13 из `<behavior>`; для каждого — отдельный сценарий и `assert`; проверять и число вызовов, и `calls[i]["response_format"]` (для слоя 3 — отсутствие ключа `response_format`). Отдельно проверить, что терминальные коды (401/403/429/500/0 → `SummaryApiError`) дают РОВНО 1 вызов и исключение `main.SummaryApiError` (не `RuntimeError(str(e))`): `except main.SummaryApiError as e: assert e.code == <код>`.

    **Часть B — реальный `_post_chat` (patch `urllib.request.urlopen`), случаи 11 и 12.** Здесь `_post_chat` НЕ подменяется — иначе `reasoning_content` и его guard'ы не проверяются:
    ```python
    import json
    from unittest.mock import patch

    RESP = [None]          # мутабельный холдер: fake_urlopen возвращает json.dumps(RESP[0])
    REQS = []              # сюда складываются urllib Request-объекты

    class FakeResp:        # контекстный менеджер, как у http.client.HTTPResponse
        def __init__(self, body: str): self._b = body.encode("utf-8")
        def read(self): return self._b
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        REQS.append(req)
        return FakeResp(json.dumps(RESP[0], ensure_ascii=False))

    eng = main.SummarizationEngine()
    eng.config["llm"] = {"api_key": "KEY123", "base_url": "http://x/v1", "model": "m", "enabled": True}
    payload = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}

    # --- 12: content + reasoning_content ---
    RESP[0] = {"choices": [{"finish_reason": "stop", "message": {
        "content": '{"tasks":["a"],"decisions":["b"],"blockers":[]}',
        "reasoning_content": "SECRET_REASONING"}}]}
    REQS.clear()
    with patch("urllib.request.urlopen", fake_urlopen):
        raw = eng._post_chat(payload)
        summary = eng.summarize("транскрипция", "daily")
    assert raw == '{"tasks":["a"],"decisions":["b"],"blockers":[]}', raw          # только content
    assert "SECRET_REASONING" not in raw
    assert "SECRET_REASONING" not in summary, "reasoning leaked into summary"
    assert "ЗАДАЧИ" in summary and "• a" in summary
    assert "КОНСПЕКТ" not in summary, "double header"                             # INFO 5
    assert len(REQS) == 1, len(REQS)                                              # json_schema сработал
    sent = json.loads(REQS[0].data.decode("utf-8"))
    assert "KEY123" not in json.dumps(sent["messages"], ensure_ascii=False), "api_key in messages"
    assert "KEY123" in (REQS[0].get_header("Authorization") or ""), "Authorization header lost"

    # --- 11c: пустой content -> код None, а не терминальная ошибка ---
    RESP[0] = {"choices": [{"finish_reason": "length", "message": {
        "content": "", "reasoning_content": "SECRET_REASONING"}}]}
    try:
        with patch("urllib.request.urlopen", fake_urlopen):
            eng._post_chat(payload)
        F("11c: empty content must raise SummaryApiError")
    except main.SummaryApiError as e:
        assert e.code is None, e.code
        assert main.SummarizationEngine._is_layer_failure(e) is True, "empty content must be a layer failure"

    # --- неожиданная форма ответа -> код None ---
    for bad in ([], {"choices": [{"message": {}}]}, {"choices": [{"message": {"reasoning_content": "R"}}]}):
        RESP[0] = bad if isinstance(bad, dict) else {"choices": bad}
        try:
            with patch("urllib.request.urlopen", fake_urlopen):
                eng._post_chat(payload)
            F("bad shape must raise SummaryApiError")
        except main.SummaryApiError as e:
            assert e.code is None, e.code

    # --- 11c end-to-end: все три слоя отдают пустой content -> ошибка после 3 вызовов ---
    RESP[0] = {"choices": [{"finish_reason": "length", "message": {"content": "   ", "reasoning_content": "R"}}]}
    REQS.clear()
    try:
        with patch("urllib.request.urlopen", fake_urlopen):
            eng.summarize("транскрипция", "daily")
        F("11c: expected SummaryApiError when every layer is empty")
    except main.SummaryApiError as e:
        assert e.code is None, e.code
    assert len(REQS) == 3, len(REQS)
    assert "response_format" in json.loads(REQS[0].data.decode("utf-8"))          # json_schema
    assert json.loads(REQS[1].data.decode("utf-8"))["response_format"]["type"] == "json_object"
    assert "response_format" not in json.loads(REQS[2].data.decode("utf-8"))      # plain text
    ```
    Все ошибки печатать как `FAIL: <случай>` + `sys.exit(1)` (ASCII), успех — `print("OK task2")`. Скрипт не должен делать сетевых вызовов (оба patch обязательны).
    Дополнительно: `py -3 -c "import main; print('IMPORT OK')"` и `py -3 -m py_compile main.py`. Удалить временный скрипт после прогона.</automated>
  </verify>
  <done>
    Все 13 поведений проходят (включая под-случаи 8, 11a–11c и 12, где 11/12 проверяются на РЕАЛЬНОМ `_post_chat` с подменённым `urlopen`); `summarize` для структурированного пресета делает 1 вызов при рабочем `json_schema`, 2 вызова при 400/422 / пустом `content` / не-JSON, 3 вызова как последний рубеж; слой 3 и пресет `free` уходят без `response_format`; терминальные ошибки (401/403/429/5xx/сеть=0) пробрасываются наружу как `SummaryApiError` без повторов, а провалы слоя (`code in {None, 400, 422}`) лестницу НЕ прерывают; пустой `content` не рендерится, `reasoning_content` не попадает в результат; внутренний заголовок не дублирует «КОНСПЕКТ»; `start_summary`/`_run_summary`/queue-контракт не изменены.
  </done>
</task>

<task type="auto">
  <name>Task 3: Combobox выбора пресета в SYSTEM STATUS + связка с движком и конфигом</name>
  <files>main.py</files>
  <action>
    Только UI-связка. Логику `summarize` не трогать.

    1. В `_build_ui` в блоке `status_panel` — между паковкой `self.settings_btn` (`.pack(... pady=(0, 6))`) и созданием `self.summary_btn` — вставить:
       - `self.preset_labels = {p["label"]: pid for pid, p in SUMMARY_PRESETS.items()}` (строится ОДИН раз здесь; порядок ключей = порядок пресетов);
       - `tk.Label(status_panel, text="SUMMARY PRESET", font=("Consolas", 8, "bold"), fg=self.muted_color, bg=self.panel_color).pack(anchor="w", padx=14, pady=(0, 2))`;
       - `self._configure_combobox_style()` (см. п.2);
       - `self.preset_var = tk.StringVar(value=SUMMARY_PRESETS[self.summarizer.preset]["label"])`;
       - `self.preset_combo = ttk.Combobox(status_panel, textvariable=self.preset_var, values=list(self.preset_labels.keys()), state="readonly", width=24, style="Echo.TCombobox", font=("Consolas", 9))` + `.pack(anchor="w", padx=14, pady=(0, 10))`;
       - `self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_change)`.
       Размеры/отступы подобрать так, чтобы панель не «прыгала» относительно `unit_panel` при `window 900x650` (Combobox шириной ~24 символа, те же `padx=14`, что у соседних виджетов).

    2. Добавить метод `_configure_combobox_style(self) -> None`: `style = ttk.Style()`; `try: style.theme_use("clam")` `except tk.TclError: pass`; `style.configure("Echo.TCombobox", fieldbackground=self.panel_dark, background=self.panel_dark, foreground=self.text_color, arrowcolor=self.accent_color)`; `style.map("Echo.TCombobox", fieldbackground=[("readonly", self.panel_dark)], foreground=[("readonly", self.text_color)], selectbackground=[("readonly", self.panel_dark)], selectforeground=[("readonly", self.text_color)])`. Это косметика в тёмной индустриальной палитре; при сбое темы интерфейс обязан продолжить работать (никаких исключений наружу).

    3. Добавить метод `on_preset_change(self, event=None) -> None`: взять `label = self.preset_var.get()`; `preset_id = self.preset_labels.get(label, DEFAULT_PRESET)`; `self.summarizer.set_preset(preset_id)`; обновить статус: `self.status_label.configure(text=f"PRESET // {SUMMARY_PRESETS[preset_id]['title']}")`. Никаких сетевых вызовов и перезапуска конспекта — только сохранение выбора.

    4. НЕ менять: `generate_summary` (движок сам знает пресет через `self.summarizer.preset`), `_handle_summary_complete`, `save_transcription_txt`, `_build_save_buttons`, `open_settings`. Сохранение выбора в файл происходит внутри `set_preset` (Task 1). Рендер → `last_summary` → .txt уже обеспечен Task 2 (решение пользователя №4/№5).
  </action>
  <verify>
    <automated>Создать `C:\Users\898F~1\AppData\Local\Temp\opencode\q3_ui.py` (вне репозитория), запустить `py -3` из `A:\Repos\Echo`:
    ```python
    import json, sys, tkinter as tk, app_config, main
    F = lambda m: (print("FAIL:", m), sys.exit(1))
    r = tk.Tk(); r.withdraw()
    app = main.TranscriberApp(r)
    cb = getattr(app, "preset_combo", None)
    assert cb is not None, "no preset_combo"
    assert str(cb.cget("state")) == "readonly", cb.cget("state")
    assert list(cb.cget("values")) == ["Дейли","Лекция","Интервью","Клиент","Свободный"], list(cb.cget("values"))
    assert app.preset_var.get() == "Свободный", app.preset_var.get()
    assert app.summarizer.preset == "free"
    app.preset_var.set("Дейли"); app.preset_combo.event_generate("<<ComboboxSelected>>"); r.update()
    assert app.summarizer.preset == "daily", app.summarizer.preset
    saved = json.load(open(app_config.CONFIG_PATH, encoding="utf-8"))
    assert saved["llm"]["summary_preset"] == "daily", "not persisted"
    app.preset_var.set("Свободный"); app.on_preset_change()
    saved = json.load(open(app_config.CONFIG_PATH, encoding="utf-8"))
    assert saved["llm"]["summary_preset"] == "free", "restore failed"
    r.destroy(); print("OK task3")
    ```
    Плюс smoke отрисовки: `py -3 -c "import tkinter as tk, main; r=tk.Tk(); r.withdraw(); main.TranscriberApp(r); r.destroy(); print('UI OK')"`.
    Плюс регресс-проверка контракта экспорта: `py -3 -c "import main; print(hasattr(main.TranscriberApp,'save_transcription_txt'), hasattr(main.TranscriberApp,'_handle_summary_complete'))"` → `True True`.
    Плюс `py -3 -m py_compile main.py app_config.py`. Удалить временный скрипт после прогона.</automated>
  </verify>
  <done>
    Combobox присутствует в `status_panel`, readonly, содержит ровно 5 пресетов в порядке Дейли/Лекция/Интервью/Клиент/Свободный, стартует со значения из конфига; выбор пресета меняет `summarizer.preset` и пишет `llm.summary_preset` в app_config.json; `free` восстанавливается; приложение строится headless без исключений; `save_transcription_txt` и обработчики конспекта не изменены.
  </done>
</task>

</tasks>

<verification>
Порядок проверок (все команды запускать из `A:\Repos\Echo` через `py -3`; временные скрипты — в `C:\Users\898F~1\AppData\Local\Temp\opencode\`, вне репозитория):

1. `py -3 -m py_compile main.py app_config.py` — синтаксис.
2. Скрипт Task 1 — реестр + персист + backfill (конфиг возвращён в `free`).
3. Скрипт Task 2 — 13 поведений лестницы слоёв и рендера (часть A — patch `_post_chat`; часть B — patch `urllib.request.urlopen` для случаев 11/12; ни одного реального сетевого вызова).
4. Скрипт Task 3 — Combobox + персист выбора (конфиг возвращён в `free`).
5. Отсутствие регрессов: `python -c` проверки из Task 3 + `py -3 -c "import main; print('IMPORT OK')"`.
6. Состояние конфига после всех прогонов: `llm.summary_preset == "free"`, `api_key`/`base_url`/`model`/`enabled` не изменены (сравнить с исходными значениями: `deepseek-v4.1-flash`, `https://api.dslab.tech/v1`, `enabled: true`).

Живой сетевой E2E (опционально, только по запросу пользователя): один вызов через новый `summarize` с пресетом `daily` — ожидаем заголовки `ЗАДАЧИ` / `РЕШЕНИЯ` / `БЛОКЕРЫ` (json_schema-слой подтверждён эмпирически 2026-09-21). Не включать в обязательную проверку: зависит от квоты и сети.
</verification>

<success_criteria>
- `ttk.Combobox` (readonly) с 5 пресетами живёт в `status_panel` рядом с GENERATE SUMMARY; стартовое значение берётся из `app_config.json`.
- У daily/lecture/interview/client своя JSON-схема и свои разделы; `free` работает как раньше и не отправляет `response_format`.
- `json_schema` → (400/422, пустой/неожиданный ответ или непригодный JSON) → `json_object` → (неудача) → plain text; иных повторов нет; терминальные ошибки (401/403/429/5xx/сеть) показываются пользователю сразу, без повторов.
- Провал слоя по пустому `content` (`code=None`) НЕ показывается пользователю, пока следующий слой даёт результат; `reasoning_content` никогда не рендерится и не попадает в `last_summary`; в .txt нет двойного заголовка «КОНСПЕКТ».
- Отрендеренный текст попадает в окно вывода и в `self.last_summary`, поэтому `SAVE .TXT` с блоком КОНСПЕКТ работает без правок.
- Выбранный пресет сохраняется в `llm.summary_preset` и не затирается сохранением API-настроек; старые конфиги получают дефолт `free`.
- Изменены ТОЛЬКО `main.py` и `app_config.py`; `ROADMAP.md` и `REQUIREMENTS.md` не тронуты.
</success_criteria>

<output>
After completion, create `.planning/quick/260921-ofx-combobox-system-status-json-response-for/260921-ofx-SUMMARY.md`
</output>
