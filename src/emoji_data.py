from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Emoji:
    id: str
    name: str
    codes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    rank: int = 10_000
    char: Optional[str] = None        # unicode emojis
    image_path: Optional[str] = None  # user-added images

    @property
    def is_image(self) -> bool:
        return self.image_path is not None


def _bundled_path() -> Path:
    # In a PyInstaller --onefile bundle the assets live under sys._MEIPASS;
    # otherwise they're alongside the source tree.
    meipass = getattr(sys, "_MEIPASS", None)
    base = Path(meipass) if meipass else Path(__file__).resolve().parent.parent
    return base / "assets" / "emojis.json"


class EmojiIndex:
    """Bundled Unicode emojis + user-contributed aliases and image emojis.

    Call `reload()` to pick up changes from CustomStore after the user edits
    settings.
    """

    def __init__(self, custom_store=None):
        self._custom_store = custom_store
        self._all: list[Emoji] = []
        self.reload()

    def reload(self) -> None:
        self._all = list(self._load_bundled())
        if self._custom_store is not None:
            self._merge_customs(self._custom_store)

    def _load_bundled(self) -> list[Emoji]:
        path = _bundled_path()
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[emoji_data] failed to load {path}: {e}")
            return []
        out: list[Emoji] = []
        for r in raw:
            out.append(Emoji(
                id=r["id"],
                name=r.get("name", ""),
                codes=list(r.get("codes", [])),
                keywords=list(r.get("keywords", [])),
                rank=int(r.get("rank", 10_000)),
                char=r.get("char"),
            ))
        return out

    def _merge_customs(self, store) -> None:
        # Aliases: add user codes to existing unicode emojis.
        by_char: dict[str, Emoji] = {e.char: e for e in self._all if e.char}
        for code, char in store.aliases().items():
            target = by_char.get(char)
            if target and code not in target.codes:
                target.codes.insert(0, code)
        # Image emojis: append as new entries.
        for img in store.images():
            self._all.append(Emoji(
                id=img["id"],
                name=img.get("name", ""),
                codes=list(img.get("codes", [])),
                keywords=[],
                rank=0,  # user-added images sort high
                image_path=img["path"],
            ))

    def all(self) -> list[Emoji]:
        return list(self._all)

    def by_id(self, emoji_id: str) -> Optional[Emoji]:
        for e in self._all:
            if e.id == emoji_id:
                return e
        return None

    def search(self, query: str, limit: int = 500) -> list[Emoji]:
        """Score = (bucket, rank). Lower bucket = better match.

        0: exact shortcode match
        1: name starts with query
        2: shortcode starts with query
        3: name contains query
        4: keyword exact match
        5: keyword contains query
        """
        q = query.strip().lower()
        if not q:
            return sorted(self._all, key=lambda e: e.rank)[:limit]

        scored: list[tuple[tuple[int, int], Emoji]] = []
        for e in self._all:
            bucket = self._score(e, q)
            if bucket < 99:
                scored.append(((bucket, e.rank), e))
        scored.sort(key=lambda x: x[0])
        return [e for _, e in scored[:limit]]

    @staticmethod
    def _score(e: Emoji, q: str) -> int:
        name = e.name.lower()
        if any(c.lower() == q for c in e.codes):
            return 0
        if name.startswith(q):
            return 1
        if any(c.lower().startswith(q) for c in e.codes):
            return 2
        if q in name:
            return 3
        if any(k.lower() == q for k in e.keywords):
            return 4
        if any(q in k.lower() for k in e.keywords):
            return 5
        if any(q in c.lower() for c in e.codes):
            return 5
        return 99
