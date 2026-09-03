"""Persistent application config for pluggable LLM API settings."""

import json
import os

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "app_config.json",
)

DEFAULT_CONFIG = {
    "llm": {
        "api_key": "",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "enabled": False,
    }
}


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT_CONFIG))

    for key, value in DEFAULT_CONFIG.items():
        cfg.setdefault(key, value)
    for key, value in DEFAULT_CONFIG["llm"].items():
        cfg["llm"].setdefault(key, value)
    return cfg


def save_config(cfg: dict) -> None:
    normalized = json.loads(json.dumps(DEFAULT_CONFIG))
    normalized["llm"].update(cfg.get("llm", {}))
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
