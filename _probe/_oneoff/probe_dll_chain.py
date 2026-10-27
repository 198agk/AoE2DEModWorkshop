# -*- coding: utf-8 -*-
"""Which dependency actually fails to load?

`STATUS_DLL_NOT_FOUND` (0xC0000135) names no file, and the PE import table
only lists the first layer.  So walk the transitive list by hand with
LoadLibraryEx, which answers per file, and report the first one that fails.
"""
import ctypes
import os
import sys

DIST = r"D:\Software\AI\帝国项目\_build\native2\app_entry.dist"

# Everything the import tables of the exe + python312.dll + vcruntime140.dll name.
NAMES = [
    "KERNEL32.dll", "msvcrt.dll", "SHELL32.dll", "python312.dll",
    "VERSION.dll", "WS2_32.dll", "bcrypt.dll", "ADVAPI32.dll",
    "VCRUNTIME140.dll", "vcruntime140.dll", "VCRUNTIME140_1.dll",
    "ucrtbase.dll",
    "api-ms-win-core-path-l1-1-0.dll",
    "api-ms-win-crt-stdio-l1-1-0.dll",
    "api-ms-win-crt-environment-l1-1-0.dll",
    "api-ms-win-crt-heap-l1-1-0.dll",
    "api-ms-win-crt-runtime-l1-1-0.dll",
    "api-ms-win-crt-locale-l1-1-0.dll",
    "api-ms-win-crt-string-l1-1-0.dll",
    "api-ms-win-crt-convert-l1-1-0.dll",
    "api-ms-win-crt-math-l1-1-0.dll",
    "api-ms-win-crt-time-l1-1-0.dll",
    "api-ms-win-crt-process-l1-1-0.dll",
    "api-ms-win-crt-conio-l1-1-0.dll",
    "api-ms-win-crt-filesystem-l1-1-0.dll",
]

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
k32.LoadLibraryExW.restype = ctypes.c_void_p

# LOAD_LIBRARY_SEARCH_DEFAULT_DIRS | LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR
FLAGS = 0x00001000 | 0x00000100

print("dist:", DIST)
print("%-42s %-10s %s" % ("name", "result", "resolved path"))
print("-" * 78)
failed = []
for name in NAMES:
    local = os.path.join(DIST, name)
    h = k32.LoadLibraryExW(local if os.path.isfile(local) else name, None, FLAGS)
    if h:
        buf = ctypes.create_unicode_buffer(1024)
        k32.GetModuleFileNameW(ctypes.c_void_p(h), buf, 1024)
        print("%-42s %-10s %s" % (name, "ok", buf.value))
    else:
        err = ctypes.get_last_error()
        print("%-42s %-10s error %d" % (name, "FAILED", err))
        failed.append((name, err))

print("-" * 78)
if failed:
    print("FAILED:", failed)
else:
    print("every named dependency loads")

# And the exe itself, which is the one that matters.
exe = os.path.join(DIST, "aoe2mod-engine.exe")
os.add_dll_directory(DIST)
try:
    h = k32.LoadLibraryExW(exe, None, FLAGS)
    print("\nengine exe:", "loaded" if h else "FAILED err=%d" % ctypes.get_last_error())
except OSError as exc:
    print("\nengine exe: OSError", exc)
