# Echo

**Echo** — локальное desktop-приложение для автоматической транскрибации аудиофайлов в текст с использованием [OpenAI Whisper](https://github.com/openai/whisper).

Приложение предоставляет простой графический интерфейс, через который можно выбрать аудиофайл, запустить распознавание речи и получить готовый текст.

> **Audio → Whisper → Text**

## Features

* Распознавание речи с помощью OpenAI Whisper
* Поддержка нескольких аудиоформатов:

  * MP3
  * WAV
  * M4A
  * FLAC
  * OGG
  * WebM
* Автоматическое определение языка
* Графический интерфейс на Tkinter
* Отображение статуса обработки
* Работа транскрибации в отдельном потоке, чтобы GUI не зависал
* Обработка ошибок с понятными сообщениями
* Ленивое (`lazy`) и потокобезопасное создание Whisper-модели
* Возможность повторно использовать загруженную модель без её повторной загрузки
* Конспект транскрипции через подключаемую LLM (OpenRouter)
* Пресеты конспекта: Дейли / Лекция / Интервью / Клиент / Свободный
* Структурированный вывод конспекта: JSON-схема с рендером в читаемые разделы
* Диалог **API SETTINGS** для ключа, URL и модели, а также выбора пресета
* Сохранение результата в `.txt` и `.srt`

## How it works

Echo состоит из двух основных частей:

```text
┌──────────────────────────┐
│           GUI            │
│         Tkinter          │
│                          │
│  Select file             │
│  Start transcription     │
│  Display result          │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│   TranscriptionEngine    │
│                          │
│  • model management      │
│  • background thread     │
│  • status updates        │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│       OpenAI Whisper     │
│                          │
│      Speech → Text       │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│    Transcription text    │
│                          │
│  • GUI result view       │
│  • saved to .txt/.srt    │
└────────────┬─────────────┘
             │  (optional) GENERATE SUMMARY
             ↓
┌──────────────────────────┐
│   SummarizationEngine    │
│                          │
│  • preset / prompt       │
│  • json_schema →         │
│    json_object → text    │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│        llm_client        │
│                          │
│   HTTP POST (urllib)     │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│        OpenRouter        │
│                          │
│  external LLM (summary)  │
└──────────────────────────┘
```

### Transcription flow

1. Пользователь выбирает аудиофайл.
2. Echo активирует кнопку транскрибации.
3. Транскрибация запускается в отдельном потоке.
4. `TranscriptionEngine` загружает модель Whisper при первом запуске.
5. Whisper обрабатывает аудиофайл.
6. Приложение получает распознанный текст и определённый язык.
7. Результат отображается в GUI.

Статусы обработки передаются между рабочим потоком и GUI через потокобезопасную `queue.Queue`. Это позволяет не блокировать основной поток Tkinter во время работы модели.

### Summarization flow

1. Пользователь нажимает **GENERATE SUMMARY** и выбирает пресет конспекта.
2. `SummarizationEngine` собирает запрос по выбранному пресету.
3. `llm_client` отправляет HTTP POST в OpenRouter.
4. Ответ рендерится в читаемые разделы (структурированные пресеты принимаются по JSON-схеме).
5. Готовый конспект кладётся в GUI и сохраняется вместе с транскрипцией.

Конспект — опциональный этап: без настроенного API-ключа и включённой опции он просто не запускается.

## Architecture

Основная логика распределена по пакету `echo/` и его подпакету `echo/ui/`.

### `TranscriberApp`

Отвечает за пользовательский интерфейс:

* выбор файла;
* отображение пути к файлу;
* запуск транскрибации;
* отображение статуса;
* вывод результата;
* обработку пользовательских ошибок.

### `TranscriptionEngine`

Отвечает за работу с Whisper:

* загрузку модели;
* выполнение транскрибации;
* запуск фонового потока;
* передачу статусов;
* обработку исключений.

Модель загружается лениво:

```python
self.model = None
```

При первом запуске:

```python
self.model = whisper.load_model("base")
```

После этого уже загруженная модель переиспользуется.

Для защиты загрузки модели от одновременного доступа используется `threading.Lock`.

### `SummarizationEngine`

Отвечает за опциональный конспект через подключаемую LLM:

* хранит конфиг и выбранный пресет;
* собирает лестницу слоёв запроса: `json_schema` → `json_object` → plain text;
* провал слоя (провайдер не принял `response_format`, пустой или непригодный ответ) ведёт на следующий слой, а терминальные ошибки (`401/403/429/5xx`, сеть) не повторяются;
* запускает генерацию в фоновом потоке и передаёт результат через очередь.

### `llm_client`

Единственная точка сети в приложении:

* собирает `messages` для запроса;
* делает HTTP POST в OpenRouter через стандартную библиотеку `urllib.request`;
* парсит JSON-ответ и рендерит его в читаемые разделы.

### Package layout

Код разбит на пакет `echo/` с подпакетом `echo/ui/`:

* `echo/ui/app.py` — `TranscriberApp` (состояние, потоки, polling);
* `echo/ui/build.py` — построение виджетов;
* `echo/ui/theme.py` — палитра `COLORS`;
* `echo/ui/settings_dialog.py` — диалог **API SETTINGS**;
* `echo/transcription_engine.py` — движок транскрибации;
* `echo/summarization_engine.py` — движок конспекта;
* `echo/config.py`, `echo/presets.py`, `echo/errors.py`, `echo/srt.py` — листовые модули.

## Tech Stack

| Technology     | Purpose                                            |
| -------------- | -------------------------------------------------- |
| Python         | Основной язык                                      |
| Tkinter        | GUI                                                |
| OpenAI Whisper | Распознавание речи                                 |
| PyTorch        | ML backend для Whisper                             |
| NumPy          | Работа с числовыми данными                         |
| tqdm           | Отображение прогресса в Whisper                    |
| OpenRouter LLM | Конспект через подключаемую LLM                    |

Основные зависимости закреплены в `requirements.txt` — это скомпилированный `pip-tools` lock: все
прямые и транзитивные пакеты зафиксированы точными пинами (`==`) и хэшами (`--hash=sha256:`).
Установка выполняется в режиме проверки хэшей (`--require-hashes`).

Конспект обращается к LLM через стандартную библиотеку `urllib.request` — **новых зависимостей для конспекта нет**.

Субтитры `.srt` формируются вручную в `echo/srt.py` — сторонний пакет `srt` не используется и в зависимостях не объявлен.

## Requirements

* Python 3.10+
* Достаточно оперативной памяти для выбранной модели Whisper
* Интернет-соединение требуется при первом скачивании модели

## Installation

### 1. Clone repository

```bash
git clone https://github.com/TimoshaK/Echo.git
cd Echo
```

### 2. Create virtual environment

#### Windows

```bash
py -3 -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

Установка идёт в режиме проверки хэшей: pip сверит каждый скачанный архив с хэшем из lock-файла и
откажется устанавливать что-либо, что не совпало.

```bash
pip install --require-hashes -r requirements.txt
```

`requirements.txt` — CPU-сборка (`torch` с PyPI). Для NVIDIA-видеокарты используйте CUDA-lock:

```bash
pip install --require-hashes -r requirements-cuda.txt
```

CUDA-lock тянет `torch==2.14.0+cu130` с индекса `https://download.pytorch.org/whl/cu130` (~2.8 ГБ).
На машине без NVIDIA-видеокарты он не нужен.

Инструменты разработки (`pip-tools`, `pip-audit`, `pyinstaller`) лежат в отдельном lock-файле и для
запуска приложения не требуются:

```bash
pip install -r requirements-dev.txt
```

Два замечания:

* `openai-whisper` публикуется только как sdist, поэтому pip собирает его из исходников. Зависимости
  сборочного окружения (PEP 517) **не** покрыты `--require-hashes` — это остаточный риск.
* `torch==2.14.0` (CPU-lock) и `torch==2.14.0+cu130` (CUDA-lock): pip считает требование `==2.14.0`
  выполненным, если уже установлен `2.14.0+cu130`, поэтому в существующем CUDA-окружении CPU-lock не
  понизит torch. В чистом окружении он поставит CPU-сборку.

### 4. Install FFmpeg (system binary, not pip)

Whisper использует FFmpeg для декодирования аудио, и он **не ставится через pip** — это отдельный системный бинарник.

Windows:

```bash
winget install "FFmpeg (Essentials Build)"
:: либо choco install ffmpeg
:: либо scoop install ffmpeg
```

Вручную: распаковать сборку FFmpeg и добавить её папку `bin` в `PATH`.

Linux / macOS:

```bash
# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

Проверка установки:

```bash
ffmpeg -version
```

### Regenerating the locks

Lock-файлы генерируются `pip-tools`; команда генерации записана в заголовке каждого файла.

CPU- и dev-lock (чистый PyPI; хэши берутся из PyPI JSON API, поэтому загрузок нет):

```bash
pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements.txt requirements.in
pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements-dev.txt requirements-dev.in
```

CUDA-lock генерируется иначе. Для версии `+cu130` `--generate-hashes` не может получить хэши из PyPI
JSON API и пытается скачать **все 24** CUDA-колеса (десятки ГБ). Поэтому выходной файл «засевается»
из CPU-lock: блок `torch` заменяется на `torch==2.14.0+cu130` с хэшами, опубликованными индексом
PyTorch, после чего `--reuse-hashes` переиспользует все хэши и ничего не скачивает:

```bash
pip-compile --generate-hashes --reuse-hashes --allow-unsafe --strip-extras --output-file requirements-cuda.txt requirements-cuda.in
```

Хэши `torch==2.14.0+cu130` берутся из HTML индекса `https://download.pytorch.org/whl/cu130/torch/`,
где они опубликованы во фрагменте URL (`#sha256=...`). Версия в URL закодирована как
`2.14.0%2Bcu130`.

Всегда задавайте `CUSTOM_COMPILE_COMMAND`: без него pip-tools записывает в заголовок
несуществующий флаг `--no-index`.

## Dependency audit (pip-audit)

Локальная проверка зависимостей на известные уязвимости. **Без CI** — команда запускается вручную:

```bash
py -3 -m pip install -r requirements-dev.txt
py -3 -m pip_audit -r requirements.txt --progress-spinner off
```

`pip-audit` разбирает lock-файл вместе со строками `--hash=`. Ненулевой код возврата означает
найденные уязвимости. Для CUDA-lock:

```bash
py -3 -m pip_audit -r requirements-cuda.txt --progress-spinner off
```

Обновление уязвимого пакета: изменить пин в соответствующем `.in`-файле, перегенерировать lock
(см. выше) и повторить аудит.

## Run

Запустите приложение:

```bash
py -3 main.py
```

Альтернативно — как пакет:

```bash
py -3 -m echo
```

Файл `app_config.json` создаётся и читается в **корне репозитория**.

После запуска:

1. Нажмите **«Выбрать файл»**.
2. Выберите аудиофайл.
3. Нажмите **«Транскрибировать»**.
4. Дождитесь окончания обработки.
5. Готовый текст появится в области результата.

При первом запуске Whisper скачает выбранную модель.

## Run in Docker (browser GUI)

Тот же GUI можно запустить в контейнере: образ поднимает виртуальный дисплей и отдаёт окно в браузер через VNC (x11vnc + noVNC) на порту `6080`.

```powershell
docker build -t echo:cpu .
docker run --rm -p 127.0.0.1:6080:6080 -v "${PWD}/config:/config" -e ECHO_CONFIG_PATH=/config/app_config.json -v echo-whisper:/root/.cache/whisper -v "${PWD}/audio:/root/audio" echo:cpu
```

Откройте <http://localhost:6080/vnc.html>. Корпоративный **https** endpoint задаётся в `app_config.json`, который подаётся **каталогом** `config/` (монтировать сам файл нельзя); аудио и кэш модели Whisper подключаются томами. Подробности о монтировании, безопасности порта и развёртывании на другом ПК (`docker save`/`load`) — в [BUILD.md](BUILD.md).

## Whisper models

Сейчас Echo использует модель:

```text
base
```

Whisper предоставляет несколько размеров моделей, которые отличаются скоростью работы, требованиями к ресурсам и качеством распознавания:

| Model    |     Speed | Accuracy | Resource usage |
| -------- | --------: | -------: | -------------: |
| `tiny`   | Very fast |    Lower |       Very low |
| `base`   |      Fast |     Good |            Low |
| `small`  |    Medium |   Better |         Medium |
| `medium` |    Slower |     High |           High |
| `large`  |   Slowest |  Highest |      Very high |

Для текущей версии проекта используется `base` как компромисс между скоростью и качеством.

## Error handling

Echo обрабатывает распространённые ошибки и преобразует их в понятные пользователю сообщения.

Например:

```text
FFmpeg / audio codec
        ↓
"Не установлен ffmpeg..."

Unsupported format
        ↓
"Неподдерживаемый формат файла..."

Model download
        ↓
"Не удалось загрузить модель Whisper..."

Memory error
        ↓
"Недостаточно памяти..."
```

Исходная информация об ошибке также сохраняется и выводится пользователю для диагностики.

## Project structure

```text
Echo/
│
├── main.py                    # тонкий лаунчер
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

`main.py` — тонкий лаунчер; основная логика находится в пакете `echo/`.

## Configuration

Настройки хранятся в `app_config.json` в **корне репозитория**:

| Key                  | Default                        | Назначение                          |
| -------------------- | ------------------------------ | ----------------------------------- |
| `llm.api_key`        | пусто                          | API-ключ OpenRouter                 |
| `llm.base_url`       | `https://openrouter.ai/api/v1` | Базовый URL OpenAI-совместимого API |
| `llm.model`          | `openai/gpt-4o-mini`           | Модель для конспекта                |
| `llm.enabled`        | `false`                        | Включает конспект                   |
| `llm.summary_preset` | `free`                         | Пресет конспекта                    |

Настраивать удобнее через диалог **API SETTINGS** в приложении: он сохраняет ключ, URL, модель и выбранный пресет в этот же файл.

Доступные пресеты конспекта:

* **Дейли** (`daily`) — AFD, решения, блокеры
* **Лекция** (`lecture`) — тезис, ключевые пункты, термины, выводы
* **Интервью** (`interview`) — резюме, вопросы и ответы, цитаты
* **Клиент** (`client`) — требования, договорённости, следующие шаги
* **Свободный** (`free`) — свободный конспект без фиксированной схемы

## Design goals

Echo создавался с несколькими простыми принципами:

* **Local-first** — обработка выполняется локально.
* **Simple UI** — пользователь должен понимать сценарий без дополнительной настройки.
* **Non-blocking UI** — длительные операции не должны замораживать интерфейс.
* **Separation of concerns** — GUI и логика работы с Whisper разделены.
* **Graceful error handling** — технические ошибки должны превращаться в понятные сообщения для пользователя.

## Roadmap

Планируемые направления развития:

* [ ] Выбор модели Whisper из GUI
* [ ] Настройка языка транскрибации
* [x] Сохранение результата в `.txt`
* [x] Экспорт в `.srt`
* [x] Отображение прогресса обработки
* [x] Конспект транскрипции через LLM (OpenRouter)
* [x] Пресеты конспекта (дейли/лекция/интервью/клиент/свободный)
* [ ] История транскрибаций
* [ ] Drag & Drop для аудиофайлов
* [ ] Настройки приложения
* [x] Улучшение архитектуры проекта
* [ ] Создание тестов
* [ ] Сборка standalone-приложения для Windows

## Privacy

Echo использует локальную модель Whisper для обработки аудио.

После загрузки модели транскрибация выполняется непосредственно на компьютере пользователя. Аудиофайлы не требуют отправки во внешний API для выполнения распознавания.

**Конспект (GENERATE SUMMARY) — опциональный и работает иначе:** он отправляет **текст транскрипции** во внешний LLM-провайдер (OpenRouter). Аудио при этом по-прежнему никуда не уходит. Если конспект не используется, ничего по сети не отправляется (кроме первичного скачивания модели).

При этом **при первом использовании модели требуется её скачать**, поэтому для первоначальной настройки необходимо подключение к интернету.

## License

This project is licensed under the MIT License.

---

## Author

**TimoshaK**
littlesonofsun@gmail.com
@TSon_of_The_Sun - tg
