from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QThread, Signal


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012


MOD_NAMES: dict[str, int] = {
    "ctrl": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
}

# Virtual-key name ↔ code. Covers what we'd reasonably bind from a keyboard.
VK_BY_NAME: dict[str, int] = {
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46,
    "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C,
    "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50, "q": 0x51, "r": 0x52,
    "s": 0x53, "t": 0x54, "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58,
    "y": 0x59, "z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "space": 0x20, "tab": 0x09, "enter": 0x0D, "backspace": 0x08,
    "semicolon": 0xBA,   # ;:
    "equals": 0xBB,      # =+
    "comma": 0xBC,       # ,<
    "minus": 0xBD,       # -_
    "period": 0xBE,      # .>
    "slash": 0xBF,       # /?
    "backtick": 0xC0,    # `~
    "lbracket": 0xDB,    # [{
    "backslash": 0xDC,   # \|
    "rbracket": 0xDD,    # ]}
    "quote": 0xDE,       # '"
}

NAME_BY_VK: dict[int, str] = {v: k for k, v in VK_BY_NAME.items()}


@dataclass(frozen=True)
class HotkeySpec:
    id: int
    mods: int
    vk: int
    name: str = "open_picker"

    @staticmethod
    def from_names(id: int, mod_names: list[str], key_name: str, action: str = "open_picker") -> "HotkeySpec":
        mods = 0
        for m in mod_names:
            mods |= MOD_NAMES[m.lower()]
        vk = VK_BY_NAME[key_name.lower()]
        return HotkeySpec(id=id, mods=mods, vk=vk, name=action)

    def display(self) -> str:
        parts: list[str] = []
        if self.mods & MOD_CONTROL:
            parts.append("Ctrl")
        if self.mods & MOD_ALT:
            parts.append("Alt")
        if self.mods & MOD_SHIFT:
            parts.append("Shift")
        if self.mods & MOD_WIN:
            parts.append("Win")
        key = NAME_BY_VK.get(self.vk, f"0x{self.vk:02X}")
        key_label = {
            "semicolon": ";",
            "comma": ",",
            "period": ".",
            "slash": "/",
            "minus": "-",
            "equals": "=",
            "backtick": "`",
            "quote": "'",
            "backslash": "\\",
            "lbracket": "[",
            "rbracket": "]",
            "space": "Space",
            "tab": "Tab",
            "enter": "Enter",
            "backspace": "Backspace",
        }.get(key, key.upper() if len(key) == 1 else key.capitalize())
        parts.append(key_label)
        return "+".join(parts)


class HotkeyThread(QThread):
    hotkey_fired = Signal(str)

    def __init__(self, specs: list[HotkeySpec]):
        super().__init__()
        self._specs = list(specs)
        self._thread_id = 0
        self._id_to_name = {s.id: s.name for s in specs}

    def run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        registered: list[int] = []
        for spec in self._specs:
            ok = user32.RegisterHotKey(None, spec.id, spec.mods | MOD_NOREPEAT, spec.vk)
            if ok:
                registered.append(spec.id)
            else:
                err = ctypes.get_last_error()
                print(f"[hotkeys] failed to register {spec.name} ({spec.display()}): err={err}")

        msg = wintypes.MSG()
        try:
            while True:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
                if msg.message == WM_HOTKEY:
                    name = self._id_to_name.get(int(msg.wParam))
                    if name:
                        self.hotkey_fired.emit(name)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            for hid in registered:
                user32.UnregisterHotKey(None, hid)

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)


class HotkeyManager(QObject):
    hotkey = Signal(str)

    def __init__(self, specs: list[HotkeySpec], parent: QObject | None = None):
        super().__init__(parent)
        self._specs = list(specs)
        self._thread: HotkeyThread | None = None

    def start(self) -> None:
        self._thread = HotkeyThread(self._specs)
        self._thread.hotkey_fired.connect(self.hotkey)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is not None:
            self._thread.stop()
            self._thread.wait(1000)
            self._thread = None

    def replace(self, specs: list[HotkeySpec]) -> None:
        self.stop()
        self._specs = list(specs)
        self.start()
