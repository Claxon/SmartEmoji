from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .hotkeys import HotkeySpec


APP_DIR_ENV = "APPDATA"
APP_FOLDER = "SmartEmoji"


def app_data_dir() -> Path:
    base = os.environ.get(APP_DIR_ENV) or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / APP_FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return app_data_dir() / "config.json"


@dataclass
class HotkeyConfig:
    mods: list[str]
    key: str
    action: str = "open_picker"


@dataclass
class Config:
    hotkeys: list[HotkeyConfig] = field(default_factory=list)
    grid_cols: int = 10
    grid_rows: int = 5
    show_caption: bool = True

    def to_dict(self) -> dict:
        return {
            "hotkeys": [{"mods": h.mods, "key": h.key, "action": h.action} for h in self.hotkeys],
            "grid_cols": self.grid_cols,
            "grid_rows": self.grid_rows,
            "show_caption": self.show_caption,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        hotkeys = [
            HotkeyConfig(mods=list(h.get("mods", [])), key=h.get("key", ""), action=h.get("action", "open_picker"))
            for h in data.get("hotkeys", [])
        ]
        if not hotkeys:
            hotkeys = [HotkeyConfig(mods=["ctrl"], key="semicolon", action="open_picker")]
        return cls(
            hotkeys=hotkeys,
            grid_cols=int(data.get("grid_cols", 10)),
            grid_rows=int(data.get("grid_rows", 5)),
            show_caption=bool(data.get("show_caption", True)),
        )

    def hotkey_specs(self) -> list[HotkeySpec]:
        specs: list[HotkeySpec] = []
        for i, h in enumerate(self.hotkeys, start=1):
            try:
                specs.append(HotkeySpec.from_names(id=i, mod_names=h.mods, key_name=h.key, action=h.action))
            except KeyError:
                print(f"[config] skipping invalid hotkey {h}")
        return specs


def load() -> Config:
    path = config_path()
    if not path.exists():
        cfg = Config.from_dict({})
        save(cfg)
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return Config.from_dict({})
    return Config.from_dict(data)


def save(cfg: Config) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(prefix=".config", dir=str(path.parent))
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
