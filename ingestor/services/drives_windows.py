from __future__ import annotations

import os
import string
import ctypes
from ctypes import wintypes


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GetLogicalDrives = kernel32.GetLogicalDrives
GetLogicalDrives.restype = wintypes.DWORD

GetVolumeInformationW = kernel32.GetVolumeInformationW
GetVolumeInformationW.argtypes = [
    wintypes.LPCWSTR,  # lpRootPathName
    wintypes.LPWSTR,   # lpVolumeNameBuffer
    wintypes.DWORD,    # nVolumeNameSize
    ctypes.POINTER(wintypes.DWORD),  # lpVolumeSerialNumber
    ctypes.POINTER(wintypes.DWORD),  # lpMaximumComponentLength
    ctypes.POINTER(wintypes.DWORD),  # lpFileSystemFlags
    wintypes.LPWSTR,   # lpFileSystemNameBuffer
    wintypes.DWORD,    # nFileSystemNameSize
]
GetVolumeInformationW.restype = wintypes.BOOL


def list_windows_drives() -> list[tuple[str, str]]:
    """
    Returns list of (root, label) like ("E:\\", "MyBook 2").
    Includes fixed + removable drives. Label may be "" if unknown.
    """
    drives_bitmask = GetLogicalDrives()
    results: list[tuple[str, str]] = []

    for letter in string.ascii_uppercase:
        if not (drives_bitmask & (1 << (ord(letter) - ord("A")))):
            continue

        root = f"{letter}:\\"
        if not os.path.exists(root) or letter == 'C':
            continue

        vol_name_buf = ctypes.create_unicode_buffer(261)
        fs_name_buf = ctypes.create_unicode_buffer(261)
        serial = wintypes.DWORD()
        max_comp = wintypes.DWORD()
        fs_flags = wintypes.DWORD()

        ok = GetVolumeInformationW(
            root,
            vol_name_buf,
            len(vol_name_buf),
            ctypes.byref(serial),
            ctypes.byref(max_comp),
            ctypes.byref(fs_flags),
            fs_name_buf,
            len(fs_name_buf),
        )

        label = vol_name_buf.value.strip() if ok else ""
        results.append((root, label))

    return results

# --- add below list_windows_drives() ---

GetDriveTypeW = kernel32.GetDriveTypeW
GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
GetDriveTypeW.restype = wintypes.UINT

DRIVE_REMOVABLE = 2  # per WinAPI


def list_removable_drives() -> list[tuple[str, str]]:
    """
    Returns removable drives only (typically SD card readers / USB sticks):
    [("G:\\", "SONY_CARD"), ...]
    """
    all_drives = list_windows_drives()
    removable: list[tuple[str, str]] = []
    for root, label in all_drives:
        try:
            dtype = GetDriveTypeW(root)
            if dtype == DRIVE_REMOVABLE:
                removable.append((root, label))
        except Exception:
            continue
    return removable


def drive_display(root: str, label: str) -> str:
    letter = root[:2]  # "E:"
    if label:
        return f"{letter} - {label}"
    return f"{letter} - (No Label)"


def get_drive_space(root: str) -> tuple[int, int]:
    """
    Returns (total_bytes, free_bytes) for a drive root like 'E:\\'
    Uses Python's disk_usage (works great for drive roots).
    """
    import shutil
    usage = shutil.disk_usage(root)
    return usage.total, usage.free