# Whisper Transcriber

## What This Is

Приложение с графическим интерфейсом для транскрипции аудиофайлов с помощью модели Whisper от OpenAI. Простой и удобный инструмент для преобразования аудио в текст.

## Core Value

Быстрая и точная транскрипция аудиофайлов в удобном интерфейсе с сохранением результатов в читаемых форматах.

## Requirements

### Validated

- ✓ Выбор аудиофайла через стандартный диалог — Phase 1
- ✓ Отображение пути выбранного файла — Phase 1
- ✓ Запуск транскрипции одной кнопкой — Phase 2
- ✓ Обработка в отдельном потоке (без зависания GUI) — Phase 2
- ✓ Обработка ошибок с выводом сообщений — Phase 2
- ✓ Генерация конспекта через подключаемый LLM (OpenRouter) — Phase 3
- ✓ Выбор типа конспекта (пресеты дейли/лекция/интервью/клиент/свободный) + JSON response_format — Phase 3 / quick 260921-ofx
- ✓ Сохранение результатов в .txt и .srt (с таймкодами) — Phase 4
- ✓ Рефакторинг монолита в пакет `echo/` (config, presets, errors, llm_client, srt, engines, ui/) без изменения поведения — Phase 6
- ✓ Security hardening: права 0600 + атомарная запись `app_config.json`, https-only `base_url`, отсечение `Authorization` при cross-origin редиректе, явная ошибка при повреждённом конфиге, санитизация ошибок API, пины зависимостей — Phase 7
- ✓ Supply-chain hardening: полностью зафиксированный lock зависимостей с хэшами (pip-tools), CPU + CUDA варианты torch, локальный гайд `pip-audit` — Phase 8

### Active

- [ ] Индикатор прогресса во время обработки (сейчас только текстовый статус)
- [ ] Автоматическое использование GPU при наличии
- [ ] Упаковка и распространение (документация зависимостей + standalone .exe) — Phase 5 запланирована

### Out of Scope

- Выбор языка — автоопределение достаточно для v1
- Перевод на английский — не требуется
- Выбор модели — фиксированная модель base
- Формат .vtt и .json — не нужны

## Context

Python-приложение с tkinter GUI (пакет `echo/`, тонкий лаунчер `main.py`), использующее whisper + torch для локальной транскрипции и опциональный конспект через подключаемый OpenAI-совместимый LLM (по умолчанию OpenRouter). Настройки API хранятся в корневом `app_config.json`. Адресовано пользователям, которым нужно быстро получить текст из аудиозаписей.

## Constraints

- **Tech stack**: Python, tkinter, whisper, torch
- **Platform**: Desktop (Windows/macOS/Linux)
- **Model**: Фиксированная модель base
- **Formats**: Только .txt и .srt
- **Structure**: пакет `echo/`; `main.py` — тонкий лаунчер без реэкспортов
- **Config**: `app_config.json` в корне репозитория (не коммитится)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Минималистичный интерфейс | Простота использования | ✓ Good |
| Фиксированная модель base | Баланс скорости и качества | ✓ Good |
| Только автоопределение языка | Упрощение интерфейса | ✓ Good |
| Два формата вывода | txt для текста, srt для субтитров | ✓ Good |
| Queue-based threading pattern | Prevents tkinter crashes from background threads | ✓ Good |
| Lazy model loading | Delays expensive whisper model load until first use | ✓ Good |
| Подключаемый LLM-провайдер (OpenAI-совместимый, по умолчанию OpenRouter) | Независимость от конкретного вендора, конфиг по ключу | ✓ Good |
| Пресеты конспекта со своими JSON-схемами через response_format + слоистый fallback | Структурированный вывод и совместимость с разными моделями | ✓ Good |
| Пакет `echo/` вместо монолита `main.py` | Читаемость, разделение слоёв, тестируемость | ✓ Good |
| `CONFIG_PATH` привязан к корню репозитория | Сохраняет существующий `app_config.json` при переносе модуля | ✓ Good |
| `base_url` только `https://` | Предотвращает отправку API-ключа по открытому каналу | ✓ Good |
| Отсечение `Authorization` при cross-origin редиректе | Защита ключа от слива через редирект | ✓ Good |
| Секреты не пишутся в UI/логи (санитизация ошибок) | Снижает риск утечки ключа в диалогах | ✓ Good |
| Тесты на stdlib `unittest` (без pytest) | Ноль новых зависимостей в фазе пиннинга | ✓ Good |
| Полный lock зависимостей с хэшами (pip-tools), CPU + CUDA варианты | Воспроизводимость и защита от supply-chain (подмена/вредоносная версия) | ✓ Good |
| CUDA-lock через seed из CPU-lock + `--reuse-hashes` | Обходит массовую загрузку CUDA-колёс и `OSError(28)` | ✓ Good |

---
*Last updated: 2026-09-23 after Phase 8 completion*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
