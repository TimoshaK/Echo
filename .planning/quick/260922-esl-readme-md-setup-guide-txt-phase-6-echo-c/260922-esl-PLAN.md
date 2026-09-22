---
phase: quick-260922-esl
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [README.md, SETUP_GUIDE.txt]
autonomous: true
requirements: [REFR-01, REFR-02]
must_haves:
  truths:
    - "README.md описывает конспект через подключаемую LLM (OpenRouter) и 5 пресетов (Дейли/Лекция/Интервью/Клиент/Свободный), не теряя авторский тон"
    - "README.md показывает ветку суммирования (Transcription → SummarizationEngine → OpenRouter) отдельно от локальной транскрибации"
    - "README.md содержит актуальное дерево проекта с пакетом echo/ и подпакетом echo/ui/ и раздел Configuration про app_config.json + API SETTINGS"
    - "README.md в Installation требует FFmpeg отдельным шагом и использует py / py -3 (алиас python сломан); Run показывает py -3 main.py и py -3 -m echo"
    - "README.md честно раскрывает приватность: опциональный конспект отправляет ТЕКСТ транскрипции в OpenRouter, аудио остаётся локальным"
    - "SETUP_GUIDE.txt ссылается на echo/config.py (CONFIG_PATH → корневой app_config.json), а не на удалённый app_config.py"
    - "SETUP_GUIDE.txt описывает пакет echo/ и точку входа py -3 -m echo; заметка про build/dist/main.spec говорит, что dist/ собран из старого монолита и требует пересборки"
    - "Поведение приложения не меняется — изменены только README.md и SETUP_GUIDE.txt"
  artifacts:
    - path: "README.md"
      provides: "Features/How it works/Architecture/Tech Stack/Installation/Run/Project structure/Configuration/Privacy/Roadmap под Phase 6"
    - path: "SETUP_GUIDE.txt"
      provides: "Актуальные инструкции: echo/config.py CONFIG_PATH, FFmpeg, echo/ tree, py -3 -m echo, stale dist/"
  key_links:
    - from: "README.md:Installation"
      to: "FFmpeg install step"
      via: "winget/choco/scoop + PATH"
      pattern: "FFmpeg"
    - from: "README.md:Architecture"
      to: "echo/ package layout"
      via: "echo/ + echo/ui/ tree"
      pattern: "echo/ui/"
    - from: "SETUP_GUIDE.txt:section 3 / 8"
      to: "py -3 -m echo"
      via: "echo/__main__.py"
      pattern: "py -3 -m echo"
    - from: "SETUP_GUIDE.txt:section 7"
      to: "echo/config.py CONFIG_PATH"
      via: "Path(__file__).resolve().parent.parent / 'app_config.json'"
      pattern: "app_config.json"
---

<objective>
Актуализировать README.md и SETUP_GUIDE.txt под рефактор Phase 6: структура пакета `echo/` (config, presets, errors, llm_client, srt, engines, ui/), конспект через OpenRouter + пресеты, сохранение `.txt`/`.srt`, FFmpeg в установке, `app_config.json` в корне, privacy-раскрытие LLM-конспекта.

Purpose: документация сейчас описывает монолитный `main.py`, не упоминает конспект/пресеты, не содержит обязательного шага FFmpeg и ссылается на удалённый модуль `app_config.py`. После рефактора Phase 6 это вводит читателя в заблуждение.

Output: обновлённые README.md и SETUP_GUIDE.txt. Другие файлы НЕ создаются и НЕ меняются (docs-only, поведение неизменно).
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
@$HOME/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/06-refactor-main-into-echo-package/06-CONTEXT.md

# ОБЯЗАТЕЛЬНО прочитать перед правкой:
@README.md
@SETUP_GUIDE.txt
@main.py
@echo/config.py
@echo/presets.py
@echo/__main__.py

## Решения пользователя (ЗАЛОЧЕНЫ — не пересматривать)

1. **Scope = ТОЛЬКО README.md и SETUP_GUIDE.txt.** НЕ создавать новые доки (никаких ARCHITECTURE.md / GETTING-STARTED.md / CONFIGURATION.md) и НЕ запускать широкий docs-pipeline. `files_modified` строго `[README.md, SETUP_GUIDE.txt]`.
2. **README правится хирургически / in-place**, сохраняя авторский голос, порядок и tone (русский, `*`-bullets, ASCII-диаграммы, таблицы). НЕ регенерировать с нуля.
3. Exact edit list для **README.md**: Features (конспект + пресеты + JSON + сохранение + API SETTINGS), How it works (ветка суммирования), Architecture (`SummarizationEngine`, `llm_client`, `echo/`, `echo/ui/`), Tech Stack (LLM/OpenRouter на stdlib `urllib.request`, без новых зависимостей; `srt` — declared-but-unused), Installation (обязательный FFmpeg; `py`/`py -3`), Run (`py -3 main.py` и `py -3 -m echo`; где лежит `app_config.json`), Project structure (дерево `echo/`), Privacy (текст уходит в OpenRouter, аудио — локально), Roadmap (отметить конспект/пресеты/сохранение/улучшение архитектуры), новая секция Configuration.
4. Exact edit list для **SETUP_GUIDE.txt**: `app_config.py` → `echo/config.py` с `CONFIG_PATH`, переякоренным на корень репозитория; заметка про `build/`/`dist/`/`main.spec` (dist/ собран из СТАРОГО монолита и stale, нужна пересборка, размеры build ~150 MB, dist ~3 GB); добавить дерево пакета `echo/` и точку входа `py -3 -m echo`.
5. **Поведение не меняется** — это docs-only задача. Меняются только README.md и SETUP_GUIDE.txt.

## Verified facts (из кода этого репозитория)

- `main.py` — 15 строк, `from echo.ui.app import TranscriberApp`, `main()`.
- `echo/__main__.py` существует → работает `py -3 -m echo`.
- `echo/config.py`: `CONFIG_PATH = Path(__file__).resolve().parent.parent / "app_config.json"`.
- `echo/config.py:DEFAULT_CONFIG["llm"]` = `api_key=""`, `base_url="https://openrouter.ai/api/v1"`, `model="openai/gpt-4o-mini"`, `enabled=False`, `summary_preset="free"`.
- `echo/presets.py`: `DEFAULT_PRESET = "free"`; `SUMMARY_PRESETS` = daily(Дейли) / lecture(Лекция) / interview(Интервью) / client(Клиент) / free(Свободный).
- Пакет: `echo/{__init__,__main__,config,presets,errors,llm_client,srt,transcription_engine,summarization_engine}.py` + `echo/ui/{__init__,theme,build,settings_dialog,app}.py`.

## Ограничения окружения

- Запуск/проверки Python: `py -3` (алиас `python` сломан). `py -3 -m py_compile` для компиляции.
- PowerShell портит кириллицу; в проверочных скриптах печатать только ASCII и ставить `$env:PYTHONIOENCODING="utf-8"`.
- Проверки — offline-греп по документам. Сетевых вызовов нет.

<interfaces>
<!-- Ключевые факты, нужные для точной правки текста. Использовать напрямую. -->

Актуальное дерево проекта (для README «Project structure» и SETUP_GUIDE нового раздела):
```text
Echo/
│
├── main.py                    # тонкий лаунчер (15 строк)
├── app_config.json            # конфиг: API-ключ, base URL, модель, пресет — в КОРНЕ
├── requirements.txt
├── README.md
├── SETUP_GUIDE.txt
├── echo/
│   ├── __init__.py
│   ├── __main__.py            # точка входа py -3 -m echo
│   ├── config.py              # CONFIG_PATH → корневой app_config.json
│   ├── presets.py             # DEFAULT_PRESET, SUMMARY_PRESETS
│   ├── errors.py              # SummaryApiError, map_transcription_error()
│   ├── llm_client.py          # HTTP POST, messages, schema/instruction, parse/render
│   ├── srt.py                 # time_to_srt(), build_srt_content()
│   ├── transcription_engine.py
│   ├── summarization_engine.py
│   └── ui/
│       ├── __init__.py
│       ├── theme.py           # палитра COLORS
│       ├── build.py           # построение виджетов (функции от app)
│       ├── settings_dialog.py # диалог API SETTINGS
│       └── app.py             # TranscriberApp (состояние, потоки, polling)
└── .planning/
```

Пресеты (label → id): Дейли→daily, Лекция→lecture, Интервью→interview, Клиент→client, Свободный→free.
Дефолт: preset `free`, base_url `https://openrouter.ai/api/v1`, model `openai/gpt-4o-mini`.
</interfaces>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| README/SETUP_GUIDE → читатель | Документация может ввести пользователя в заблуждение о приватности или установке |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260922-01 | Information Disclosure | README Privacy / SETUP_GUIDE FAQ «конспект» | mitigate | Явно указать, что опциональный конспект отправляет ТЕКСТ транскрипции в OpenRouter, а аудио остаётся локальным; транскрибация — всегда локальная (Task 1). |
| T-260922-02 | Spoofing (misconfiguration) | README Installation / SETUP_GUIDE install | mitigate | Обязательный шаг FFmpeg с проверкой `ffmpeg -version`; `py`/`py -3` вместо сломанного `python` (Task 1, Task 2). |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Хирургически обновить README.md под Phase 6</name>
  <files>README.md</files>
  <action>
    Править README.md IN-PLACE, сохраняя авторский голос, порядок секций, `*`-bullets, ASCII-диаграммы, таблицы и язык (русский). НЕ регенерировать файл. Все правки — по залоченному списку ниже (пункты 1–1 соответствуют решению 3).

    1. **Features** — добавить в список после существующих пунктов:
       - Конспект транскрипции через подключаемую LLM (OpenRouter)
       - Пресеты конспекта: Дейли / Лекция / Интервью / Клиент / Свободный
       - Структурированный вывод конспекта (JSON-схема с рендером в читаемые разделы)
       - Диалог **API SETTINGS** для ключа/URL/модели и выбора пресета
       - Сохранение результата в `.txt` и `.srt`

    2. **How it works** — дополнить ASCII-диаграмму второй (опциональной) веткой. После `OpenAI Whisper → текст` добавить ветвление: основной путь остаётся локальным, а опционально текст уходит в `SummarizationEngine` → `llm_client` → `OpenRouter`. Добавить подраздел `### Summarization flow` (по образцу существующего `### Transcription flow`): пользователь нажимает **GENERATE SUMMARY** с выбранным пресетом → `SummarizationEngine` формирует запрос → `llm_client` делает HTTP POST в OpenRouter → ответ рендерится в разделы → результат кладётся в GUI и сохраняется вместе с транскрипцией. Сохранить существующее описание `queue.Queue`/потоков.

    3. **Architecture** — расширить: добавить `SummarizationEngine` (лестница слоёв запроса: `json_schema → json_object → plain text`, терминальные ошибки не ретраятся), `llm_client` (единственная точка сети, сборка messages, парсинг/рендер JSON), и уточнить, что код разбит на пакет `echo/` с подпакетом `echo/ui/`: `echo/ui/app.py` (`TranscriberApp`), `echo/ui/build.py`, `echo/ui/theme.py`, `echo/ui/settings_dialog.py`; движки `echo/transcription_engine.py` и `echo/summarization_engine.py`; листовые модули `echo/config.py`, `echo/presets.py`, `echo/errors.py`, `echo/srt.py`. Сохранить существующее описание ленивой загрузки модели и `threading.Lock`.

    4. **Tech Stack** — в таблицу добавить строку LLM: Purpose «Конспект (конспект через OpenRouter)», примечание в тексте ниже, что используется стандартная библиотека `urllib.request` — **новых зависимостей нет**. Строку `srt` пометить как **declared, but unused** (пакет в `requirements.txt` есть, код его не импортирует; `.srt` формируется вручную). Не удалять строку.

    5. **Installation** — добавить ОБЯЗАТЕЛЬНЫЙ шаг FFmpeg (сейчас отсутствует). Переименовать/дополнить шаги: после установки зависимостей идёт «Install FFmpeg (system binary, not pip)» с командами `winget install "FFmpeg (Essentials Build)"` / `choco install ffmpeg` / `scoop install ffmpeg`, ручным вариантом (распаковать сборку и добавить `bin` в PATH) и проверкой `ffmpeg -version`. В шагах с venv/pip на Windows использовать `py -3` вместо `python` (алиас `python` сломан): `py -3 -m venv .venv`, `.venv\Scripts\activate`. Linux/macOS-ветку (`python3`) можно оставить.

    6. **Run** — заменить `python main.py` на `py -3 main.py`; рядом указать альтернативу `py -3 -m echo`. Добавить строку, что `app_config.json` создаётся/читается в **корне репозитория**. Сохранить пронумерованный сценарий работы в GUI.

    7. **Project structure** — заменить устаревшее дерево (`main.py`, `requirements.txt`, `AGENTS.md`, `.planning/`, `README.md`) на актуальное дерево из блока `<interfaces>`. Убрать фразу «Основная логика приложения в текущей версии находится в `main.py`» и заменить на «`main.py` — тонкий лаунчер; логика в пакете `echo/`».

    8. **Configuration** — добавить НОВУЮ секцию (после `Project structure` или рядом с `Run`): описать `app_config.json` в корне репозитория и его ключи `llm.api_key`, `llm.base_url` (дефолт `https://openrouter.ai/api/v1`), `llm.model` (дефолт `openai/gpt-4o-mini`), `llm.enabled`, `llm.summary_preset`; описать диалог **API SETTINGS** и пресеты. Стиль — как у остальных секций.

    9. **Privacy** — расширить: транскрибация по-прежнему полностью локальная, аудио никуда не отправляется; **НО опциональный конспект (GENERATE SUMMARY) отправляет ТЕКСТ транскрипции в OpenRouter** (внешний LLM-провайдер). Если конспект не используется, ничего по сети не уходит (кроме первичного скачивания модели). Сохранить существующий абзац про скачивание модели.

    10. **Roadmap** — отметить выполненное: `[x] Конспект транскрипции через LLM (OpenRouter)`, `[x] Пресеты конспекта (дейли/лекция/интервью/клиент/свободный)`, сохранить `[x]` у сохранения `.txt`/`.srt`, и перевести `[ ] Улучшение архитектуры проекта` → `[x]`. Остальные пункты не трогать. При необходимости переформулировать существующую строку «Настройки приложения» отдельно НЕ трогать (в залоченном списке её нет).

    Запрещено: создавать новые .md файлы; менять код; переписывать секции целиком «с нуля» (только вставки/точечные правки); удалять секции License/Author/Whisper models/Error handling/Design goals.
  </action>
  <verify>
    <automated>Offline-греп по README.md (использовать `rg` или `Select-String`, кириллицу в выводе не печатать):

    Обязательно присутствует:
    - `rg -n "SummarizationEngine" README.md`
    - `rg -n "llm_client" README.md`
    - `rg -n "echo/ui/" README.md`
    - `rg -n "OpenRouter" README.md`
    - `rg -n "FFmpeg" README.md`
    - `rg -n "py -3 main\.py" README.md`
    - `rg -n "py -3 -m echo" README.md`
    - `rg -n "app_config\.json" README.md`
    - `rg -n "urllib\.request" README.md` (или явное утверждение «новых зависимостей нет»)
    - `rg -n "summary_preset" README.md` (секция Configuration)
    - `rg -n "## Configuration" README.md`

    Обязательно ОТСУТСТВУЕТ (устаревшее):
    - `rg -n "python main\.py" README.md` → пусто (допускается только `python3` в Linux/macOS-ветке venv)
    - `rg -n "Основная логика приложения в текущей версии находится в" README.md` → пусто
    - `rg -n "app_config\.py" README.md` → пусто
    - `rg -n "\[ \] Улучшение архитектуры проекта" README.md` → пусто (пункт отмечен)

    А также: `git diff --name-only` показывает РОВНО `README.md` и `SETUP_GUIDE.txt` (после Task 2), и `git diff --stat` не содержит изменений кода (`echo/`, `main.py`).</automated>
  </verify>
  <done>
    README.md описывает конспект/пресеты/JSON/API SETTINGS, ветку суммирования, `SummarizationEngine`+`llm_client` и пакет `echo/`+`echo/ui/`; Tech Stack содержит LLM-строку (stdlib `urllib.request`, без новых зависимостей) и помечает `srt` как declared-but-unused; Installation содержит обязательный FFmpeg-шаг и `py -3`; Run показывает `py -3 main.py` и `py -3 -m echo` и место `app_config.json`; дерево проекта актуальное; добавлена секция Configuration; Privacy раскрывает отправку ТЕКСТА в OpenRouter при конспекте (аудио локально); Roadmap отмечает конспект/пресеты/архитектуру. Авторский голос и структура сохранены.
  </done>
</task>

<task type="auto">
  <name>Task 2: Обновить SETUP_GUIDE.txt (echo/config.py, stale dist/, echo/ tree) + сквозная сверка</name>
  <files>SETUP_GUIDE.txt</files>
  <action>
    Править SETUP_GUIDE.txt IN-PLACE, сохраняя его plain-text box-стиль (`====` / `----` разделители, отступы, нумерацию секций) и русский язык. НЕ переписывать документ целиком. Правки по залоченному списку (решение 4):

    1. **Раздел 3 «КОМПОНЕНТ 1: PYTHON»**: строка «Написан на нём main.py» → «Написан на нём код в пакете `echo/`». Строку запуска `Запуск приложения:   py main.py` → `py -3 main.py` и добавить альтернативу `py -3 -m echo` (пояснить: пакет `echo/` имеет `__main__.py`). Сохранить существующее предупреждение про сломанный алиас `python` на этой машине и рекомендацию использовать `py`.

    2. **Раздел 4.1 openai-whisper**: фразу «библиотека вызывается из main.py» → «библиотека вызывается из `echo/transcription_engine.py`».

    3. **Раздел 7 «PyInstaller»**, пункт про КОНФИГ: заменить «сейчас `app_config.py` пишет файл рядом с кодом» на актуальное: модуль `echo/config.py`, а `CONFIG_PATH` переякорен на **корень репозитория** — `Path(__file__).resolve().parent.parent / "app_config.json"`. Сохранить вывод про onefile (`%APPDATA%\Echo\config.json` как рекомендация) — это по-прежнему верное замечание, просто привязать его к `echo/config.py`.

    4. **Раздел 7**, абзац про текущую сборку (сейчас: «Текущая сборка в репозитории (build/, dist/, main.spec) — черновая: весит ~3 ГБ, console=True, без FFmpeg и модели. Для раздачи не годится.»): уточнить, что `dist/` была собрана из **СТАРОГО монолитного `main.py`** и поэтому **stale** — её нужно **пересобрать** после рефактора в пакет `echo/` (в `main.spec` добавлен `hiddenimports=['echo']`). Указать размеры: `build/` ~150 МБ, `dist/` ~3 ГБ.

    5. **Новый раздел про структуру кода**: добавить секцию (например, «СТРУКТУРА КОДА: ПАКЕТ echo/» — разместить логично, перед разделом «ИСТОЧНИКИ» или после раздела 3) с деревом пакета `echo/` из блока `<interfaces>` и пояснением точки входа `py -3 -m echo`. Сохранить box-стиль и нумерацию соседних разделов (если вставляется нумерованная секция — перенумеровать аккуратно либо дать ей номер 11 перед ИСТОЧНИКАМИ).

    6. **Раздел 8, Сценарий A, шаг «Запуск»**: `py main.py` → `py -3 main.py` (и упомянуть `py -3 -m echo`). **Сценарий B** — то же: `py main.py` → `py -3 main.py`. Проверить весь файл на прочие `py main.py` и заменить на `py -3 main.py`.

    Запрещено: создавать новые файлы; менять код; ломать ASCII/box-разметку; удалять разделы 1–10 и блок ИСТОЧНИКИ (только точечные правки + одна новая секция).

    После правки SETUP_GUIDE — выполнить СКВОЗНУЮ сверку обоих документов: убедиться, что нигде не осталось `app_config.py` как модуля конфига, что оба документа согласованы по названию пакета, точке входа `py -3 -m echo`, пути `app_config.json` (корень) и роли FFmpeg. Если найдена остаточная несогласованность в README.md — точечно поправить её здесь же (README остаётся в `files_modified`).
  </action>
  <verify>
    <automated>Offline-греп по SETUP_GUIDE.txt:

    Обязательно присутствует:
    - `rg -n "echo/config\.py" SETUP_GUIDE.txt`
    - `rg -n "parent\.parent" SETUP_GUIDE.txt` (или явное упоминание «корень репозитория» рядом с `app_config.json`)
    - `rg -n "py -3 -m echo" SETUP_GUIDE.txt`
    - `rg -n "echo/" SETUP_GUIDE.txt` (дерево пакета)
    - `rg -n "150" SETUP_GUIDE.txt` и `rg -n "3 ГБ" SETUP_GUIDE.txt`
    - `rg -n "пересобрать|stale|СТАРОГО" SETUP_GUIDE.txt`

    Обязательно ОТСУТСТВУЕТ:
    - `rg -n "app_config\.py" SETUP_GUIDE.txt` → пусто
    - `rg -n "py main\.py" SETUP_GUIDE.txt` → пусто
    - `rg -n "вызывается из main\.py" SETUP_GUIDE.txt` → пусто

    Сквозная проверка обоих документов:
    - `rg -n "app_config\.py" README.md SETUP_GUIDE.txt` → пусто
    - `rg -n "py -3 -m echo" README.md SETUP_GUIDE.txt` → есть в обоих
    - `git diff --name-only` → РОВНО `README.md` и `SETUP_GUIDE.txt` (никаких других файлов)
    - `git diff --stat` → нет изменений в `.py` файлах

    Кодировка/структура: файл читается как UTF-8, разделители `====`/`----` сохранены — проверить `rg -c "^={10,}" SETUP_GUIDE.txt` (>0) и `rg -c "^----" SETUP_GUIDE.txt` (>0).</automated>
  </verify>
  <done>
    SETUP_GUIDE.txt ссылается на `echo/config.py` с `CONFIG_PATH` на корень репозитория (не на `app_config.py`); заметка про сборку говорит, что `dist/` собран из старого монолита и требует пересборки (`build/` ~150 МБ, `dist/` ~3 ГБ); добавлено дерево пакета `echo/` и точка входа `py -3 -m echo`; все запуски — `py -3 main.py`; box-разметка сохранена. Сквозная сверка подтверждает: `app_config.py` нигде не упоминается как модуль конфига, оба документа согласованы, изменены ровно два файла, код не тронут.
  </done>
</task>

</tasks>

<verification>
- `git diff --name-only` — ровно `README.md` и `SETUP_GUIDE.txt`.
- `git diff --stat` — нет изменений в `echo/**`, `main.py` или любых `.py`.
- Оба документа согласованы: `echo/` package, `py -3 -m echo`, `app_config.json` в корне, обязательный FFmpeg, privacy-раскрытие OpenRouter.
- Устаревшие ссылки отсутствуют: `python main.py`, `app_config.py` как модуль конфига, «логика в main.py».
</verification>

<success_criteria>
- README.md содержит все залоченные правки (решение 3), сохранив авторский голос и структуру.
- SETUP_GUIDE.txt содержит все залоченные правки (решение 4), сохранив plain-text box-стиль.
- Ни один другой файл не создан и не изменён (docs-only, поведение неизменно).
- Все проверки выше проходят offline, без сетевых вызовов.
</success_criteria>

<output>
After completion, create `.planning/quick/260922-esl-readme-md-setup-guide-txt-phase-6-echo-c/260922-esl-SUMMARY.md`
</output>
