from __future__ import annotations

import sys
import winreg
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SmartEmoji"


def _launcher_command() -> str:
    # PyInstaller --onefile: sys.executable IS SmartEmoji.exe — just run it.
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / ".venv" / "Scripts" / "pythonw.exe",
        project_root.parent / "SmartClipboard" / ".venv" / "Scripts" / "pythonw.exe",
        Path(sys.executable).with_name("pythonw.exe"),
        Path(sys.executable),
    ]
    exe = next((p for p in candidates if p.exists()), Path(sys.executable))
    main_py = project_root / "main.py"
    return f'"{exe}" "{main_py}"'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> None:
    cmd = _launcher_command()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)


def disable() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
