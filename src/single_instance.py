from __future__ import annotations

import ctypes
from ctypes import wintypes


_MUTEX_NAME = r"Global\SmartEmoji-singleton-v1"
_ERROR_ALREADY_EXISTS = 183

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

# Held for the life of the process — releasing this handle releases the
# named mutex, which would let a second instance slip in. Keep a strong
# module-level reference.
_held_handle: int | None = None


def try_acquire() -> bool:
    """Try to become the single running instance.

    Returns True if we acquired the lock (no other instance was running) and
    the caller should proceed. Returns False if another SmartEmoji is already
    running and the caller should exit quietly.
    """
    global _held_handle
    # The backslash in the name means "Global\..." — a session-wide namespace.
    # For a per-user app we could use "Local\..." but Global is fine because
    # the mutex name is specific enough to avoid cross-user collisions.
    handle = _kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    last_err = ctypes.get_last_error()
    if not handle:
        # Fail-open: if the syscall failed for some reason, let the app run.
        # Duplicate instances are less bad than mysteriously failing to start.
        return True
    if last_err == _ERROR_ALREADY_EXISTS:
        _kernel32.CloseHandle(handle)
        return False
    _held_handle = handle
    return True


def release() -> None:
    """Release the mutex. Optional — the OS cleans it up on process exit."""
    global _held_handle
    if _held_handle is not None:
        _kernel32.CloseHandle(_held_handle)
        _held_handle = None
