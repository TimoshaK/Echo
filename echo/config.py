"""Persistent application config for pluggable LLM API settings."""

import json
from pathlib import Path

# D-01: app_config.json lives in the REPOSITORY ROOT — one level above the echo/ package.
# Do NOT use Path(__file__).parent here: that resolves to echo/app_config.json, which does
# not exist, and load_config() would silently fall back to DEFAULT_CONFIG (empty API key),
# breaking REFR-03 with no visible error.
CONFIG_PATH = Path(__file__).resolve().parent.parent / "app_config.json"

DEFAULT_CONFIG = {
    "llm": {
        "api_key": "",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "enabled": False,
        "summary_preset": "free",
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
