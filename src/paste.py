from __future__ import annotations

import ctypes
from ctypes import wintypes


user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_V = 0x56


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("_pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def _make_input(vk: int, flags: int, w_scan: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(vk, w_scan, flags, 0, None)
    return inp


def _send(sequence: list[INPUT]) -> None:
    if not sequence:
        return
    arr = (INPUT * len(sequence))(*sequence)
    user32.SendInput(len(sequence), ctypes.byref(arr), ctypes.sizeof(INPUT))


def send_ctrl_v() -> None:
    """Release held modifiers, then synthesize Ctrl+V. Used for image pastes."""
    _send([
        _make_input(VK_MENU, KEYEVENTF_KEYUP),
        _make_input(VK_SHIFT, KEYEVENTF_KEYUP),
        _make_input(VK_LWIN, KEYEVENTF_KEYUP),
        _make_input(VK_RWIN, KEYEVENTF_KEYUP),
        _make_input(VK_CONTROL, KEYEVENTF_KEYUP),
        _make_input(VK_CONTROL, 0),
        _make_input(VK_V, 0),
        _make_input(VK_V, KEYEVENTF_KEYUP),
        _make_input(VK_CONTROL, KEYEVENTF_KEYUP),
    ])


def send_unicode_text(text: str) -> None:
    """Type `text` into the foreground window using KEYEVENTF_UNICODE.

    This bypasses the clipboard and does NOT press Ctrl, so it avoids the
    'browser edit control re-selects on focus → Ctrl+V replaces selection'
    failure mode that afflicts Ctrl+V-based paste tools.

    Non-BMP code points (like most emojis) are sent as UTF-16 surrogate pairs,
    which is what Windows expects for KEYEVENTF_UNICODE.
    """
    if not text:
        return
    inputs: list[INPUT] = []
    # Release any stuck modifiers first so the synthetic unicode keystrokes
    # don't get combined with a physically-held Ctrl/Alt/Shift.
    for vk in (VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN, VK_CONTROL):
        inputs.append(_make_input(vk, KEYEVENTF_KEYUP))
    # Emit each UTF-16 code unit; Windows reassembles surrogate pairs into
    # the non-BMP code point at the receiving edit control.
    utf16 = text.encode("utf-16-le")
    for i in range(0, len(utf16), 2):
        code_unit = int.from_bytes(utf16[i:i + 2], "little")
        inputs.append(_make_input(0, KEYEVENTF_UNICODE, w_scan=code_unit))
        inputs.append(_make_input(0, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, w_scan=code_unit))
    _send(inputs)
