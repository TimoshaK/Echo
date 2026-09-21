# Phase 5: Packaging & Distribution — Research

**Researched:** 2026-09-21
**Domain:** Desktop-приложение Python/tkinter + Whisper — распространение, зависимости, PyInstaller
**Confidence:** HIGH (по составу зависимостей и роли FFmpeg), MEDIUM (по размерам/оптимизации сборки), LOW (по macOS/Linux-пакетам)

> Фаза не имеет CONTEXT.md (каталог `05-packaging-distribution` пуст на момент исследования) — жёстких пользовательских ограничений из discuss-phase нет. Все решения ниже — рекомендации исследователя, требующие подтверждения на этапе планирования/обсуждения.

---

## Summary

Phase 5 — это фаза **документирования и упаковки**, а не написания функциональности. Приложение уже полностью работает (Phase 1–4 завершены). Требуется: (1) перечень ПО с источниками, (2) объяснение роли FFmpeg, (3) пошаговая инструкция установки, (4) возможность собрать standalone-исполняемый файл.

Ключевой вывод исследования: **приложению нужны ровно три «внешних» сущности, которых нет в самом репозитории** — интерпретатор Python, набор pip-пакетов (во главе с `openai-whisper`/`torch`) и **системный бинарник FFmpeg**. FFmpeg обязателен, потому что `openai-whisper` не содержит собственного декодера аудио: функция `whisper.audio.load_audio()` **запускает `ffmpeg` как внешний процесс** и получает от него сырой PCM. Без FFmpeg в `PATH` транскрибация падает ещё до обращения к нейросети.

Важное уточнение по вопросу пользователя «умеет ли FFmpeg транскрибировать»: **сам FFmpeg — это мультимедийный фреймворк (decode/encode/transcode/mux/filter/play), распознавания речи в нём нет**. Транскрибирует именно модель Whisper (нейросеть, работающая внутри Python/torch). FFmpeg лишь конвертирует контейнер/кодек/частоту дискретизации. Нюанс: с августа 2025 FFmpeg можно собрать с `libwhisper` (whisper.cpp) и тогда появляется аудиофильтр `whisper` — но это только в «full»-сборках, и **установленная в этом окружении сборка FFmpeg собрана с `--disable-whisper`**, то есть фильтра транскрибации в ней нет.

Отдельный практический риск: **текущая сборка PyInstaller уже создана, но непригодна для раздачи** — она весит **3 045 МБ** (torch 2.14.0+cu130 = 2 789 МБ), собрана в режиме `console=True`, не содержит ни FFmpeg, ни модели, а `app_config.py` пишет конфиг рядом с `__file__`, что в onefile-режиме означает потерю настроек (файл уходит в удаляемый `sys._MEIPASS`).

**Primary recommendation:** документировать **два независимых сценария** — (A) запуск из исходников (`py -m pip install -r requirements.txt` + системный FFmpeg) и (B) standalone-сборка **PyInstaller `--onedir`** с **CPU-only torch** (убирает ~2.5 ГБ CUDA), встроенным `ffmpeg.exe` и конфигом в `%APPDATA%\Echo\config.json`. Модель `base.pt` (138.5 МБ) — на выбор: встроить в бандл (`--add-data`) или скачивать при первом запуске.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DIST-01 | Перечень необходимого ПО/репозиториев с источниками для запуска на другом ПК | Раздел «Required Software & Sources»: таблица из 9 pip-пакетов + FFmpeg + Python, все с PyPI/GitHub/официальными URL; проверенные версии |
| DIST-02 | Объяснение роли FFmpeg и его аналогов в процессе транскрибации | Разделы «Why FFmpeg» (точный код `whisper/audio.py:load_audio`) и «FFmpeg vs Alternatives» (таблицы по декодерам и по ASR-движкам) |
| DIST-03 | Пошаговая инструкция установки и использования всего ПО | Раздел «Install & Usage Walkthrough»: сценарии «разработчик», «конечный пользователь из исходников», «конечный пользователь — exe», с командами и проверками |
| DIST-04 | Возможность сборки standalone-исполняемого файла (PyInstaller) | Раздел «PyInstaller Packaging Notes»: разбор текущей сборки, исправление config-пути, встраивание ffmpeg и модели, оптимизация размера, готовый spec |
</phase_requirements>

---

## Required Software & Sources (DIST-01)

### Что именно нужно скачать/установить

| # | Компонент | Тип | Версия (проверено 2026-09-21) | Источник | Роль |
|---|-----------|-----|-------------------------------|----------|------|
| 1 | **Python** | runtime | 3.10–3.12 (реком.); локально работает 3.14.3 | https://www.python.org/downloads/ | Интерпретатор, tkinter входит в stdlib |
| 2 | **FFmpeg** | системный бинарник | BtbN win64-gpl (`N-126390-g9fc8c785e2-20260902`) или gyan.dev release 9.0.2 | https://github.com/BtbN/FFmpeg-Builds , https://www.gyan.dev/ffmpeg/builds/ | **Декодирование/ресемплинг аудио** для whisper |
| 3 | **openai-whisper** | PyPI | `20250625` (latest) | https://pypi.org/project/openai-whisper/ | Движок ASR + загрузка модели |
| 4 | **torch** | PyPI | `2.14.0` (latest) | https://pypi.org/project/torch/ | Backend инференса нейросети |
| 5 | **numpy** | PyPI (транзитивно) | `2.5.3` (latest); установлено 2.4.4 | https://pypi.org/project/numpy/ | Числовые массивы (волновая форма) |
| 6 | **numba** | PyPI (транзитивно от whisper) | `0.67.0` | https://pypi.org/project/numba/ | JIT для `whisper.timing` |
| 7 | **llvmlite** | PyPI (транзитивно от numba) | `0.49.0` | https://pypi.org/project/llvmlite/ | LLVM-биндинги (114.8 МБ в бандле!) |
| 8 | **tiktoken** | PyPI (транзитивно от whisper) | `0.14.0` | https://pypi.org/project/tiktoken/ | Токенизатор |
| 9 | **more-itertools** | PyPI (транзитивно от whisper) | `11.1.0` | https://pypi.org/project/more-itertools/ | Утилиты |
| 10 | **tqdm** | PyPI (транзитивно от whisper) | `4.70.1` (установлено 4.70.0) | https://pypi.org/project/tqdm/ | Прогресс скачивания модели |
| 11 | **srt** | PyPI (объявлен, **не используется**) | `3.5.3` | https://pypi.org/project/srt/ | **В коде не импортируется** — SRT генерируется вручную в `main.py` |
| 12 | **PyInstaller** | dev-инструмент | `6.19.0` + `pyinstaller-hooks-contrib 2026.4` | https://pyinstaller.org/ | Сборка standalone |
| 13 | **Модель `base.pt`** | данные | 138.5 МБ (кэш локально) | https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt | Веса модели (скачивается автоматически) |

**Проверенные факты о зависимостях** `[VERIFIED: pip show / importlib.metadata]`:

```
Requires: more-itertools, numba, numpy, tiktoken, torch, tqdm
+ triton>=2; (platform_machine == "x86_64" and sys_platform == "linux") or sys_platform == "linux2"
```

То есть `numba`, `llvmlite`, `tiktoken`, `more-itertools` **не нужно ставить вручную** — они придут как зависимости `openai-whisper`. Но их **нужно указать в документации**, потому что именно они определяют вес бандла.

### Что реально импортирует приложение

`[VERIFIED: чтение main.py + проверка sys.modules после import whisper]`

`main.py` импортирует только: `json, os, queue, threading, tkinter, urllib.request, urllib.error, whisper, app_config`.
После `import whisper` в память подгружаются: `numba, llvmlite, tiktoken, tqdm, torch, numpy`.
**Не подгружаются:** `matplotlib`, `torchvision`, `PIL`, `srt`.

### Два важных расхождения в `requirements.txt`

1. **`numpy>=2.5.0`**, но в окружении установлен **2.4.4** `[VERIFIED: pip list]`. На чистой машине `pip install -r requirements.txt` подтянет 2.5.3 — совместимость с `numba 0.67.0` не проверена. Требует решения (пин или обновление окружения).
2. **`srt>=3.5.3` не используется кодом** — можно удалить из requirements или, наоборот, начать использовать. `tqdm` тоже не импортируется напрямую (приходит транзитивно от whisper).

### Источники FFmpeg для Windows (ключевая развилка)

| Источник | Ссылка | Плюсы | Минусы |
|----------|--------|-------|--------|
| **BtbN/FFmpeg-Builds** (GitHub Releases) | https://github.com/BtbN/FFmpeg-Builds/releases | Автосборки ежедневно, статический `.exe`, есть «latest» с постоянным URL, варианты `gpl`/`lgpl`/`nonfree`, MIT-лицензия на скрипты сборки | Нужен GitHub; полный архив ~100+ МБ |
| **gyan.dev** (CODEX FFMPEG) | https://www.gyan.dev/ffmpeg/builds/ | `essentials` = **34 МБ (7z) / 109 МБ (zip)** — достаточно для декодирования; доступен через `choco`/`scoop`/`winget`; есть `.sha256` | «Full» сборки GPLv3; ставить лучше git master |
| **Пакетные менеджеры** | `winget install ffmpeg`, `choco install ffmpeg`, `scoop install ffmpeg` | Проще всего для конечного пользователя | Требует наличия менеджера пакетов |

`[CITED: https://www.gyan.dev/ffmpeg/builds/]` — «If you're downloading a package to support features in a program like Krita or Blender, the **release essentials** build is sufficient». Для Echo достаточно **essentials** (нужен только декодер + resampler).

`[VERIFIED: локально]` Установленный `ffmpeg.exe` — **145.8 МБ**, лежит в `A:\python\Scripts\ffmpeg.exe` (рядом `ffprobe.exe`). По признакам конфигурации (`--prefix=/ffbuild/prefix`, `crosstool-NG`, `extra-version=20260902`, формат версии `N-<коммиты>-g<hash>-<дата>`, `--enable-gpl --enable-version3`) это **статическая сборка BtbN win64-gpl** (вывод: MEDIUM, по косвенным признакам).

---

## Why FFmpeg (DIST-02)

### Точный механизм: whisper запускает ffmpeg как subprocess

`[VERIFIED: локальный исходник A:\python\Lib\site-packages\whisper\audio.py, строки 25–62]`

```python
def load_audio(file: str, sr: int = SAMPLE_RATE):
    # This launches a subprocess to decode audio while down-mixing
    # and resampling as necessary.  Requires the ffmpeg CLI in PATH.
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", file,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),      # sr = SAMPLE_RATE = 16000
        "-"
    ]
    try:
        out = run(cmd, capture_output=True, check=True).stdout
    except CalledProcessError as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
```

### Что это значит по шагам

1. Пользователь выбирает, например, `lecture.mp3` (или `.m4a`, `.flac`, `.ogg`, `.webm`, `.wav`).
2. `model.transcribe(path)` → внутри вызывается `load_audio(path)`.
3. Python **порождает дочерний процесс** `ffmpeg`, который:
   - **демультиплексирует** контейнер (mp3/m4a/ogg/webm/flac/wav) → извлекает аудиопоток;
   - **декодирует** кодек (MP3/AAC/Opus/Vorbis/FLAC/PCM) в сырые сэмплы;
   - **даунмиксит** в моно (`-ac 1`);
   - **ресемплит** в **16 000 Гц** (`-ar 16000`) — это жёсткое требование модели Whisper;
   - **перекодирует** в знаковый 16-битный PCM (`-f s16le -acodec pcm_s16le`) и отдаёт в stdout.
4. Python читает stdout, превращает байты в `float32`-массив в диапазоне `[-1, 1]` (деление на 32768).
5. Дальше массив уходит в `log_mel_spectrogram()` → в нейросеть. **FFmpeg на этом шаге больше не нужен.**

Итого: **FFmpeg — это «входной шлюз» для аудио.** Модель Whisper умеет работать только с тензором моно-PCM 16 кГц; она физически не умеет открывать `.mp3`/`.m4a`/`.webm`.

### Что происходит без FFmpeg

- `subprocess.run(["ffmpeg", ...])` при отсутствии исполняемого файла бросает **`FileNotFoundError`** (не `CalledProcessError`).
- Исключение поднимается из фонового потока `_run_transcription` → попадает в `progress_queue` как `{"type": "error", "error": "<текст>"}`.
- В `main.py` (строки 1042–1051) есть попытка маппинга:
  ```python
  if "ffmpeg" in error_lower or "avconv" in error_lower:
      error_msg = "Не установлен ffmpeg. Установите ffmpeg и попробуйте снова."
  ```
  **Проблема:** на русскоязычной Windows сообщение `FileNotFoundError` выглядит как `[WinError 2] Не удалось найти указанный файл: 'ffmpeg'` — слово `ffmpeg` там есть (в кавычках), так что сработает; но на других локалях/в некоторых случаях (например, `NotADirectoryError`, ошибки PATH) текст может не содержать `ffmpeg`, и пользователь получит generic «Ошибка при обработке аудио». **Рекомендуется отдельная явная проверка `shutil.which("ffmpeg")` при старте** (см. Pitfalls).

### Почему FFmpeg не ставится через pip

`openai-whisper` объявляет FFmpeg как **системную зависимость**, а не Python-пакет. Официальный README прямо пишет:

`[CITED: https://github.com/openai/whisper]` — «It also requires the command-line tool `ffmpeg` to be installed on your system, which is available from most package managers». Далее приводятся: `sudo apt install ffmpeg`, `brew install ffmpeg`, `choco install ffmpeg`, `scoop install ffmpeg`.

Следствие для DIST-03: **инструкция обязана содержать отдельный шаг установки FFmpeg**, не сводящийся к `pip install`.

---

## FFmpeg vs Alternatives (DIST-02 / DIST-03)

### Вопрос 1: умеет ли FFmpeg транскрибировать?

**Нет.** Официальное определение:

`[CITED: https://www.ffmpeg.org/about.html]` — «FFmpeg is the leading **multimedia framework**, able to **decode, encode, transcode, mux, demux, stream, filter** and **play** pretty much anything that humans and machines have created… It contains libavcodec, libavutil, libavformat, libavfilter, libavdevice, libswscale and libswresample».

В этом списке **нет** speech-to-text / ASR. FFmpeg — про транспорт и формат медиа, не про распознавание речи.

**Нюанс (важно для корректности документации):** начиная с 2025-08-21 в «full»-сборках FFmpeg для Windows появилась поддержка транскрибации через **whisper.cpp**:

`[CITED: https://www.gyan.dev/ffmpeg/builds/ (changelog, build 055, 2025-08-21)]` — «added support for audio transcription using **whisper.cpp** to full builds». В списке библиотек full-сборки указан `whisper`.

Однако:
- это доступно **только в «full»-варианте**, не в «essentials»;
- `[VERIFIED: ffmpeg -buildconf]` **установленная в этом окружении сборка содержит `--disable-whisper`**, а `ffmpeg -filters` не содержит фильтра `whisper` → `ffmpeg -h filter=whisper` отвечает `Unknown filter 'whisper'`;
- то есть **Echo ни при каких обстоятельствах не полагается на транскрибацию внутри FFmpeg** — распознаёт Whisper-модель в Python.

Вывод для документации: «FFmpeg декодирует звук, Whisper распознаёт речь — это два разных этапа и два разных инструмента».

### Вопрос 2: аналоги FFmpeg именно как аудио-декодера

| Решение | Что это | Нужен системный FFmpeg? | Плюсы для Echo | Минусы / почему не сейчас |
|---------|---------|--------------------------|----------------|----------------------------|
| **FFmpeg CLI** (текущий) | внешний бинарник | **Да** | Поддерживает все форматы; zero-config для Python; то, что ожидает whisper из коробки | Нужен отдельный шаг установки; PATH-зависимость |
| **PyAV** | Python-биндинги к libav* | **Нет** — FFmpeg-библиотеки внутри wheel | Убирает внешнюю зависимость; именно так работает faster-whisper | Требует переписывания загрузки аудио; добавляет бинарный wheel ~30–50 МБ |
| **soundfile (libsndfile)** | чтение WAV/FLAC/OGG | Нет | Простой API | **Не читает MP3/AAC/M4A** в стандартной сборке → не покрывает форматы Echo |
| **librosa** | высокоуровневый аудиоанализ | Косвенно (через soundfile/audioread) | Удобный resample | Тяжёлая зависимость (scipy, numba, scikit-learn); для MP3 всё равно тянет ffmpeg/audioread |
| **torchaudio** | аудио в экосистеме torch | Частично (в новых версиях — через FFmpeg/sox) | Уже есть torch | Нестабильный API между версиями; на Windows исторически требует FFmpeg для mp3 |
| **pydub** | обёртка над ffmpeg | **Да** (всё равно вызывает ffmpeg) | Простой API | Не убирает зависимость, добавляет слой; фактически заброшен `[ASSUMED]` |
| **miniaudio** | один C-файл, декодирует mp3/flac/wav | Нет | Лёгкий; используется whisper.cpp | Нет поддержки m4a/aac/ogg-vorbis в базовом виде |

**Рекомендация:** оставить **FFmpeg CLI** (нулевые изменения кода, полное покрытие форматов, официально поддерживаемый whisper путь). Вариант с PyAV — кандидат на будущее, если критично убрать внешнюю зависимость.

### Вопрос 3: аналоги движка транскрибации

| Движок | Лицензия | Скорее всего лучше для | Плюсы | Минусы для Echo |
|--------|----------|------------------------|-------|------------------|
| **openai-whisper** (текущий) | MIT | Референсная реализация | Официальный, простой API `load_model/transcribe`, автоопределение языка, SRT-сегменты с таймкодами | Медленнее конкурентов, тянет torch (~2.8 ГБ с CUDA) |
| **faster-whisper** (CTranslate2) | MIT | Скорость и память | **До 4× быстрее** openai/whisper при той же точности; int8-квантизация; **системный FFmpeg НЕ нужен** (PyAV внутри) | Другой API (`WhisperModel`, генератор сегментов); требует cuBLAS/cuDNN 9 для GPU; `[CITED: pypi.org/project/faster-whisper]` |
| **whisper.cpp** | MIT | Максимально лёгкие сборки, offline, embedded | Без зависимостей (C/C++), CPU-only, квантование, модели 142 МБ (base) / ~388 МБ RAM, есть CLI `whisper-cli` | **CLI принимает только 16-бит WAV** — всё равно нужен ffmpeg для конвертации `[CITED: github.com/ggml-org/whisper.cpp]`; нужна сборка/готовый бинарник; Python-биндинги сторонние |
| **Vosk** | Apache-2.0 | Потоковое распознавание, очень лёгкие устройства | 20+ языков, **модели всего ~50 МБ**, offline, `pip3 install vosk`, streaming API | Точность ниже Whisper; другая модель/API; русская модель требует отдельной загрузки `[CITED: alphacephei.com/vosk]` |
| **wav2vec2 (HF transformers)** | Apache-2.0 | Исследования, тонкая настройка | Хорошая точность на чистом аудио | Нет «из коробки» таймкодов/мультиязычности как у Whisper; тяжёлый стек transformers |
| **Коммерческие API** (OpenAI, Deepgram, AssemblyAI, Google STT) | проприетарная | Максимальное качество без локальных ресурсов | Не нужен torch/GPU; простота | **Платно и требует интернет**; аудио уходит третьей стороне (приватность); противоречит offline-ценности приложения |

**Рекомендация для Phase 5:** движок **не менять**. `openai-whisper` уже интегрирован, покрывает требования (автоопределение языка, сегменты для SRT), а смена движка — это отдельная фаза с переписыванием `TranscriptionEngine`. Зафиксировать в документации раздел «Почему выбран openai-whisper и что можно рассмотреть в будущем» (faster-whisper — первый кандидат: и быстрее, и убирает FFmpeg-зависимость).

---

## Recommended Approach

### Стратегия: две документированные дорожки + одна сборка

| Дорожка | Кому | Что нужно на ПК | Ожидаемый объём |
|---------|------|-----------------|-----------------|
| **A. Из исходников** | разработчик / продвинутый пользователь | Python + `pip install -r requirements.txt` + системный FFmpeg | ~3–4 ГБ (если torch с CUDA) |
| **B. Standalone `.exe`** | конечный пользователь | Ничего (всё внутри папки) | ~400–600 МБ (CPU-only, оценка) |

### Решения, которые нужно зафиксировать (рекомендации)

| Вопрос | Рекомендация | Обоснование |
|--------|--------------|-------------|
| Формат сборки | **`--onedir`**, не `--onefile` | `onefile` распаковывает ~400 МБ–3 ГБ во временную папку при **каждом** запуске (десятки секунд) и ломает путь к конфигу/модели; `onedir` стартует мгновенно |
| Вариант torch | **CPU-only** для раздачи (PyPI-wheel), CUDA — опционально | PyPI-wheel `torch 2.14.0` для win_amd64 = **118.4 МБ** `[VERIFIED: pip + HTTP Content-Length]` → CPU-only. CUDA-сборка = +2.7 ГБ. Для целевой машины без NVIDIA GPU CUDA-сборка — чистый балласт |
| FFmpeg | **Встроить `ffmpeg.exe` в бандл** и добавить папку бандла в `PATH` на старте | Иначе конечному пользователю нужен отдельный шаг установки. Whisper ищет бинарник по имени `ffmpeg` в `PATH` |
| Модель `base.pt` | **Два режима:** по умолчанию — скачивание при первом запуске; опционально — `--add-data` для offline-бандла | Скачивание даёт бандл −138.5 МБ, но требует интернет при первом запуске. Offline-вариант — для машин без сети |
| Путь конфига | **`%APPDATA%\Echo\config.json`** (Windows) / `~/Library/Application Support/Echo/` (macOS) / `~/.config/Echo/` (Linux) | **Обязательное исправление** `app_config.py`: текущий путь от `__file__` в onefile указывает в `sys._MEIPASS` (удаляемая temp-папка) |
| Консоль | `--windowed` (`--noconsole`) для релиза | Текущий spec: `console=True` → у конечного пользователя открывается чёрное окно консоли |
| UPX | Отключить (`upx=False`) | UPX на больших бинарниках torch/CUDA может повреждать DLL и сильно замедлять старт `[ASSUMED]` |
| README | Создать `README.md` + `docs/DEPENDENCIES.md` | В репозитории **нет** ни README, ни LICENSE, ни docs `[VERIFIED: листинг корня]` — DIST-01/03 требуют документирования |

### Важное замечание про `.gitignore`

`[VERIFIED: A:\Repos\Echo\.gitignore]` содержит строку `*.spec`, поэтому **`main.spec` не попадает в git**. Если spec должен быть версионируемым артефактом (а для воспроизводимой сборки — должен), нужно добавить исключение:

```gitignore
*.spec
!Echo.spec
```

---

## Install & Usage Walkthrough (DIST-03)

### Сценарий A. Разработчик / запуск из исходников

```powershell
# 0) Проверить Python. ВАЖНО: на этой машине алиас `python` сломан
#    (ведёт на заглушку Microsoft Store) — использовать `py` или полный путь.
py --version                      # ожидаем 3.10+ (локально 3.14.3)

# 1) Клонировать репозиторий
git clone <repo-url> Echo
cd Echo

# 2) Виртуальное окружение
py -m venv .venv
.\.venv\Scripts\Activate.ps1      # PowerShell
# или: .\.venv\Scripts\activate.bat   (cmd)

# 3) Python-зависимости
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# 4) FFmpeg — обязательный системный шаг (pip его НЕ ставит)
winget install "FFmpeg (Essentials Build)"     # вариант 1 (gyan.dev essentials)
# choco install ffmpeg                          # вариант 2
# scoop install ffmpeg                          # вариант 3
# или вручную: скачать https://github.com/BtbN/FFmpeg-Builds/releases
#   (ffmpeg-master-latest-win64-gpl.zip), распаковать, добавить <...>\bin в PATH

# 5) Проверить, что всё видно
ffmpeg -version
py -c "import whisper, torch, numpy; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"

# 6) Запуск
py main.py
```

**Установка FFmpeg вручную (если нет пакетного менеджера):**
1. Скачать `ffmpeg-master-latest-win64-gpl.zip` с https://github.com/BtbN/FFmpeg-Builds/releases (или `ffmpeg-release-essentials.zip` 109 МБ с https://www.gyan.dev/ffmpeg/builds/).
2. Распаковать, например в `C:\ffmpeg\` (внутри будет `bin\ffmpeg.exe`).
3. Добавить `C:\ffmpeg\bin` в переменную среды `PATH` (System Properties → Environment Variables).
4. **Открыть новое окно терминала** (старое не подхватит новый PATH) и проверить `ffmpeg -version`.
5. Проверка целостности (по желанию): сверить с `.sha256` рядом с архивом на gyan.dev.

### Сценарий B. Конечный пользователь — из исходников

1. Установить Python с https://www.python.org/downloads/ (галочка **«Add python.exe to PATH»**).
2. Скачать архив с приложением и распаковать.
3. Открыть терминал в папке и выполнить:
   ```powershell
   py -m pip install -r requirements.txt
   winget install "FFmpeg (Essentials Build)"
   py main.py
   ```
4. При первом нажатии «START TRANSCRIPTION» модель `base.pt` (138.5 МБ) скачается в `%USERPROFILE%\.cache\whisper\` — **нужен интернет**.
5. Настроить конспект: кнопка **API SETTINGS** → вставить API-ключ (по умолчанию base URL `https://openrouter.ai/api/v1`, модель `openai/gpt-4o-mini`).

### Сценарий C. Конечный пользователь — standalone `.exe`

1. Получить папку `Echo\` (после сборки, см. ниже) — целиком, не только `.exe`.
2. Запустить `Echo.exe`.
3. При первом запуске (если модель не встроена) — дождаться скачивания `base.pt`.
4. FFmpeg **уже внутри** — ничего доустанавливать не нужно.
5. Конфиг с API-ключом сохраняется в `%APPDATA%\Echo\config.json` и переживает перезапуск/обновление.

### Проверочный чек-лист (использовать в задачах верификации)

| Проверка | Команда | Ожидаемый результат |
|----------|---------|---------------------|
| Python есть | `py --version` | `Python 3.1x.x` |
| Пакеты стоят | `py -c "import whisper,torch,tiktoken,numba"` | без ошибок |
| FFmpeg в PATH | `ffmpeg -version` | строка `ffmpeg version ...` |
| FFmpeg реально декодирует | `ffmpeg -i sample.mp3 -f s16le -ac 1 -ar 16000 - > NUL` | код возврата 0, без ошибок |
| GPU (опционально) | `py -c "import torch;print(torch.cuda.is_available())"` | `True` при NVIDIA, иначе `False` (работает и на CPU) |
| Модель скачана | `dir %USERPROFILE%\.cache\whisper` | `base.pt` ≈ 138.5 МБ |
| Приложение стартует | `py main.py` | окно «ECHO // Audio Processing Unit» |

---

## PyInstaller Packaging Notes (DIST-04)

### Что уже есть и чем это плохо

`[VERIFIED: main.spec, build/, dist/, pip list]`

| Параметр текущей сборки | Значение | Проблема |
|--------------------------|----------|----------|
| Режим | `COLLECT` → **onedir** | Хорошо |
| `console` | `True` | У конечного пользователя открывается консольное окно |
| `upx` | `True` | Риск повреждения больших DLL torch |
| `datas` | `[]` | **Модель не встроена** → нужен интернет при первом запуске |
| `binaries` | `[]` | **FFmpeg не встроен** → нужен системный FFmpeg |
| `hiddenimports` | `[]` | Сработало (whisper — чистый Python, hooks для torch/numba есть), но хрупко |
| Размер | **3 045 МБ** (torch 2 789 МБ) | Неприемлемо для раздачи |
| `main.exe` | 46.1 МБ | ок |
| Состав | `torch 2.14.0+cu130` → CUDA 13 DLL: `cublasLt64_13.dll` (455.8 МБ), `torch_cuda.dll` (403.1 МБ), `cufft64_12.dll` (271.2 МБ), `cudnn_*` (418 МБ) … | 90 % размера — CUDA, которая на большинстве машин не нужна |
| Лишнее | `matplotlib` 11.6 МБ, `PIL` 12.7 МБ, `torchvision` 2.3 МБ, `lxml` 6.7 МБ | Приложение их **не импортирует** → мёртвый вес |

Полезные размеры для планирования `[VERIFIED: измерение dist/]`:
`llvmlite 114.8 МБ` (нужен, транзитивно от numba) · `numpy 5.9` · `_tcl_data 3.0` · `_tk_data 0.8` · `tcl8 0.3` · `tiktoken 2.3` · `numba 0.5`.

### Проблема №1 (критическая): путь конфига

`[VERIFIED: app_config.py, строки 6–9]`

```python
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "app_config.json",
)
```

`[CITED: https://pyinstaller.org/en/stable/runtime-information.html]` — при импорте модуля из бандла PyInstaller подставляет `__file__ = sys._MEIPASS + '...'`. Для `onefile` `sys._MEIPASS` — это **временная папка, удаляемая при выходе**; для `onedir` — папка `_internal`, которая тоже перезаписывается при обновлении приложения. Итог: **API-ключ и настройки не сохраняются** (onefile) либо теряются при обновлении (onedir).

**Исправление (рекомендуемое):**

```python
"""Persistent application config — user-scoped, survives PyInstaller updates."""
import json
import os
import sys

APP_NAME = "Echo"


def _config_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
    return os.path.join(base, APP_NAME)


CONFIG_PATH = os.path.join(_config_dir(), "app_config.json")
```

Плюс миграция: при первом запуске, если `%APPDATA%\Echo\app_config.json` отсутствует, но рядом с приложением/модулем есть старый `app_config.json` — скопировать его (см. Runtime State Inventory).

### Проблема №2: FFmpeg внутри бандла

Whisper вызывает **голое имя** `ffmpeg` → ищет в `PATH`. PyInstaller **не добавляет** папку бандла в `PATH` автоматически. Решение — добавить её на старте, **до** первого вызова whisper:

```python
# main.py — в самом начале, после импортов
import os
import sys


def _register_bundled_ffmpeg() -> None:
    """Prepend bundle dir to PATH so whisper's `ffmpeg` subprocess resolves."""
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return  # обычный запуск из исходников — используем системный ffmpeg
    os.environ["PATH"] = base + os.pathsep + os.environ.get("PATH", "")
```

И в spec добавить бинарник:

```python
binaries=[("C:/ffmpeg/bin/ffmpeg.exe", ".")],
```

> Альтернатива без правки `PATH`: monkeypatch `whisper.audio.load_audio`, но это хрупко (зависит от внутреннего API) — **не рекомендуется**.

### Проблема №3: модель `base.pt`

`[VERIFIED: whisper/__init__.py]` — `load_model(name, device=None, download_root=None, in_memory=False)`; при `download_root=None` корень = `%USERPROFILE%\.cache\whisper` (или `$XDG_CACHE_HOME/whisper`). Функция `_download()` **использует уже существующий файл, если его SHA256 совпадает** — значит офлайн-загрузка из бандла работает, если положить файл под правильным именем:

```python
# TranscriptionEngine.load_model — поддержка встроенной модели
import os, sys

def _model_root() -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base and os.path.isfile(os.path.join(base, "models", "base.pt")):
        return os.path.join(base, "models")   # offline-модель из бандла
    return None                                # иначе ~/.cache/whisper (скачает сам)

self.model = whisper.load_model("base", download_root=_model_root())
```

В spec: `datas=[("base.pt", "models")]`.

**Развилка для планировщика:** встраивать модель или нет.

| Вариант | +бандл | Требует интернет при 1-м запуске | Кому |
|---------|--------|----------------------------------|------|
| Скачивать при первом запуске | 0 МБ | Да (138.5 МБ) | большинство пользователей |
| Встроить `base.pt` | +138.5 МБ | Нет | машины без сети / офлайн-раздача |

### Рекомендуемая сборка

**Шаг 1. Готовить окружение для раздачи с CPU-only torch** (ключ к размеру):

```powershell
py -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install openai-whisper==20250625 tqdm srt
py -m pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only, ~118 МБ
py -m pip install pyinstaller
```

> `[VERIFIED: pip]` Обычный `pip install torch==2.14.0` с PyPI на win_amd64 даёт wheel **118.4 МБ** без CUDA-суффикса (`torch-2.14.0-cp314-cp314-win_amd64.whl`) → CPU-only. CUDA-сборка (`+cu130`) тянется с индекса PyTorch (`--index-url https://download.pytorch.org/whl/cu130`). `[ASSUMED]` — см. Assumptions Log A1.

**Шаг 2. Spec-файл** (пример, `Echo.spec`):

```python
# -*- mode: python ; coding: utf-8 -*-
import os

FFMPEG = os.environ.get("FFMPEG_BIN", r"C:\ffmpeg\bin\ffmpeg.exe")
MODEL  = os.environ.get("WHISPER_MODEL_PT", "")   # пусто => модель не встраивается

datas    = [(MODEL, "models")] if MODEL and os.path.isfile(MODEL) else []
binaries = [(FFMPEG, ".")] if os.path.isfile(FFMPEG) else []

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=["whisper", "tiktoken", "numba", "llvmlite"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "PIL", "torchvision", "lxml", "scipy",
        "IPython", "pytest", "torch.distributed", "torch.testing",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Echo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX выключен намеренно
    console=False,        # GUI-приложение, без консольного окна
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="Echo",
)
```

**Шаг 3. Сборка и запуск:**

```powershell
$env:FFMPEG_BIN = "C:\ffmpeg\bin\ffmpeg.exe"
$env:WHISPER_MODEL_PT = "$env:USERPROFILE\.cache\whisper\base.pt"   # опционально
pyinstaller --noconfirm --clean Echo.spec
.\dist\Echo\Echo.exe
```

**Альтернатива одной командой** (без spec, для быстрой проверки):

```powershell
pyinstaller --noconfirm --clean --windowed --name Echo `
  --add-binary "C:\ffmpeg\bin\ffmpeg.exe;." `
  --exclude-module matplotlib --exclude-module torchvision --exclude-module PIL `
  main.py
```

### Ожидаемый размер (оценка)

| Сборка | Оценка | Комментарий |
|--------|--------|-------------|
| Текущая (cu130, с лишним) | **3 045 МБ** `[VERIFIED]` | измерено |
| CPU-only + исключения | **~350–550 МБ** `[ASSUMED]` | torch CPU (~120 МБ распакованных ~250 МБ) + llvmlite 115 + tk/numpy/tiktoken + exe |
| + встроенная `base.pt` | **+138.5 МБ** | |

> Точные цифры появятся после первой «чистой» CPU-сборки — это должно стать проверяемым критерием задачи, а не предположением.

### Известные подводные камни PyInstaller

| Проблема | Причина | Решение |
|----------|---------|---------|
| `FileNotFoundError: ffmpeg` в exe | Бинарник не собран/не в `PATH` | `--add-binary` + `_register_bundled_ffmpeg()` |
| Настройки не сохраняются | `__file__` → `sys._MEIPASS` | Конфиг в `%APPDATA%` |
| Антивирус/SmartScreen блокирует | Бинарник не подписан | Предупреждать в README; опционально — подпись кода |
| `ModuleNotFoundError: numba` / `llvmlite` | Динамические импорты | `hiddenimports`; hook `hook-numba.py` уже есть в `pyinstaller-hooks-contrib 2026.4` |
| Огромный размер | CUDA-torch + лишние пакеты | CPU-only torch + `excludes` |
| Долгий старт | `import whisper` ≈ **9.7 с** `[VERIFIED: замер]` (в основном импорт torch) | Не импортировать whisper на верхнем уровне; перенести в `load_model()` (ленивая загрузка) |
| `onefile` «висит» при запуске | Распаковка сотен МБ в temp | Использовать `--onedir` |

---

## Runtime State Inventory

> Включено, потому что фаза меняет **место хранения** пользовательских данных (конфиг из папки репозитория → `%APPDATA%`). Это миграция состояния, а не только правка кода.

| Категория | Найдено | Требуемое действие |
|-----------|---------|--------------------|
| **Stored data (конфиг)** | `app_config.json` рядом с `main.py` (содержит `llm.api_key`, `base_url`, `model`, `enabled`). В git **не попадает** (`.gitignore`) `[VERIFIED]` | **Миграция + правка кода.** Новый путь `%APPDATA%\Echo\app_config.json`; при старте — если нового файла нет, а старый есть, скопировать |
| **Stored data (модель)** | `%USERPROFILE%\.cache\whisper\base.pt` = **138.5 МБ** (там же `large-v3-turbo.pt` 1 543 МБ от других задач) `[VERIFIED]` | Кода не требует. Если встраивать модель в бандл — использовать `download_root`; НЕ копировать чужой кэш целиком |
| **Live service config** | Внешний LLM API (OpenRouter): base URL + ключ хранятся **только** в локальном конфиге; на стороне сервиса ничего не регистрируется | Действий не требуется |
| **OS-registered state** | Отсутствует — приложение не регистрирует задачи/службы/автозапуск `[VERIFIED: в репозитории нет кода установки/регистрации]` | Нет |
| **Secrets / env vars** | `llm.api_key` лежит **открытым текстом** в `app_config.json`. Переменные окружения не используются | **Риск.** Минимум — предупредить в документации; лучше — не логировать ключ. Хранение в `%APPDATA%` (Roaming) означает, что ключ может уехать в доменный профиль |
| **Build artifacts** | `build/`, `dist/`, `main.spec` присутствуют, но **`build/` и `dist/` в `.gitignore`**, а `*.spec` игнорируется → spec не версионируется `[VERIFIED]` | Добавить `!Echo.spec` в `.gitignore`, чтобы сборка была воспроизводимой |

**Канонический вопрос:** *после того как все файлы в репозитории обновлены, какие runtime-системы всё ещё содержат старое состояние?* Ответ: **старый `app_config.json` рядом с исходниками** (может содержать рабочий API-ключ пользователя) и **кэш моделей** в `~/.cache/whisper`. Первый нужно мигрировать, второй — переиспользовать, а не дублировать.

---

## Common Pitfalls

### Pitfall 1: FFmpeg установлен, но не в PATH текущей сессии
**What goes wrong:** `ffmpeg -version` в старом терминале не работает после установки.
**Why:** Windows читает `PATH` при старте процесса.
**How to avoid:** В инструкции явно писать «откройте НОВОЕ окно терминала».
**Warning signs:** `ffmpeg` не найден, хотя установка «прошла успешно».

### Pitfall 2: Пользователь поставил только pip-пакеты
**What goes wrong:** Транскрибация падает на любом файле.
**Why:** FFmpeg не ставится через pip — про это легко забыть.
**How to avoid:** Отдельный подраздел «Шаг 3: FFmpeg (обязательно)» + проверка `shutil.which("ffmpeg")` при старте приложения с понятным messagebox.
**Warning signs:** Ошибка `[WinError 2] ... 'ffmpeg'`.

### Pitfall 3: Сборка с CUDA-torch «на всякий случай»
**What goes wrong:** Дистрибутив 3 ГБ, не влезает в лимиты, долго копируется.
**Why:** По умолчанию в dev-окружении стоит `torch+cu130`.
**How to avoid:** Собирать в отдельном venv с CPU-only torch.
**Warning signs:** `dist` > 1 ГБ.

### Pitfall 4: `onefile` вместо `onedir`
**What goes wrong:** Каждый запуск — распаковка сотен МБ; на медленном HDD — минуты; конфиг/модель теряются.
**How to avoid:** `--onedir`; распространять папку целиком (или класть в ZIP/инсталлятор).
**Warning signs:** Долгий «чёрный экран» перед появлением окна.

### Pitfall 5: Ожидание прогресса от whisper
**What goes wrong:** Пользователь думает, что приложение зависло.
**Why:** У `model.transcribe()` нет колбэка прогресса; плюс первый `import whisper` ≈ 10 с, плюс скачивание модели 138.5 МБ.
**How to avoid:** Ленивая загрузка + статус «Загрузка модели…» (уже реализовано) + предупреждение о первом скачивании в README.
**Warning signs:** «Ничего не происходит» на первом запуске.

### Pitfall 6: API-ключ в открытом виде + в Roaming-профиле
**What goes wrong:** Ключ может попасть в резервные копии/другой ПК.
**How to avoid:** Документировать; в идеале — ОС-защищённое хранилище (DPAPI/keyring) отдельной задачей.
**Warning signs:** `app_config.json` с непустым `api_key`.

### Pitfall 7: Сборка под неверную платформу
**What goes wrong:** exe, собранный на Windows, не работает на macOS/Linux.
**Why:** PyInstaller **не** кросс-компилирует.
**How to avoid:** Явно указать в README: артефакты собираются на целевой ОС; macOS/Linux — отдельные сборки (в этом проекте не проверялись).
**Warning signs:** «Exec format error» / «не является приложением Win32».

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python (`py` launcher) | Всё | ✓ | 3.14.3 (`A:\python`) | Полный путь `A:\python\python.exe` |
| Python (алиас `python`) | — | ✗ | заглушка Microsoft Store | Использовать `py` |
| pip | Установка пакетов | ✓ | 26.1.1 | `py -m ensurepip` |
| FFmpeg | Транскрибация | ✓ | `N-126390-g9fc8c785e2-20260902` (`A:\python\Scripts\ffmpeg.exe`) | BtbN/gyan.dev вручную |
| ffprobe | Не используется кодом | ✓ | там же | — |
| torch | ASR | ✓ | 2.14.0+cu130 | CPU-only wheel |
| NVIDIA GPU / CUDA | Ускорение | Не проверено (флаг `--disable-whisper` не относится к GPU) | — | CPU-инференс (медленнее) |
| openai-whisper | ASR | ✓ | 20250625 | — |
| PyInstaller | Сборка | ✓ | 6.19.0 + hooks-contrib 2026.4 | — |
| Кэш модели | Офлайн-работа | ✓ | `base.pt` 138.5 МБ | Скачать при первом запуске |
| Интернет | Первый запуск / конспект | — | — | Офлайн-бандл с `base.pt` |

**Missing dependencies with no fallback:** нет — всё критичное доступно.

**Missing dependencies with fallback:**
- Алиас `python` сломан → использовать `py` (зафиксировать в README!).
- CUDA/GPU не подтверждён → CPU-режим работает, но медленнее.

---

## Validation Architecture

`workflow.nyquist_validation = true` в `.planning/config.json` → секция обязательна.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | **Отсутствует** `[VERIFIED: нет tests/, conftest.py, pytest.ini, pyproject.toml]` |
| Config file | none — см. Wave 0 |
| Quick run command | `py -m pytest tests -q` (после Wave 0) |
| Full suite command | `py -m pytest tests -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DIST-01 | В документе перечислены все зависимости с URL | manual-only (проверка артефакта) | — (ревью `docs/DEPENDENCIES.md`) | ❌ Wave 0 |
| DIST-02 | Роль FFmpeg объяснена; проверено, что FFmpeg не ASR | manual + smoke | `ffmpeg -version` / `ffmpeg -filters` (нет `whisper`) | ❌ Wave 0 |
| DIST-03 | Инструкция приводит к рабочему запуску | smoke (ручной прогон) | `py main.py` + реальная транскрибация | ❌ Wave 0 |
| DIST-04 | Собирается standalone exe и запускается | smoke/e2e | `pyinstaller --noconfirm --clean Echo.spec` → `.\dist\Echo\Echo.exe` | ❌ Wave 0 |
| (инфра) | Конфиг переживает перезапуск | **unit** | `py -m pytest tests/test_config.py -q` | ❌ Wave 0 |
| (инфра) | FFmpeg обнаруживается на старте | **unit** | `py -m pytest tests/test_ffmpeg_check.py -q` | ❌ Wave 0 |
| (инфра) | Сборка не содержит CUDA/лишних пакетов | **smoke** | проверка размера `dist/Echo` < порога | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `py -m pytest tests -q` (быстрые unit-тесты, < 5 с)
- **Per wave merge:** `py -m pytest tests -q` + `py -c "import whisper"` (импорт-смоук)
- **Phase gate:** полный ручной прогон сценариев A/B/C + сборка exe + проверка размера

### Wave 0 Gaps
- [ ] `tests/` + `tests/conftest.py` — pytest не установлен, инфраструктуры нет
- [ ] `tests/test_config.py` — путь конфига user-scoped и не зависит от `__file__`
- [ ] `tests/test_ffmpeg_check.py` — функция проверки FFmpeg корректно отрабатывает отсутствие бинарника
- [ ] `tests/test_srt.py` — `_srt_content()` / `_time_to_srt()` (сейчас без тестов)
- [ ] `docs/DEPENDENCIES.md` — DIST-01/02
- [ ] `README.md` — DIST-03 (в репозитории README нет)
- [ ] `Echo.spec` + `!Echo.spec` в `.gitignore` — DIST-04
- [ ] Установка: `py -m pip install pytest` (добавить в dev-зависимости)

---

## Security Domain

`security_enforcement` в конфиге не выставлен в `false` → секция обязательна.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Да (частично) | API-ключ LLM: не логировать, не печатать в messagebox, хранить вне репозитория |
| V3 Session Management | Нет | Сессий нет |
| V4 Access Control | Нет | Однопользовательское настольное приложение |
| V5 Input Validation | Да | Путь к аудио: передавать в `subprocess` **списком** (как делает whisper), не через `shell=True`; проверять существование файла до запуска |
| V6 Cryptography | Да | **Не изобретать своё.** Для секретов использовать ОС-хранилище (`keyring`/DPAPI). Сейчас — открытый JSON (осознанный компромисс v1) |
| Supply chain (вне ASVS, но критично) | Да | FFmpeg и pip-пакеты — из официальных источников; проверять `.sha256`; фиксировать версии |

### Known Threat Patterns for {Python desktop + subprocess + PyInstaller}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Вредоносный медиафайл эксплуатирует уязвимость парсера FFmpeg | Elevation of Privilege | Держать FFmpeg в актуальной сборке (BtbN обновляется ежедневно); запускать subprocess без лишних прав |
| Инъекция команд через имя файла | Tampering | `subprocess.run([...])` без `shell=True` (уже так в whisper) |
| Кража API-ключа из `app_config.json` | Information Disclosure | `%APPDATA%` вместо папки приложения; не коммитить (уже в `.gitignore`); в перспективе — `keyring` |
| Подмена `ffmpeg.exe` в бандле | Tampering | Собирать из официального источника, фиксировать хэш, распространять целостным архивом |
| Неподписанный exe → SmartScreen / подмена DLL | Spoofing | Информировать в README; опционально — code signing; не загружать DLL из CWD |
| Ключ уезжает в доменный профиль (Roaming) | Information Disclosure | Осознанно принять либо использовать `%LOCALAPPDATA%` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PyPI-wheel `torch 2.14.0` (win_amd64, 118.4 МБ) — **CPU-only**; CUDA требует `--index-url download.pytorch.org/whl/cuXXX` | Recommended Approach / PyInstaller | Если неверно — документированная CPU-сборка внезапно потянет 2.5 ГБ CUDA, и размер бандла не уменьшится |
| A2 | Python 3.14.3 совместим с whisper/torch в этом окружении (официально README заявляет 3.8–3.11) | Required Software | На чистой машине с 3.14 могут быть сбои сборки/колеса отсутствовать → рекомендовать 3.10–3.12 |
| A3 | `numpy>=2.5.0` из requirements совместим с `numba 0.67.0` | Required Software | pip подтянет 2.5.3 и `import numba` может упасть → нужен пин |
| A4 | Установленный `ffmpeg.exe` (145.8 МБ) — сборка **BtbN win64-gpl** | Required Software | Неверная атрибуция источника в документации |
| A5 | Оценка размера CPU-only сборки ~350–550 МБ | PyInstaller | Планирование по неверному бюджету размера |
| A6 | Отключение UPX безопасно/предпочтительно для torch-сборок | Recommended Approach | Если UPX был нужен для сжатия — вырастет размер (но не сломается) |
| A7 | `%APPDATA%` — корректный user-scoped путь для Windows | Runtime State | На нестандартных конфигурациях профиля путь может быть недоступен |
| A8 | `matplotlib`/`torchvision`/`PIL`/`lxml` в бандле — мёртвый вес (приложение их не импортирует) | PyInstaller | Если что-то из них нужно транзитивно в рантайме — `--exclude` сломает приложение (проверять после сборки!) |

**Если таблица непустая:** перечисленные пункты нужно подтвердить на discuss/plan этапе до фиксации решений (особенно A1, A2, A3, A8).

---

## Open Questions

1. **Встраивать ли модель `base.pt` в бандл?**
   - Что знаем: файл 138.5 МБ, whisper корректно читает его из `download_root` при совпадении SHA256.
   - Что неясно: целевая аудитория — есть ли у неё интернет при первом запуске.
   - Рекомендация: по умолчанию — скачивание; сделать встраивание опциональным флагом сборки (`WHISPER_MODEL_PT`).

2. **Нужна ли поддержка GPU в раздаваемом exe?**
   - Что знаем: CUDA-сборка = +2.7 ГБ; CPU работает всегда.
   - Что неясно: готов ли пользователь на 3 ГБ ради ускорения.
   - Рекомендация: CPU по умолчанию; документировать, как собрать CUDA-вариант для себя.

3. **Менять ли движок на faster-whisper?**
   - Что знаем: до 4× быстрее, не требует системного FFmpeg (PyAV внутри).
   - Что неясно: стоит ли переписывать `TranscriptionEngine` в этой фазе.
   - Рекомендация: **не менять в Phase 5**; зафиксировать как кандидата в будущий milestone.

4. **Нужен ли инсталлятор (Inno Setup/NSIS/MSIX) вместо ZIP?**
   - Что знаем: `--onedir` даёт папку; для конечного пользователя ZIP привычнее и проще.
   - Рекомендация: на этой фазе — ZIP с `--onedir`; инсталлятор — при необходимости позже.

5. **macOS/Linux-сборки?**
   - Что знаем: PyInstaller не кросс-компилирует; в этом окружении проверяется только Windows.
   - Рекомендация: документировать как «не проверено», ограничить фазу Windows.

---

## Sources

### Primary (HIGH confidence)
- **Локальный исходный код** `A:\python\Lib\site-packages\whisper\audio.py` (строки 25–62) — точный вызов ffmpeg и параметры 16 кГц/моно/s16le
- **Локальный исходный код** `A:\python\Lib\site-packages\whisper\__init__.py` — `_MODELS`, `download_root` (`~/.cache/whisper`), SHA256-проверка, `load_model()`
- **Локальное окружение** — `pip show/list`, `pip index versions`, `pip install --dry-run --report`, размеры `dist/`, `ffmpeg -buildconf`, замер `import whisper`
- **PyInstaller runtime information** — https://pyinstaller.org/en/stable/runtime-information.html (`sys._MEIPASS`, поведение `__file__`)
- **openai/whisper README** — https://github.com/openai/whisper (требование FFmpeg, команды установки, таблица моделей: base = 74M параметров, ~1 ГБ VRAM, ~7×)
- **FFmpeg About** — https://www.ffmpeg.org/about.html (определение: multimedia framework; decode/encode/transcode/mux/demux/filter/play)
- **PyPI** — https://pypi.org/project/openai-whisper/ , https://pypi.org/project/torch/ , https://pypi.org/project/numpy/ , https://pypi.org/project/tqdm/ , https://pypi.org/project/srt/

### Secondary (MEDIUM confidence)
- **BtbN/FFmpeg-Builds** — https://github.com/BtbN/FFmpeg-Builds (статические Windows/Linux-сборки, «latest» с постоянным URL, варианты gpl/lgpl/nonfree)
- **gyan.dev CODEX FFMPEG** — https://www.gyan.dev/ffmpeg/builds/ (essentials 34 МБ 7z / 109 МБ zip; `winget install "FFmpeg (Essentials Build)"`; changelog 055: поддержка whisper.cpp в full-сборках)
- **faster-whisper на PyPI** — https://pypi.org/project/faster-whisper/ (до 4× быстрее; FFmpeg не нужен — PyAV внутри; требования cuBLAS/cuDNN 9)
- **whisper.cpp** — https://github.com/ggml-org/whisper.cpp (без зависимостей, CPU-only, CLI принимает только 16-бит WAV, base = 142 МиБ диск / ~388 МБ RAM)
- **Vosk** — https://alphacephei.com/vosk/ (offline, 20+ языков, модели ~50 МБ, streaming API, `pip3 install vosk`)
- **PyInstaller hooks** — `_pyinstaller_hooks_contrib\stdhooks\hook-torch.py`, `hook-numba.py` (локально, версия 2026.4)

### Tertiary (LOW confidence)
- Атрибуция установленного `ffmpeg.exe` к BtbN (по косвенным признакам сборки) — требует подтверждения
- Оценки размера CPU-only сборки — требуют измерения после первой сборки
- Поведение UPX с torch-DLL — требует проверки
- `pydub` как «заброшенный» — по памяти, не проверялось в этой сессии

---

## Metadata

**Confidence breakdown:**
- **Standard stack: HIGH** — версии и зависимости проверены через `pip`/`importlib.metadata`; источники официальные
- **Why FFmpeg: HIGH** — подтверждено чтением исходного кода `whisper/audio.py`, а не предположением
- **FFmpeg vs alternatives: MEDIUM** — сравнения взяты из официальных README/PyPI-страниц, но производительность не бенчмаркалась
- **PyInstaller packaging: MEDIUM** — механика подтверждена документацией и текущей сборкой; размеры/исключения требуют практической проверки
- **Pitfalls: HIGH** — большая часть подтверждена локальными проверками (битый алиас `python`, `--disable-whisper`, 3 ГБ dist, 9.7 с импорт)

**Research date:** 2026-09-21
**Valid until:** ~2026-10-21 (30 дней; версии FFmpeg-сборок обновляются ежедневно, whisper/torch — раз в месяцы)
