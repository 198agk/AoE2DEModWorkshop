"""Two things before shipping a reskin test mod:

 1. the deer/wolf swap the last probe suggested (is the name table or my
    reading of it wrong?),
 2. the blast radius of "make the villager look like a sheep" -- how many OTHER
    units share the villager's art, so the test result is not over-reported.
"""
import os
import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()
idx = tk._reskin_art()
civs = tk._parsed[1]
units = {u["id"]: u for u in civs[0]["units"]}

print("=== deer / wolf ===")
for uid, label in ((126, "Deer"), (65, "Wolf")):
    a = idx.art(units[uid])
    print("  unit %-4d %-6s stem=%-8r file=%-28s name=%r"
          % (uid, label, a.get("stem"), a.get("file"), a.get("name")))
for uid in (126, 65):
    print("  unit %d display=%r" % (uid, tk._sem().get(uid).display if False else ""))

print()
print("=== who else shares the villager's art? ===")
for uid, label in ((83, "Villager M"), (594, "Sheep")):
    a = idx.art(units[uid])
    stem = a.get("stem")
    ids = []
    for c in civs:
        for u in c["units"]:
            try:
                ua = idx.art(u)
            except Exception:
                continue
            if ua.get("stem") == stem:
                ids.append(u["id"])
    uniq = sorted(set(ids))
    print("  stem %-22r shared by %d unit ids: %s" % (stem, len(uniq), uniq[:20]))

print()
print("=== the exact file list for Villager <- Sheep, per civ ===")
from aoe2mod.intent import reskin as RK
for u in units.values():
    if u["id"] != 83:
        continue
    print("  unit 83 record civ=%r" % u.get("civ"))
    break
# Which civ names map to which villager stem?
from collections import defaultdict
by_stem = defaultdict(list)
for c in civs:
    for u in c["units"]:
        if u["id"] == 83:
            by_stem[idx.art(u).get("stem")].append(c["name"])
for stem, names in sorted(by_stem.items()):
    print("  villager stem %-24r -> %d civs %s" % (stem, len(names), names[:4]))

raw = RK.plan(tk.game_root, tk._stats["graphics"], civs, 83, 594)
print()
print("  ok=%s file_count=%s civ_count=%s" % (raw.get("ok"), raw.get("file_count"),
                                              raw.get("civ_count")))
print("  target_stems=%s donor_stems=%s" % (raw.get("target_stems"), raw.get("donor_stems")))
print("  warnings=%s" % (raw.get("warnings"),))
total = 0
for tgt, src in sorted(raw["files"].items()):
    p = os.path.join(tk.game_root, "resources", "_common", "drs", "graphics", tgt)
    n = os.path.getsize(p) if os.path.exists(p) else -1
    if n > 0:
        total += n
    print("    %-38s <- %s   %d B" % (tgt, src, n))
print("  TOTAL shipped bytes: %d (%.1f MB)" % (total, total / 1e6))
