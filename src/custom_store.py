from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from .config import app_data_dir


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def _custom_path() -> Path:
    return app_data_dir() / "custom.json"


def _images_dir() -> Path:
    d = app_data_dir() / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


class CustomStore:
    """User-defined aliases (extra shortcodes for existing unicode emojis)
    and image emojis (user PNGs/JPGs that paste as images).
    """

    def __init__(self):
        self._aliases: dict[str, str] = {}    # shortcode -> emoji char
        self._images: list[dict] = []          # list of {id,name,codes,path}
        self._load()

    def _load(self) -> None:
        path = _custom_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[custom_store] failed to read {path}: {e}")
            return
        self._aliases = dict(data.get("aliases", {}))
        images = data.get("images", [])
        self._images = [
            {
                "id": img.get("id") or uuid.uuid4().hex[:12],
                "name": img.get("name", ""),
                "codes": list(img.get("codes", [])),
                "path": img.get("path", ""),
            }
            for img in images
            if img.get("path") and Path(img["path"]).exists()
        ]

    def _save(self) -> None:
        path = _custom_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(
            {"aliases": self._aliases, "images": self._images},
            ensure_ascii=False,
            indent=2,
        )
        fd, tmp = tempfile.mkstemp(prefix=".custom", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)

    def images(self) -> list[dict]:
        return [dict(img) for img in self._images]

    def set_alias(self, code: str, emoji_char: str) -> None:
        code = code.strip().lower()
        if not code:
            return
        self._aliases[code] = emoji_char
        self._save()

    def remove_alias(self, code: str) -> None:
        self._aliases.pop(code.strip().lower(), None)
        self._save()

    def add_image(self, src_path: str, name: str, codes: list[str]) -> dict:
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(src_path)
        ext = src.suffix.lower()
        if ext not in IMAGE_EXTS:
            raise ValueError(f"Unsupported extension: {ext}")
        img_id = uuid.uuid4().hex[:12]
        dest = _images_dir() / f"{img_id}{ext}"
        shutil.copy2(src, dest)
        entry = {
            "id": img_id,
            "name": name.strip() or src.stem,
            "codes": [c.strip().lower() for c in codes if c.strip()],
            "path": str(dest),
        }
        self._images.append(entry)
        self._save()
        return entry

    def remove_image(self, image_id: str) -> None:
        keep: list[dict] = []
        for img in self._images:
            if img["id"] == image_id:
                try:
                    Path(img["path"]).unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                keep.append(img)
        self._images = keep
        self._save()

    def update_image(self, image_id: str, *, name: Optional[str] = None, codes: Optional[list[str]] = None) -> None:
        for img in self._images:
            if img["id"] == image_id:
                if name is not None:
                    img["name"] = name.strip() or img["name"]
                if codes is not None:
                    img["codes"] = [c.strip().lower() for c in codes if c.strip()]
                break
        self._save()
