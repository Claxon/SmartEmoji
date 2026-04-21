from __future__ import annotations

import json
import math
import os
import tempfile
import time
from pathlib import Path

from .config import app_data_dir


HALF_LIFE_DAYS = 14.0


def _usage_path() -> Path:
    return app_data_dir() / "usage.json"


class UsageStore:
    """Tracks how often each emoji is picked and when it was last used.

    Uses a time-decayed score so the "most used" grid adapts to what the
    user has been picking recently, not just all-time.
    """

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        path = _usage_path()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[usage_store] failed to read {path}: {e}")
            return
        if isinstance(raw, dict):
            self._data = {k: v for k, v in raw.items() if isinstance(v, dict)}

    def flush(self) -> None:
        if not self._dirty:
            return
        path = _usage_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self._data, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(prefix=".usage", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, path)
            self._dirty = False
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def record(self, emoji_id: str) -> None:
        entry = self._data.setdefault(emoji_id, {"count": 0, "last": 0.0})
        entry["count"] = int(entry.get("count", 0)) + 1
        entry["last"] = time.time()
        self._dirty = True

    def score(self, emoji_id: str) -> float:
        entry = self._data.get(emoji_id)
        if not entry:
            return 0.0
        count = float(entry.get("count", 0))
        last = float(entry.get("last", 0.0))
        if last <= 0 or count <= 0:
            return 0.0
        age_days = max(0.0, (time.time() - last) / 86400.0)
        decay = 0.5 ** (age_days / HALF_LIFE_DAYS)
        return count * decay

    def sort_key(self, emoji_id: str) -> float:
        """Higher = more recent/frequent. Return value is negated so the
        default `sorted()` ascending order puts most-used first."""
        return -self.score(emoji_id)
