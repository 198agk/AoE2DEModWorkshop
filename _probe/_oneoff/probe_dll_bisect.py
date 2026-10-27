# -*- coding: utf-8 -*-
"""Bisect by dependency set: which import makes the engine exe refuse to start?

`0xC0000135` means the loader could not satisfy a static import.  LoadLibraryEx
on the exe succeeded, which is odd, so the failure may be in the *static* import
table entry that is only resolved at process start (delay-load vs regular), or
in a DLL that only the loader looks for by full name.

Rather than guess, walk every DLL in the dist and load them the way the loader
would, and report the first failure with its error code.
"""
import ctypes
import os

DIST = r"D:\Software\AI\帝国项目\_build\native2\app_entry.dist"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
k32.LoadLibraryExW.restype = ctypes.c_void_p
k32.AddDllDirectory.argtypes = [ctypes.c_wchar_p]
k32.AddDllDirectory.restype = ctypes.c_void_p

# Same flags the loader uses for a normal process start with the app dir first.
FLAGS = 0x00000001 | 0x00000008 | 0x00000100   # DLL_LOAD_DIR|ALTERED|DEFAULT_DIRS
cookie = k32.AddDllDirectory(DIST)
print("AddDllDirectory:", cookie, "err", ctypes.get_last_error())

print("%-26s %-8s %s" % ("file", "result", "err"))
print("-" * 60)
bad = []
for name in sorted(os.listdir(DIST)):
    if not (name.lower().endswith(".pyd") or name.lower().endswith(".dll")):
        continue
    path = os.path.join(DIST, name)
    ctypes.set_last_error(0)
    h = k32.LoadLibraryExW(path, None, FLAGS)
    code = ctypes.get_last_error()
    if not h:
        print("%-26s %-8s %d" % (name, "FAIL", code))
        bad.append((name, code))
    else:
        print("%-26s %-8s %d" % (name, "ok", code))
print("-" * 60)
print("failures:", bad if bad else "none")

# Now the exe, as a data file.
exe = os.path.join(DIST, "aoe2mod-engine.exe")
ctypes.set_last_error(0)
h = k32.LoadLibraryExW(exe, None, FLAGS)
print("\nengine exe as DLL:", h, "err", ctypes.get_last_error())
