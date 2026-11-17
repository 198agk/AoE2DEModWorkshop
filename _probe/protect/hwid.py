# -*- coding: utf-8 -*-
"""Machine fingerprint for license binding.

Only stable, machine-scoped values: Windows MachineGuid and the system volume
serial.  NIC MACs and hostnames change (USB dongles, dock), so they are not
used -- a license that dies on a laptop reboot is worse than a weak license.
"""
import ctypes
import hashlib
import os
import platform


def _machine_guid():
    try:
        import winreg
        flags = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, flags) as k:
            return str(winreg.QueryValueEx(k, "MachineGuid")[0])
    except Exception:
        return ""


def _vol_serial(root=None):
    root = root or os.environ.get("SystemDrive", "C:") + "\\"
    try:
        k32 = ctypes.windll.kernel32
        vol = ctypes.c_ulong(0)
        fs = ctypes.c_ulong(0)
        ok = k32.GetVolumeInformationW(ctypes.c_wchar_p(root), None, 0,
                                       ctypes.byref(vol), ctypes.byref(fs), None, None, 0)
        return "%08X" % (vol.value & 0xFFFFFFFF) if ok else ""
    except Exception:
        return ""


def fingerprint():
    parts = [_machine_guid(), _vol_serial(), platform.machine()]
    raw = "|".join(x for x in parts if x)
    if not raw:
        import uuid
        raw = str(uuid.getnode())
    return hashlib.sha256(("aoe2mod-hwid-v1|" + raw).encode("utf-8")).hexdigest()[:20]


def pretty():
    h = fingerprint()
    return "-".join(h[i:i + 5] for i in range(0, 20, 5))


if __name__ == "__main__":
    print(fingerprint())
    print(pretty())
