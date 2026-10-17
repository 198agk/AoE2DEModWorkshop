"""Corrections + code analysis.
 1) <locale> placeholder expansion for storage points (my earlier 'uncovered' check was wrong).
 2) .pdata membership of candidate code VAs; raw dump + caller scan for func RVA 0xbdb50.
 3) mode-related string hunting; path-building literals.
 4) morematerials.json + COMMON_STRINGS real file names.
Read-only.
"""
import os, json, struct, re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
POM  = os.path.join(GAME, "modes", "Pompeii")
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
buf = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
secs = json.load(open(os.path.join(OUT, "exe_sections.json")))
S = {s["name"]: s for s in secs}
TV, TR = S[".text"]["vaddr"], S[".text"]["rawptr"]
TD = buf[TR:TR + S[".text"]["rawsize"]]

funcs = [tuple(x) for x in json.load(open(os.path.join(OUT, "exe_funcmap.json")))]
fset = sorted(funcs)

def func_of(va):
    lo, hi = 0, len(fset) - 1
    while lo <= hi:
        m = (lo + hi) // 2
        b, e, u = fset[m]
        if b <= va < e: return fset[m]
        if va < b: hi = m - 1
        else: lo = m + 1
    return None

print("=== 1) .pdata membership of candidate VAs ===")
for va, lbl in [(0xbdb50, "func w/ modes\\Pompeii\\ (RVA)"),
                (0x1ee15ba, "storage_point_list disp32 site (VA)"),
                (0x1ee05ba, "storage_point_list disp32 site (textFile-RVA)"),
                (0x967514, "pompeii-strings site"),
                (0xbdb9e, "LEA modes\\Pompeii\\"),
                (0xbdba1, "LEA modes\\Pompeii\\ (brute)")]:
    print(f"  {lbl}: VA/RVA {va:#x} -> func {func_of(va)}")

print("\n=== 2) raw dump of func 0xbdb50-0xbdc93 ===")
lo, hi = 0xbdb50, 0xbdc93
for i in range(lo, hi, 16):
    c = TD[i:i+16]
    asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
    print(f"  {TV+i:#010x} (rva {i:#08x})  {c.hex(' ')}  |{asc}|")

print("\n=== 3) callers of 0xbdb50 (direct call rel32) ===")
callers = []
for i in range(len(TD) - 5):
    if TD[i] == 0xE8:
        rel = struct.unpack_from("<i", TD, i+1)[0]
        if TV + i + 5 + rel == 0xbdb50:
            callers.append(TV + i)
print("  direct call count:", len(callers), [hex(c) for c in callers[:20]])

print("\n=== 4) functions referencing 'modes\\Pompeii\\' plus their .rdata strings ===")
def cstr(va):
    off = None
    for s in secs:
        if s["vaddr"] <= va < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            off = s["rawptr"] + (va - s["vaddr"]); break
    if off is None: return None
    a = off
    while a > 0 and buf[a-1] != 0 and (off - a) < 200: a -= 1
    b = off
    while b < len(buf) and buf[b] != 0 and (b - off) < 300: b += 1
    return buf[a:b].decode("latin1")

def strings_in(lo_va, hi_va):
    out = {}
    for p in range(max(0, lo_va - TV), min(len(TD) - 4, hi_va - TV)):
        disp = struct.unpack_from("<i", TD, p)[0]
        t = TV + p + 4 + disp
        if t == 0: continue
        for s in secs:
            if s["vaddr"] <= t < s["vaddr"] + max(s["vsize"], s["rawsize"]):
                c = cstr(t)
                if c and len(c) >= 3 and sum(1 for ch in c if 32 <= ord(ch) < 127) / len(c) > 0.9:
                    out.setdefault(c, TV + p)
                break
    return out

for f in [func_of(0xbdb50)]:
    if not f: continue
    b, e, _ = f
    print(f"  func rva {b:#x}-{e:#x}:")
    for s, at in strings_in(b, e).items():
        print(f"     {s!r}  (via {at:#x})")

print("\n=== 5) mode-related strings (case-insensitive 'mode' as a word/path) ===")
pats = [rb"SelectedContentMode", rb"ContentMode", rb"GameMode", rb"game_mode"]
for p in pats:
    for m in re.finditer(re.escape(p), buf):
        a = m.start()
        s0 = a
        while s0 > 0 and buf[s0-1] != 0: s0 -= 1
        e0 = a
        while e0 < len(buf) and buf[e0] != 0: e0 += 1
        print(f"  {p.decode()} @{a:#x}: {buf[s0:e0].decode('latin1')!r}")

print("\n=== 6) path-builder literals ===")
for n in [rb"Age of Empires II: Definitive Edition", rb"Age of Empires 2 DE", rb"<userrelicid>",
          rb"<locale>", rb"workshop\content", rb"mods", rb"local", rb"subscribed",
          rb"Schema", rb"AoE2DE.dat", rb"morematerials.json", rb"build_atlas.ps1"]:
    hits = [m.start() for m in re.finditer(re.escape(n), buf)]
    print(f"  {n.decode():45s} {len(hits)} hits {[hex(h) for h in hits[:6]]}")

print("\n=== 7) morematerials.json + COMMON_STRINGS actual names ===")
for side, root in [("base", GAME), ("pompeii", POM)]:
    p = os.path.join(root, "widgetui", "morematerials.json")
    print(f"  {side} morematerials.json exists={os.path.exists(p)} size={os.path.getsize(p) if os.path.exists(p) else None}")
    d = os.path.join(root, "resources", "_common", "strings")
    if os.path.isdir(d):
        for dp, dn, fn in os.walk(d):
            for f in fn:
                fp = os.path.join(dp, f)
                print(f"  {side} {os.path.relpath(fp, root)}  {os.path.getsize(fp)}")
    d2 = os.path.join(root, "widgetui")
    for f in ["build_atlas.ps1"]:
        fp = os.path.join(d2, f)
        print(f"  {side} widgetui/{f} exists={os.path.exists(fp)} size={os.path.getsize(fp) if os.path.exists(fp) else None}")

print("\n=== 8) <locale> expansion: correct 'uncovered' check ===")
LOCALES = ["br","de","en","es","fr","hi","it","jp","ko","ms","mx","pl","ru","tr","tw","vi","zh"]
def load_tsv(p):
    d = {}
    with open(p, encoding="utf-8") as f:
        next(f)
        for line in f:
            line = line.rstrip("\n")
            if not line: continue
            r, s = line.rsplit("\t", 1); d[r] = int(s)
    return d
pom = load_tsv(os.path.join(OUT, "inv_pompeii.tsv"))
pj = json.loads(open(os.path.join(POM, "Pompeii.json"), "rb").read().decode("utf-8-sig"))
sps = [e["path"].replace("\\", "/").strip("/") for e in pj["storage_point_list"]]
expanded = []
for sp in sps:
    if "<locale>" in sp:
        for L in LOCALES:
            expanded.append(sp.replace("<locale>", L))
    else:
        expanded.append(sp)
def covered(rel):
    return any(rel == s or rel.startswith(s + "/") for s in expanded)
un = sorted(r for r in pom if not covered(r))
print(f"  genuinely uncovered Pompeii files: {len(un)}")
for r in un: print("    ", r, pom[r])
