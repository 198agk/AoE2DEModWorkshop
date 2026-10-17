import os, io, hashlib, re
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
BASE = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

rows = []
for root, dirs, fs in os.walk(MODS):
    for f in fs:
        p = os.path.join(root, f)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        rows.append((os.path.relpath(p, MODS), sz))
rows.sort()
w("=== ALL FILES IN SUBSCRIBED+LOCAL MODS (%d files)" % len(rows))
for rel, sz in rows:
    w("%10d  %s" % (sz, rel))

TOPDIRS = ("resources", "widgetui", "gamedata", "sound", "history", "scenario",
           "campaign", "art", "ui", "mod.json", "modinfo.json")

w("\n\n=== OVERRIDE MAP (mod file -> engine-relative target path)")
targets = {}
for rel, sz in rows:
    parts = rel.split(os.sep)
    tgt = None
    for i, pt in enumerate(parts):
        if pt.lower() in TOPDIRS:
            tgt = os.path.join(*parts[i:])
            break
    if tgt is None:
        w("UNMAPPED: %s" % rel)
        continue
    targets.setdefault(tgt, []).append((rel, sz))
    w("%-100s -> %s  (%d B)" % (rel, tgt, sz))

w("\n\n=== DOES THE OVERRIDE TARGET EXIST IN THE BASE GAME? (proof the mod replaces a real engine file)")
for tgt, srcs in sorted(targets.items()):
    bp = os.path.join(BASE, tgt)
    exists = os.path.isfile(bp)
    bsz = os.path.getsize(bp) if exists else -1
    bhash = ""
    if exists:
        bhash = hashlib.md5(open(bp, "rb").read()).hexdigest()[:10]
    shash = hashlib.md5(open(os.path.join(MODS, srcs[0][0]), "rb").read()).hexdigest()[:10]
    w("%-100s  base=%s size=%-10d md5base=%s md5mod=%s %s" % (
        tgt, "YES" if exists else "NO ", bsz, bhash, shash, "DIFFERENT" if bhash != shash else "IDENTICAL"))

w("\n\n=== FOCUS: mod files under resources\\_common\\dat\\ or \\dat (data-modding surface)")
for rel, sz in rows:
    low = rel.lower()
    if "\\_common\\dat\\" in low or "\\_common\\dat" == low[-13:]:
        w("%10d  %s" % (sz, rel))

open(os.path.join(OUT, "s20_mods.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:6000])
