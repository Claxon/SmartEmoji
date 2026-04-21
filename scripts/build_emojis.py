"""One-off script: fetch emojilib data and write assets/emojis.json.

Run from the project root:

    python scripts/build_emojis.py

Writes:  assets/emojis.json

The produced file is committed to the repo; end users don't need to re-run
this. We only re-run when we want to refresh the emoji set (e.g. after a new
Unicode revision).
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path


EMOJILIB_URL = "https://raw.githubusercontent.com/muan/emojilib/main/dist/emoji-en-US.json"

# Hand-curated "starter" popularity: these float to the top of the grid
# before the user has recorded any usage of their own. Ordered by a rough
# approximation of daily-use frequency in Western text.
POPULAR: list[str] = [
    "😂", "❤️", "🤣", "👍", "😭", "🙏", "😘", "🥰", "😍", "😊",
    "🎉", "😁", "💕", "🥺", "😅", "🔥", "☺️", "🤦", "♥️", "🤷",
    "🙄", "😆", "🤗", "😉", "🎂", "🤔", "👏", "🙂", "😳", "🥳",
    "😎", "👌", "💜", "😔", "💪", "✨", "💖", "👀", "😋", "😏",
    "😢", "👉", "💗", "😩", "💯", "🌹", "💞", "🎈", "💙", "😃",
    "😡", "💐", "😜", "🙈", "🤞", "😄", "🤤", "🙌", "🤪", "❣️",
    "😀", "💋", "💀", "👇", "💔", "😌", "💓", "🤩", "🙃", "😬",
    "😱", "😴", "🤭", "😐", "🌞", "😒", "😇", "🌸", "😈", "🎶",
    "✌️", "🎊", "🥵", "😞", "💚", "☀️", "🖤", "💰", "😚", "👑",
    "🎁", "💥", "🙋", "☹️", "😑", "🥴", "👈", "💩", "✅", "👋",
    "🤮", "😤", "🤢", "🌟", "❗", "🤬", "🧡", "🤫", "🐢", "😵",
    "💫", "🫶", "🫡", "🫠", "🫣", "🤡", "🥲", "🥹", "🤝", "✋",
    "💎", "🍀", "⭐", "💍", "🎵", "💘", "🌈", "💦", "😪", "⚡",
    "👎", "📷", "🤯", "🤟", "😕", "🎮", "🍎", "🍕", "🍔", "🍰",
    "🍺", "☕", "🏆", "🎯", "👻", "🫂", "💭", "💬", "💤", "🍻",
]


def fetch_emojilib() -> dict[str, list[str]]:
    req = urllib.request.Request(EMOJILIB_URL, headers={"User-Agent": "SmartEmoji-build/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def emoji_id(char: str) -> str:
    return hashlib.md5(char.encode("utf-8")).hexdigest()[:12]


def build() -> list[dict]:
    data = fetch_emojilib()
    pop_index = {c: i for i, c in enumerate(POPULAR)}
    records: list[dict] = []
    for i, (char, keywords) in enumerate(data.items()):
        # emojilib convention: first keyword is the canonical name (snake_case),
        # the rest are search aliases.
        kws = list(keywords) if isinstance(keywords, list) else []
        name = kws[0].replace("_", " ") if kws else char
        codes = [kws[0]] if kws else []
        other = [k for k in kws[1:] if isinstance(k, str)]
        rank = pop_index.get(char, 1000 + i)
        records.append({
            "id": emoji_id(char),
            "char": char,
            "name": name,
            "codes": codes,
            "keywords": other,
            "rank": rank,
        })
    records.sort(key=lambda r: (r["rank"], r["name"]))
    return records


def main() -> int:
    out_path = Path(__file__).resolve().parent.parent / "assets" / "emojis.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = build()
    out_path.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(records)} emojis to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
