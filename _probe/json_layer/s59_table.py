import os, io, json, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=== does 'gamedata_x1'/'gamedata_x2' exist on disk? (GameDataSet '%s\\%s') ===")
for n in ("gamedata_x1", "gamedata_x2", "gamedata_x3", "gamedata"):
    p = os.path.join(GAME, "resources", "_common", n)
    alt = os.path.join(GAME, "resources", n)
    w("  %-14s _common=%-6s resources=%s" % (n, os.path.isdir(p), os.path.isdir(alt)))
w("  dat-dir subdirs = %s" % [d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))])
w("  resources/_common subdirs = %s" % [d for d in os.listdir(os.path.join(GAME, "resources", "_common")) if os.path.isdir(os.path.join(GAME, "resources", "_common", d))][:30])

w("")
w("=== 'modes' tree: which mode names exist, and does each carry a dat dir? ===")
modes = os.path.join(GAME, "modes")
for m in sorted(os.listdir(modes)):
    dd = os.path.join(modes, m, "resources", "_common", "dat")
    if os.path.isdir(dd):
        fs = os.listdir(dd)
        w("  %-16s dat files=%d json=%d" % (m, len(fs), len([f for f in fs if f.endswith('.json')])))

w("")
w("=== FINAL per-file verdict input table (auto) ===")
IN_SCOPE = ["AIConsts.json", "adapterblacklist.json", "airesourcetypes.json", "buttons.json",
            "chronicles_selection_group_def.json", "civilizations.json", "dropsites.json", "eras.json",
            "futuravailableunits.json", "hotkeys.json", "linkedTechs.json", "linkedUnits.json", "maps.json",
            "objreplacement.json", "paphos_campaign.json", "paphosfutureavailableunits.json", "peru_campaign.json",
            "providence_campaign.json", "selection_group_def.json", "sharedbuildings.json", "sounds.json",
            "unitcategories.json", "unitlines.json"]
rows = []
for f in IN_SCOPE:
    p = os.path.join(BASE, f)
    pj = os.path.join(BASE, "CivTechTrees", f)
    path = p if os.path.exists(p) else pj
    size = os.path.getsize(path)
    name_in_exe = f.encode() in exe
    txt = open(path, "rb").read().decode("utf-8-sig", "ignore")
    keys = sorted(set(re.findall(r'"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', txt)))
    keys = [k for k in keys if len(k) >= 4]
    present = [k for k in keys if k.encode() in exe]
    # longest contiguous run of PRESENT keys within 600B
    offs = sorted((exe.find(k.encode()), k) for k in present)
    best, cur, start, prev = 0, 0, None, None
    for o, k in offs:
        if prev is not None and 0 <= o - prev <= 600:
            cur += 1
        else:
            cur = 1
        if cur > best:
            best = cur
        prev = o
    rows.append((f, size, len(keys), len(present), name_in_exe, best, sum(txt.count('\n') for _ in [0])))
w("  %-42s %10s %6s %6s %7s %7s" % ("file", "bytes", "keys", "present", "nameInExe", "maxrun"))
for f, size, nk, npr, ne, run, _ in rows:
    w("  %-42s %10d %6d %6d %9s %7d" % (f, size, nk, npr, ne, run))
# CivTechTrees sample
for f in ("BRITONS.json", "KHITANS.json", "ACHAEMENIDS.json"):
    path = os.path.join(BASE, "CivTechTrees", f)
    size = os.path.getsize(path)
    txt = open(path, "rb").read().decode("utf-8-sig", "ignore")
    keys = [k for k in sorted(set(re.findall(r'"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', txt))) if len(k) >= 4]
    present = [k for k in keys if k.encode() in exe]
    offs = sorted((exe.find(k.encode()), k) for k in present)
    best, cur, prev = 0, 0, None
    for o, k in offs:
        if prev is not None and 0 <= o - prev <= 600: cur += 1
        else: cur = 1
        best = max(best, cur); prev = o
    w("  %-42s %10d %6d %6d %9s %7d" % ("CivTechTrees\\" + f, size, len(keys), len(present), False, best))
open(os.path.join(OUT, "s59_table.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
