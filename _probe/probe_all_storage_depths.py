# -*- coding: utf-8 -*-
"""Which storage points do installed mods reach into BELOW the root, and how deep?

Why this exists
---------------
`_probe/test_overlay_depth.py` concluded "storage-point overlays resolve nested
subdirectories" from ONE storage point: WIDGETUI, whose nested files are known
to work (the chibi emblem sits 3 levels down and is visible in the HUD).

That is too broad a conclusion for one data point, and the texture system has
its own loose-file lookup (`loose_override_proof.py`), so WIDGETUI may be
special.  The DAT storage point is the one that matters here, and its only
nested file is the smoke test that did nothing.

So: take the declared storage-point table, attribute every file of every
installed mod to the storage point it lands in (longest prefix match), and
report depth by storage point.  This says how much of the "nested overrides
work" claim is actually covered, and how much rests on WIDGETUI alone.
"""
import json
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
POMPEII = os.path.join(GAME, "modes", "Pompeii", "Pompeii.json")

with open(POMPEII, "r", encoding="utf-8") as fh:
    reg = json.load(fh)

sps = reg.get("storage_point_list")
if sps is None:
    sys.exit("no storage_point_list in %s" % POMPEII)
print("storage points declared: %d" % len(sps))


def norm(p):
    return p.replace("\\", "/").strip("/").lower()


POINTS = []
for e in sps:
    POINTS.append((e.get("type"), norm(e.get("path") or ""), e))
# longest path first so the most specific storage point wins
POINTS.sort(key=lambda t: -len(t[1]))
for t, p, e in POINTS:
    flag = "modes-aware" if e.get("use_modes_path_for_mods") else ""
    rep = "replace" if e.get("replace") else ""
    print("    %-22s %-34s %s %s" % (t, p, flag, rep))

import aoe2mod.api as A  # noqa: E402

tk = A.open_toolkit()
mods = tk.mods()
print()
print("installed mods: %d" % len(mods))

# ---- attribute every mod file to a storage point ---------------------------
stats = {}     # type -> dict(mods=set(), files=0, depth={d:count}, sample={d:path})
unclaimed = []
for m in mods:
    root = m["path"]
    name = m["name"]
    if not os.path.isdir(root):
        print("    (missing on disk) %s" % name)
        continue
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            r = norm(rel)
            if r == "info.json" or r.startswith("thumbnail") or r == "previewicon":
                continue
            hit = None
            for t, p, e in POINTS:
                if r == p or r.startswith(p + "/"):
                    hit = (t, p)
                    break
            if hit is None:
                unclaimed.append((name, rel))
                continue
            t, p = hit
            tail = r[len(p):].lstrip("/")
            depth = 0 if tail == "" else tail.count("/") + 1
            st = stats.setdefault(t, {"mods": set(), "files": 0, "depth": {},
                                      "sample": {}})
            st["mods"].add(name)
            st["files"] += 1
            st["depth"][depth] = st["depth"].get(depth, 0) + 1
            if depth not in st["sample"]:
                st["sample"][depth] = tail

print()
print("=" * 100)
print("files per storage point, by depth below the storage root")
print("=" * 100)
print("%-22s %5s %6s  %s" % ("storage point", "mods", "files", "depth histogram"))
print("-" * 100)
rows = sorted(stats.items(),
              key=lambda kv: (-max(kv[1]["depth"]), -kv[1]["files"]))
for t, st in rows:
    hist = ", ".join("d%d=%d" % (d, st["depth"][d]) for d in sorted(st["depth"]))
    print("%-22s %5d %6d  %s" % (t, len(st["mods"]), st["files"], hist))
    for d in sorted(st["depth"]):
        if d >= 1:
            print("%-22s       %6s  d%d sample: %s"
                  % ("", "", d, st["sample"][d]))
    if t.upper() == "DAT":
        print("%-22s       %s" % ("", "  ^^ the storage point whose overlay is in question"))

print()
print("unclaimed mod files (no storage point matched): %d" % len(unclaimed))
for name, rel in unclaimed[:25]:
    print("    %-46s %s" % (name[:46], rel))

print()
print("=" * 100)
deep = {t: st for t, st in stats.items() if max(st["depth"]) >= 1}
print("storage points with at least one NESTED mod file: %d of %d used"
      % (len(deep), len(stats)))
for t, st in sorted(deep.items(), key=lambda kv: -max(kv[1]["depth"])):
    print("    %-22s max depth %d  files %d  mods %d"
          % (t, max(st["depth"]), st["files"], len(st["mods"])))

print()
print("ALL-STORAGE DEPTH CENSUS: this is how wide the 'nested overrides work'")
print("claim really is.  A single non-WIDGETUI storage point with a nested file")
print("would extend it; WIDGETUI alone does not.")
