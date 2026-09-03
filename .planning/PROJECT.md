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

### Active

- [ ] Индикатор прогресса и статус во время обработки
- [ ] Сохранение результатов в .txt и .srt форматах
- [ ] Автоматическое использование GPU при наличии

### Out of Scope

- Выбор языка — автоопределение достаточно для v1
- Перевод на английский — не требуется
- Выбор модели — фиксированная модель base
- Формат .vtt и .json — не нужны

## Context

Python приложение с tkinter GUI, использующее библиотеки whisper и torch. Адресовано пользователям, которым нужно быстро получить текст из аудиозаписей.

## Constraints

- **Tech stack**: Python, tkinter, whisper, torch
- **Platform**: Desktop (Windows/macOS/Linux)
- **Model**: Фиксированная модель base
- **Formats**: Только .txt и .srt

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Минималистичный интерфейс | Простота использования | ✓ Good |
| Фиксированная модель base | Баланс скорости и качества | ✓ Good |
| Только автоопределение языка | Упрощение интерфейса | ✓ Good |
| Два формата вывода | txt для текста, srt для субтитров | — Pending |
| Queue-based threading pattern | Prevents tkinter crashes from background threads | ✓ Good |
| Lazy model loading | Delays expensive whisper model load until first use | ✓ Good |

---
*Last updated: 2026-09-03 after Phase 2 completion*

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
