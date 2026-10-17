"""Final pre-flight state + exact line numbers for the report's evidence column."""
import json
import os
import re
import time

PROF = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MOD = os.path.join(PROF, "mods", "local", "aoe2mod Smoke5 TreeVsPanel")

print("=== NOW ===")
print("    %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

print("\n=== mod-status.json ===")
ms = os.path.join(PROF, "mods", "mod-status.json")
print("    path=%s  size=%d  mtime=%s"
      % (ms, os.path.getsize(ms), time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(ms)))))
d = json.load(open(ms, encoding="utf-8-sig"))
for m in d["Mods"]:
    print("    Enabled=%-5s Prio=%-2s %s" % (m["Enabled"], m["Priority"], m["Path"]))
print("    >>> Smoke5 present: %s" % any("Smoke5" in m["Path"] for m in d["Mods"]))

print("\n=== smoke5 mod folder ===")
for root, dirs, files in os.walk(MOD):
    for f in files:
        fp = os.path.join(root, f)
        print("    %-8d %s" % (os.path.getsize(fp), os.path.relpath(fp, MOD)))

print("\n=== latest log dirs ===")
ld = os.path.join(PROF, "..", "logs")
ld = os.path.abspath(ld)
names = sorted(os.listdir(ld))
print("    n=%d  newest 4: %s" % (len(names), names[-4:]))

def lineno(path, pat, flags=0, limit=6):
    out = []
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            if re.search(pat, line, flags):
                out.append((i, line.strip()[:120]))
                if len(out) >= limit:
                    break
    return out

print("\n=== line-number evidence ===")
for label, path, pat in [
    ("screentechtree RegionalUnitIcon", os.path.join(GAME, "widgetui", "screentechtree.json"), r'"RegionalUnitIcon"'),
    ("screentechtree TTKeyRegionalUnit", os.path.join(GAME, "widgetui", "screentechtree.json"), r'TTKeyRegionalUnit'),
    ("materials TTKeyRegionalUnit", os.path.join(GAME, "widgetui", "materials.json"), r'"TTKeyRegionalUnit"'),
    ("screenoptions EnableFutureItemsDisplay", os.path.join(GAME, "widgetui", "screenoptions.json"), r'"EnableFutureItemsDisplay"'),
    ("screenoptions TechTreePreview", os.path.join(GAME, "widgetui", "screenoptions.json"), r'"TechTreePreview"'),
    ("stringreference FUTURE_ITEMS", os.path.join(GAME, "widgetui", "stringreference.json"), r'IDS_OPT_DISPLAY_FUTURE_ITEMS"'),
]:
    print("    %-42s %s" % (label, lineno(path, pat)))

print("\n=== confirm commandpanel.json has NO RegionalUnit / futuravailable ===")
for f in ("commandpanel.json", "techtreepreviewpanel.json"):
    t = open(os.path.join(GAME, "widgetui", f), encoding="utf-8-sig", errors="replace").read()
    print("    %-30s RegionalUnit=%d futuravailable=%d" % (f, t.count("RegionalUnit"), t.count("futuravailable")))

print("\n=== BRITONS.json (mod) added-row line numbers ===")
mp = os.path.join(MOD, "resources", "_common", "dat", "CivTechTrees", "BRITONS.json")
with open(mp, encoding="utf-8-sig") as fh:
    lines = fh.readlines()
print("    total lines=%d" % len(lines))
for i, line in enumerate(lines, 1):
    if "Champi" in line or '"Node ID": 2550' in line:
        print("    %d: %s" % (i, line.rstrip()[:130]))
print("DONE")
