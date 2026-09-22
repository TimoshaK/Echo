---
created: 2026-09-22T06:41:17.320Z
title: Consider Docker for headless CLI batch transcription
area: general
files: []
---

## Problem

Docker не подходит для текущего desktop-GUI приложения (tkinter) — вывод окна в контейнере требует хрупкого проброса X11/Wayland (особенно на Windows), диалоги выбора файлов показывают пути контейнера вместо хоста, CUDA требует nvidia-container-toolkit, и образ получается многогигабайтным (torch ~3 ГБ). Пользователю всё равно пришлось бы ставить Docker — хуже, чем нативный `.exe`.

Однако Docker мог бы быть уместен, если у проекта появится headless/CLI-режим или серверная раздача.

## Solution

TBD — рассмотреть только при добавлении CLI-энтрипоинта (батч-транскрипция). Варианты:

- `/gsd-add-phase "CLI batch transcription"` — новый CLI-энтрипоинт (`py -3 -m echo.cli --file x.mp3 --out y.txt`), который затем можно контейнеризировать.
- Dockerfile на базе python-slim + ffmpeg + CPU-only torch; монтирование входной/выходной директории как volume.
- Использовать как альтернативу PyInstaller для Linux-серверов, а не для desktop-раздачи.

Текущее решение (Phase 5): распространять через PyInstaller (standalone) + встроенный FFmpeg, без Docker.
