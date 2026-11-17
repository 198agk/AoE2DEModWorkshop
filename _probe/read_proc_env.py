#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""读另一个同用户进程的环境块（PEB -> ProcessParameters -> Environment），只读。

用于证明「bili 代理进程里到底有没有 BILI_SILENT_DIRECT_MAX_MB」，
而不是靠推断继承关系。

用法：python -X utf8 _probe/read_proc_env.py 9964 [NAME ...]
"""
from __future__ import annotations

import ctypes as C
import sys
from ctypes import wintypes as W

k32 = C.WinDLL("kernel32", use_last_error=True)
ntdll = C.WinDLL("ntdll", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


class UNICODE_STRING(C.Structure):
    _fields_ = [("Length", C.c_ushort), ("MaximumLength", C.c_ushort),
                ("Buffer", C.c_void_p)]


class PROCESS_BASIC_INFORMATION(C.Structure):
    _fields_ = [("Reserved1", C.c_void_p), ("PebBaseAddress", C.c_void_p),
                ("Reserved2_0", C.c_void_p), ("Reserved2_1", C.c_void_p),
                ("UniqueProcessId", C.c_void_p), ("Reserved3", C.c_void_p)]


k32.OpenProcess.restype = W.HANDLE
k32.OpenProcess.argtypes = (W.DWORD, W.BOOL, W.DWORD)
k32.ReadProcessMemory.restype = W.BOOL
k32.ReadProcessMemory.argtypes = (W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t,
                                  C.POINTER(C.c_size_t))
k32.CloseHandle.argtypes = (W.HANDLE,)
ntdll.NtQueryInformationProcess.restype = C.c_long
ntdll.NtQueryInformationProcess.argtypes = (W.HANDLE, C.c_int, C.c_void_p,
                                            C.c_ulong, C.POINTER(C.c_ulong))


def read(h, addr, size):
    buf = C.create_string_buffer(size)
    got = C.c_size_t(0)
    if not k32.ReadProcessMemory(h, C.c_void_p(addr), buf, size, C.byref(got)):
        raise OSError(C.get_last_error(), "ReadProcessMemory failed")
    return buf.raw[: got.value]


def read_ptr(h, addr):
    return int.from_bytes(read(h, addr, 8)[:8], "little")


def read_env_block(h, pid):
    pbi = PROCESS_BASIC_INFORMATION()
    ret = C.c_ulong(0)
    st = ntdll.NtQueryInformationProcess(h, 0, C.byref(pbi),
                                         C.sizeof(pbi), C.byref(ret))
    if st != 0:
        raise OSError(f"NtQueryInformationProcess NTSTATUS=0x{st & 0xFFFFFFFF:08X}")
    peb = int(pbi.PebBaseAddress)
    params = read_ptr(h, peb + 0x20)
    env_ptr = read_ptr(h, params + 0x80)
    chunks, total = [], 0
    while total < 4 * 1024 * 1024:
        chunk = read(h, env_ptr + total, 65536)
        chunks.append(chunk)
        total += len(chunk)
        if chunk.endswith(b"\x00\x00\x00\x00") or b"\x00\x00\x00\x00" in chunk[-4:]:
            break
    raw = b"".join(chunks)
    text = raw.decode("utf-16-le", "replace")
    return [s for s in text.split("\x00") if s]


def read_env_block_for(pid):
    """给别的脚本用：返回该 pid 的环境变量字符串列表。"""
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, int(pid))
    if not h:
        raise OSError(C.get_last_error(), f"OpenProcess pid={pid} failed")
    try:
        return read_env_block(h, int(pid))
    finally:
        k32.CloseHandle(h)


def main(argv):
    if len(argv) < 2:
        print("usage: read_proc_env.py PID [NAME ...]")
        return 2
    pid = int(argv[1])
    want = argv[2:] or ["BILI_"]
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"FAIL OpenProcess pid={pid} err={C.get_last_error()}")
        return 1
    try:
        pairs = read_env_block(h, pid)
    finally:
        k32.CloseHandle(h)
    print(f"pid={pid} env_entries={len(pairs)}")
    hit = 0
    for p in pairs:
        for w in want:
            if w.upper() in p.upper():
                print("  " + p)
                hit += 1
                break
    if not hit:
        print(f"  (no entry matching {want})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
