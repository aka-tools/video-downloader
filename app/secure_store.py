# Copyright (c) 2026 AKA. All rights reserved.
# Part of Video Downloader - see LICENSE.txt. Unauthorised copying or modification is prohibited.
"""
Encrypts small secrets (the saved Canvas login) with Windows DPAPI.

DPAPI ties the encryption to the current Windows user account on this PC:
  * no password or key is stored by the app,
  * another user on the same PC cannot decrypt it,
  * copying the file to another computer makes it useless.
"""
import ctypes
import sys

_CRYPTPROTECT_UI_FORBIDDEN = 0x01
_ENTROPY = b"VideoDownloader/v1"  # app-specific: other apps using DPAPI can't read our blob by accident


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _to_blob(data):
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def available():
    return sys.platform == "win32"


def protect(data: bytes) -> bytes:
    if not available():
        raise OSError("Encrypted storage requires Windows")
    inp, _k1 = _to_blob(data)
    ent, _k2 = _to_blob(_ENTROPY)
    out = _Blob()
    if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(inp), ctypes.c_wchar_p("VideoDownloader login"), ctypes.byref(ent),
            None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def unprotect(data: bytes) -> bytes:
    if not available():
        raise OSError("Encrypted storage requires Windows")
    inp, _k1 = _to_blob(data)
    ent, _k2 = _to_blob(_ENTROPY)
    out = _Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(inp), None, ctypes.byref(ent),
            None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)
