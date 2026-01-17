from pathlib import Path
import json
import time
from typing import Optional

try:
    import redis
except ImportError:
    redis = None

ROOT = Path(__file__).resolve().parents[3]
COOLDOWNS_FILE = ROOT / "data" / "cooldowns.json"
COOLDOWNS_FILE.parent.mkdir(parents=True, exist_ok=True)
if not COOLDOWNS_FILE.exists():
    COOLDOWNS_FILE.write_text(json.dumps({}), encoding="utf-8")

_REDIS = None
if redis is not None:
    try:
        _REDIS = redis.Redis()
    except Exception:
        _REDIS = None


def _read_file():
    try:
        return json.loads(COOLDOWNS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_file(data):
    COOLDOWNS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def check_cooldown(user_id: str, category: str, action: str) -> int:
    """Return remaining seconds, 0 if not in cooldown"""
    key = f"cooldown:{user_id}:{category}:{action}"
    # Redis check
    if _REDIS:
        try:
            ttl = _REDIS.ttl(key)
            if ttl is None:
                return 0
            return max(0, int(ttl))
        except Exception:
            pass
    # file check
    data = _read_file()
    val = data.get(key)
    if not val:
        return 0
    if time.time() > val:
        # expired
        data.pop(key, None)
        _write_file(data)
        return 0
    return int(val - time.time())


def set_cooldown(user_id: str, category: str, action: str, duration: int = 60):
    key = f"cooldown:{user_id}:{category}:{action}"
    if _REDIS:
        try:
            _REDIS.setex(key, duration, 1)
            return
        except Exception:
            pass
    data = _read_file()
    data[key] = int(time.time() + duration)
    _write_file(data)
