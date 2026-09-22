"""Persistent application config for pluggable LLM API settings."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# D-01: app_config.json lives in the REPOSITORY ROOT — one level above the echo/ package.
# Do NOT use Path(__file__).parent here: that resolves to echo/app_config.json, which does
# not exist, and load_config() would silently fall back to DEFAULT_CONFIG (empty API key),
# breaking REFR-03 with no visible error.
CONFIG_PATH = Path(__file__).resolve().parent.parent / "app_config.json"

# SEC-01: права владельца для файла с API-ключом.
CONFIG_FILE_MODE = 0o600

DEFAULT_CONFIG = {
    "llm": {
        "api_key": "",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "enabled": False,
        "summary_preset": "free",
    }
}


class ConfigCorruptError(RuntimeError):
    """app_config.json существует, но прочитать его не удалось (SEC-04).

    Отдельный тип вместо молчаливого отката к DEFAULT_CONFIG: иначе потеря
    API-ключа выглядит для пользователя как "консоль просто перестала работать",
    а причина (повреждённый файл) не видна вообще.
    """

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"Файл настроек повреждён или недоступен ({path}): {detail}")


def load_config() -> dict:
    """Прочитать конфиг, явно сообщая о повреждении (SEC-04).

    FileNotFoundError -> дефолты: первый запуск это не ошибка.
    Любая другая причина, по которой нельзя получить корректный объект
    (нет доступа, битая кодировка, битый JSON, не тот тип на верхнем уровне
    или в секции "llm"), -> ConfigCorruptError. Молчаливый откат запрещён:
    он скрывает потерю ключа и может отправить запрос на чужой дефолтный URL.
    """
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigCorruptError(CONFIG_PATH, f"файл недоступен: {e}") from e

    try:
        cfg = json.loads(raw)
    except ValueError as e:
        raise ConfigCorruptError(CONFIG_PATH, f"некорректный JSON: {e}") from e

    if not isinstance(cfg, dict):
        raise ConfigCorruptError(CONFIG_PATH, "корень файла должен быть объектом JSON")

    llm = cfg.get("llm")
    if llm is not None and not isinstance(llm, dict):
        raise ConfigCorruptError(CONFIG_PATH, "секция 'llm' должна быть объектом JSON")

    # Глубокие копии: DEFAULT_CONFIG не должен оказаться тем же объектом, что и
    # результат, иначе запись через результат мутирует дефолты (было в старом коде).
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    for key, value in cfg.items():
        if key != "llm":
            merged[key] = value
    merged["llm"] = {**DEFAULT_CONFIG["llm"], **cfg.get("llm", {})}
    return merged


def _restrict_windows_acl(path: Path) -> None:
    """Best-effort owner-only ACL on Windows (SEC-01).

    `os.chmod(0o600)` на Windows не работает: режимные биты не поддерживаются
    (проверено — st_mode остаётся 0o666). Поэтому ACL сужаем через icacls:
    снимаем наследование и выдаём полный доступ только текущему пользователю.

    Любая неудача (нет icacls, не-NTFS, политика) НЕ должна срывать сохранение
    только что введённого ключа — исключения глушим осознанно.
    """
    if os.name != "nt":
        return
    username = os.environ.get("USERNAME") or ""
    icacls = shutil.which("icacls")
    if not icacls or not username:
        return
    try:
        subprocess.run(
            [icacls, str(path), "/inheritance:r", "/grant:r", f"{username}:F"],
            capture_output=True,
            check=False,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def _atomic_write_secure(path: Path, text: str, mode: int = CONFIG_FILE_MODE) -> None:
    """Записать файл атомарно и с правами владельца (SEC-01).

    Порядок важен: mkstemp в ТОЙ ЖЕ папке (os.replace атомарен только в пределах
    тома), запись, fsync, chmod, затем os.replace. Пока не выполнен replace,
    целевой файл остаётся прежним; если что-то упало — временный файл удаляется,
    а исходный конфиг не тронут (никаких частично записанных ключей).
    """
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=".app_config.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(tmp_path, mode)
        except OSError:
            pass
        os.replace(tmp_path, path)
    except BaseException:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise
    _restrict_windows_acl(path)


def save_config(cfg: dict) -> None:
    normalized = json.loads(json.dumps(DEFAULT_CONFIG))
    normalized["llm"].update(cfg.get("llm", {}) or {})
    data = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_secure(CONFIG_PATH, data)
