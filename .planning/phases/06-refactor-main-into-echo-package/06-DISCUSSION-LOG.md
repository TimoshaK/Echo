# Phase 6: Refactor main.py into echo package - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 06-refactor-main-into-echo-package
**Areas discussed:** Миграция и совместимость конфига, Стратегия миграции

---

## Миграция и совместимость конфига

### Q1: Как поступить с корневым app_config.py при переносе в echo/config.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Удалить, переякорить CONFIG_PATH | Удалить корневой app_config.py; в echo/config.py CONFIG_PATH явно указывает на корневой app_config.json — ключ API не теряется | ✓ |
| Оставить shim на переход | Тонкий корневой app_config.py (`from echo.config import *`), удалить позже | |
| Перенести JSON в echo/ | Перенести сам app_config.json в echo/ (меняет расположение файла с ключом) | |

**User's choice:** Удалить, переякорить CONFIG_PATH
**Notes:** Наивный перенос файла уводит `CONFIG_PATH` в `echo/` и молча ломает REFR-03.

### Q2: Где должен лежать app_config.json после рефактора?

| Option | Description | Selected |
|--------|-------------|----------|
| Корень репозитория | `Path(__file__).parent.parent / "app_config.json"` — сохраняет текущее расположение | ✓ |
| Рядом с модулем | `echo/app_config.json` — проще, но ломает REFR-03 | |
| В %APPDATA% с миграцией | `%APPDATA%/Echo/config.json` + миграция старого файла (совет research Phase 5) | |

**User's choice:** Корень репозитория
**Notes:** Расположение файла с API-ключом не меняется; существующий ключ обязан читаться.

---

## Стратегия миграции

### Q3: Как проводить миграцию?

| Option | Description | Selected |
|--------|-------------|----------|
| Поэтапно: не-GUI → GUI | Сначала не-GUI слой → зелёные проверки → потом GUI → финал | ✓ |
| Один перенос | Весь перенос за раз, один коммит | |
| По модулю на коммит | Коммит на каждый модуль | |

**User's choice:** Поэтапно: не-GUI → GUI

### Q4: Как поступить с незакоммиченной правкой AFD в main.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Закоммитить AFD отдельно | Отдельным коммитом ДО рефактора, чтобы HEAD = базлайн поведения | ✓ |
| В первый коммит | Включить AFD в первый коммит рефактора | |
| Не коммитить | Оставить незакоммиченным — риск смешивания с диффом | |

**User's choice:** Закоммитить AFD отдельно
**Notes:** Значение `AFD` сохраняется как осознанное решение (не откатывать на `ЗАДАЧИ`).

### Q5: Какой критерий «зелёного» состояния на каждом шаге?

| Option | Description | Selected |
|--------|-------------|----------|
| Полный набор smoke | py_compile + импорт + headless GUI + no-network summarize + чтение app_config.json | ✓ |
| Минимум | Только py_compile + импорт | |

**User's choice:** Полный набор smoke

---

## the agent's Discretion

- Тесты: отдельный `tests/` пакет не добавляется; страховка — transient smoke-скрипты.
- Точки входа: `main.py` — тонкий лаунчер; допускается `echo/__main__.py`; реэкспорты не добавляются.
- Упаковка: `main.spec` допускается обновить (`hiddenimports=['echo']`), не блокер.
- Разбиение `_build_ui` на логические билдер-функции внутри `echo/ui/build.py`.
- `srt.py` — только чистые функции; методы сохранения остаются в `echo/ui/app.py`.

## Deferred Ideas

- Переезд конфига в `%APPDATA%` — Phase 5.
- Удаление неиспользуемой зависимости `srt` — Phase 5.
- Переход на `faster-whisper` — будущая фаза.
- Постоянный `tests/` пакет — отдельная фаза качества.
