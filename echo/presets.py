DEFAULT_PRESET = "free"

# Единственный источник истины по пресетам конспекта: порядок ключей dict =
# порядок пунктов в Combobox (Task 3). Ключи разделов — ASCII, потому что они
# уходят и в json_schema-слой, и в json_object-инструкцию; русские заголовки
# берутся из "title" при рендере.
SUMMARY_PRESETS = {
    "daily": {
        "label": "Дейли",
        "title": "ДЕЙЛИ",
        "hint": "дейли-встречи",
        "schema_name": "daily_conspect",
        "sections": [
            {"key": "tasks", "title": "AFD", "kind": "list"},
            {"key": "decisions", "title": "РЕШЕНИЯ", "kind": "list"},
            {"key": "blockers", "title": "БЛОКЕРЫ", "kind": "list"},
        ],
    },
    "lecture": {
        "label": "Лекция",
        "title": "ЛЕКЦИЯ",
        "hint": "лекции",
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
        "hint": "интервью",
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
        "hint": "встречи с клиентом",
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
        "hint": "свободного конспекта",
        "schema_name": None,
        "sections": [],
    },
}
