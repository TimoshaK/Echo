# Phase 6: Refactor main.py into echo package - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Разбить монолитный `main.py` (1467 строк) на пакет `echo/` с подпакетом `echo/ui/`, не меняя поведение приложения.

Целевая структура (залочена в ROADMAP.md):
```
main.py                      # тонкий лаунчер
app_config.json              # остаётся в корне
echo/__init__.py
echo/config.py               # бывший app_config.py
echo/presets.py              # DEFAULT_PRESET, SUMMARY_PRESETS
echo/errors.py               # SummaryApiError + map_transcription_error()
echo/llm_client.py           # HTTP POST, messages, schema/instruction, parse/render
echo/srt.py                  # time_to_srt(), build_srt_content()
echo/transcription_engine.py # TranscriptionEngine
echo/summarization_engine.py # SummarizationEngine
echo/ui/__init__.py
echo/ui/theme.py             # палитра COLORS
echo/ui/build.py             # build_ui/build_save_buttons/configure_combobox_style (функции от app)
echo/ui/settings_dialog.py   # open_settings(app)
echo/ui/app.py               # TranscriberApp (состояние, обработчики, polling, actions)
```

**Не входит в scope:** новые фичи, изменение UI/логики, переезд конфига в `%APPDATA%`, удаление неиспользуемых зависимостей, смена движка транскрибации.

</domain>

<decisions>
## Implementation Decisions

### Миграция и совместимость конфига
- **D-01:** Корневой `app_config.py` **удаляется**. Его содержимое переносится в `echo/config.py`. `CONFIG_PATH` явно переякоривается на корень репозитория: `Path(__file__).resolve().parent.parent / "app_config.json"`. Это критично: наивный перенос файла уводит `CONFIG_PATH` в `echo/` и молча ломает REFR-03 (ключ API перестаёт читаться).
- **D-02:** `app_config.json` **остаётся в корне репозитория**. Расположение файла с API-ключом не меняется; существующий ключ должен читаться после рефактора.

### Стратегия миграции
- **D-03:** Миграция **поэтапная**: сначала не-GUI слой (`config`, `presets`, `errors`, `llm_client`, `srt`, `transcription_engine`, `summarization_engine`) → зелёные проверки → затем GUI (`theme`, `build`, `settings_dialog`, `app`) → `main.py` лаунчер → финальная проверка.
- **D-04:** Незакоммиченная правка `ЗАДАЧИ → AFD` в `SUMMARY_PRESETS["daily"]["sections"][0]["title"]` **коммитится отдельным коммитом ДО начала рефактора**, чтобы `HEAD` совпадал с базлайном поведения. Значение `AFD` сохраняется как есть (осознанное решение пользователя).
- **D-05:** Критерий «зелёного» состояния на каждом шаге — **полный smoke-набор**:
  1. `py -3 -m py_compile` всех затронутых модулей
  2. импорт пакета/модулей без ошибок
  3. headless-сборка GUI: `tk.Tk(); root.withdraw(); TranscriberApp(root)` без исключений
  4. no-network харнесс `summarize()` (патч `urllib.request.urlopen`/`_post_chat`) — лестница слоёв работает
  5. проверка, что корневой `app_config.json` читается и API-ключ на месте

### the agent's Discretion
- **Тесты:** отдельный `tests/` пакет НЕ добавляем (вне выбранных областей, избегаем scope creep). Поведение страхуется transient smoke-скриптами по D-05.
- **Точки входа:** `main.py` остаётся тонким лаунчером (`from echo.ui.app import ...`); допускается добавить `echo/__main__.py`, чтобы работал `python -m echo`. Реэкспорты `from main import ...` НЕ добавляются.
- **Упаковка:** `main.spec` (gitignored) допускается обновить (`hiddenimports=['echo']`), но это не блокер.
- **Разбиение `_build_ui` (471 строка):** допускается разложить на логические билдер-функции (header/input/processing/output/footer) внутри `echo/ui/build.py`.
- **`srt.py`:** туда переносятся только чистые функции (`time_to_srt`, `build_srt_content`); методы сохранения с `filedialog`/`messagebox` остаются в `echo/ui/app.py`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Планирование и требования
- `.planning/ROADMAP.md` §Phase 6 — цель, критерии успеха, целевая структура
- `.planning/REQUIREMENTS.md` — REFR-01, REFR-02, REFR-03
- `.planning/STATE.md` — текущее состояние и Roadmap Evolution

### Базлайн кода (что переносим)
- `main.py` — монолит-источник (1467 строк), рабочая копия = базлайн (включая `AFD`)
- `app_config.py` — конфиг (40 строк), подводный камень `CONFIG_PATH`

### Смежное (не менять в этой фазе)
- `.planning/phases/05-packaging-distribution/05-RESEARCH.md` — заметки про `CONFIG_PATH`/PyInstaller и переезд в `%APPDATA%` (отложено)
- `requirements.txt` — неиспользуемый `srt` (отложено)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app_config.load_config()/save_config()` — переносятся в `echo/config.py` без изменения логики (setdefault-backfill, normalize).
- `SUMMARY_PRESETS` + `DEFAULT_PRESET` — реестр пресетов, единственный источник истины; переносится как есть.
- `SummaryApiError` + `_is_layer_failure` — контракт ошибок слоёв; переносится в `errors.py`/`llm_client.py`.

### Established Patterns
- Thread + `queue.Queue` + `root.after(100, ...)` для апдейтов GUI — сохранить без изменений.
- Ленивая загрузка модели whisper (`TranscriptionEngine.load_model`).
- Единственная точка сети — `_post_chat`; контракты очередей `status/complete/error` и `summary_status/summary_complete/summary_error` неизменны.
- ttk-стиль `Echo.TCombobox` + `theme_use("clam")`.

### Integration Points
- Точка входа: `main.py` → `TranscriberApp(root)`.
- `TranscriberApp` использует `SUMMARY_PRESETS`, `DEFAULT_PRESET`, `TranscriptionEngine`, `SummarizationEngine`.
- Направление зависимостей: `ui → engines → (presets/errors/llm_client/config)`. Циклов быть не должно.

</code_context>

<specifics>
## Specific Ideas

- `CONFIG_PATH` в `echo/config.py` обязан указывать на **корневой** `app_config.json` (`Path(__file__).resolve().parent.parent / "app_config.json"`), чтобы REFR-03 выполнялся.
- `AFD` — намеренное значение заголовка раздела tasks в daily-пресете; не «исправлять» на `ЗАДАЧИ`.
- `main.py` не должен содержать реэкспортов — «чистая структура».

</specifics>

<deferred>
## Deferred Ideas

- Переезд конфига в `%APPDATA%/Echo/config.json` с миграцией — относится к Phase 5 (Packaging & Distribution).
- Удаление неиспользуемой зависимости `srt` из `requirements.txt` — Phase 5.
- Переход на `faster-whisper` (убирает FFmpeg-зависимость) — отдельная будущая фаза.
- Постоянный `tests/` пакет (pytest/unittest) — отдельная фаза качества, если потребуется.

</deferred>

---

*Phase: 06-refactor-main-into-echo-package*
*Context gathered: 2026-09-21*
