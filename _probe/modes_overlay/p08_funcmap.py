"""Build a function map from .pdata (x64 unwind RUNTIME_FUNCTION entries):
    each = 12 bytes: BeginRVA(u32), EndRVA(u32), UnwindInfoRVA(u32)
Then, for a given literal VA, find the function(s) that reference it and
dump every RIP-relative .rdata string that function touches.
Read-only.
"""
import os, json, struct, re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
buf = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
secs = json.load(open(os.path.join(OUT, "exe_sections.json")))
S = {s["name"]: s for s in secs}

def f2va(off):
    for s in secs:
        if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
            return s["vaddr"] + (off - s["rawptr"])
    return None

# ---------- 1) function map ----------
pd = S[".pdata"]
n = pd["rawsize"] // 12
funcs = []
for i in range(n):
    o = pd["rawptr"] + i * 12
    b, e, u = struct.unpack_from("<III", buf, o)
    if b == 0 and e == 0:
        continue
    funcs.append((b, e, u))
funcs.sort()
print(f".pdata entries: {len(funcs)}")
json.dump(funcs, open(os.path.join(OUT, "exe_funcmap.json"), "w"))

def func_of(va):
    lo, hi = 0, len(funcs) - 1
    best = None
    while lo <= hi:
        m = (lo + hi) // 2
        b, e, u = funcs[m]
        if b <= va < e:
            return funcs[m]
        if va < b:
            hi = m - 1
        else:
            lo = m + 1
    return None

# ---------- 2) text helpers ----------
TD = buf[S[".text"]["rawptr"]:S[".text"]["rawptr"] + S[".text"]["rawsize"]]
TV, TR = S[".text"]["vaddr"], S[".text"]["rawptr"]

def cstr(va):
    off = None
    for s in secs:
        if s["vaddr"] <= va < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            off = s["rawptr"] + (va - s["vaddr"]); break
    if off is None: return None
    a = off
    while a > 0 and buf[a-1] != 0 and (off - a) < 160:
        a -= 1
    b = off
    while b < len(buf) and buf[b] != 0 and (b - off) < 260:
        b += 1
    raw = buf[a:b]
    try:
        t = raw.decode("utf-8")
        if all(32 <= ord(c) < 127 for c in t):
            return (a, t)
    except Exception:
        pass
    return (a, raw.decode("latin1"))

def refs_in(lo_va, hi_va):
    """all RIP-relative disp32 in [lo_va,hi_va) resolving into any section"""
    out = []
    p0 = lo_va - TV
    p1 = hi_va - TV
    for p in range(max(0, p0), min(len(TD) - 4, p1)):
        disp = struct.unpack_from("<i", TD, p)[0]
        t = TV + p + 4 + disp
        if t == 0: continue
        for s in secs:
            if s["vaddr"] <= t < s["vaddr"] + max(s["vsize"], s["rawsize"]):
                out.append((TV + p, t, s["name"]))
                break
    return out

def describe(func, label, maxstr=200):
    b, e, u = func
    print(f"\n########## {label}: func RVA {b:#x}-{e:#x} (size {e-b} bytes) ##########")
    rs = refs_in(b, e)
    seen = {}
    for (at, t, sec) in rs:
        if sec not in (".rdata", ".data"): continue
        c = cstr(t)
        if not c: continue
        off, txt = c
        if not txt or len(txt) < 2: continue
        printable = sum(1 for ch in txt if 32 <= ord(ch) < 127) / len(txt)
        if printable < 0.9: continue
        seen.setdefault(txt, (at, t, off))
    print(f"  distinct .rdata/.data strings referenced: {len(seen)}")
    for txt, (at, t, off) in list(seen.items())[:maxstr]:
        print(f"    {t:#010x}  {txt!r}")

targets = {
    "modes\\Pompeii\\":        0x31f8420,
    "pompeii-strings":         0x31fe1d8,
    "storage_point_list":      0x325c588,
    "use_modes_path_for_mods": 0x325c5a8,
    "mod-status.json":         0x329e8d8,
    "info.json":               0x329eef0,
}
for k, va in targets.items():
    f = func_of(va)
    print(f"\n>>> literal {k!r} VA={va:#x} func={f}")

# The 3 LEAs found earlier
for name, at in [("LEA_modes_Pompeii", 0xbdb9e), ("LEA_3676DC8_a", 0xbdb7e), ("LEA_3676DC8_b", 0xbdbbf)]:
    f = func_of(at)
    print(f"\n>>> instruction @{at:#x} ({name}) in func {f}")
    print("    target string:", cstr(struct.unpack_from('<i', TD, at - TV + 3)[0] + at + 7))

# dump the function containing 0xbdb9e
f = func_of(0xbdb9e)
if f:
    describe(f, "Function containing 'modes\\Pompeii\\' LEA")

# also: which functions reference 'mod-status.json' / 'info.json' style literals?
print("\n\n=== functions referencing nearby mod literals ===")
for va, lbl in [(0x329e8d8, "mod-status.json"), (0x329eef0, "info.json"),
                (0x31f8420, "modes\\Pompeii\\"), (0x31fe1d8, "pompeii-strings")]:
    # search nearest LEA by brute force over whole text
    hits = []
    for p in range(len(TD) - 4):
        disp = struct.unpack_from("<i", TD, p)[0]
        if TV + p + 4 + disp == va:
            hits.append(TV + p - 2)
    print(f"  {lbl}: {len(hits)} disp32 candidates -> funcs {[func_of(h) for h in hits[:8]]}")
