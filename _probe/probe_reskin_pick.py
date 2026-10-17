"""Decide the reskin subject for the first in-game sprite test.

The game's own graphics names say unit 126 is the WOLF and unit 65 is the DEER,
which is the opposite of the label table I typed from memory.  That is worth
confirming against a second source before it goes in a report.
"""
import os
import aoe2mod.api as A
from aoe2mod.game import sprites as S

tk = A.open_toolkit()
tk._ensure()
idx = tk._reskin_art()
civs = tk._parsed[1]

print("=== who is 65 and who is 126? (three independent sources) ===")
for uid in (48, 65, 126, 594):
    row = tk.describe(uid)
    u = None
    for c in civs:
        for x in c["units"]:
            if x["id"] == uid:
                u = x
                break
        if u:
            break
    a = idx.art(u)
    print("  unit %-4d describe=%-14r  graphics name=%-14r  file=%s"
          % (uid, row.get("name"), a.get("name"), a.get("file")))

print()
print("=== which civs have these units at all? ===")
for uid in (65, 126, 48, 594, 83, 4, 93):
    holders = [c["name"] for c in civs
               if any(x["id"] == uid for x in c["units"])]
    print("  unit %-4d in %2d civs  %s" % (uid, len(holders), holders[:5]))

print()
print("=== the villager's art is shared -- by whom? ===")
for uid in (83, 293, 224, 1810, 1875):
    for c in civs:
        for x in c["units"]:
            if x["id"] == uid:
                a = idx.art(x)
                print("  unit %-5d describe=%-22r stem=%r" % (uid, tk.describe(uid).get("name"), a.get("stem")))
                break
        else:
            continue
        break

print()
print("=== donors that cover ALL SIX of the villager's animations ===")
VIL = {"attack", "death", "decay", "idle", "idlec", "walk"}
donors = []
for c in civs:
    for u in c["units"]:
        try:
            a = idx.art(u)
        except Exception:
            continue
        keys = set(a.get("tokens") or {})
        if a.get("kind") == "loose" and keys >= VIL:
            donors.append((u["id"], a.get("stem"), len(keys)))
seen = {}
for uid, stem, n in donors:
    if stem not in seen:
        seen[stem] = (uid, n)
print("  %d distinct stems cover every villager animation:" % len(seen))
for stem, (uid, n) in sorted(seen.items())[:25]:
    print("    unit %-5d stem=%-26r keys=%d" % (uid, stem, n))

print()
print("=== so: Villager <- Spearman (no warning at all) ===")
from aoe2mod.intent import reskin as RK
rep = tk.plan({"intent": "unit.sprite", "unit": 83, "donor": 93})
print("  editable=%s files=%s civs=%s warn=%s"
      % (rep["editable"], rep.get("file_count"), rep.get("civ_count"),
         rep.get("warnings")))
raw = RK.plan(tk.game_root, tk._stats["graphics"], civs, 83, 93)
total = 0
for tgt, src in sorted(raw["files"].items()):
    p = os.path.join(tk.game_root, tgt.replace("/", os.sep))
    n = os.path.getsize(p) if os.path.exists(p) else 0
    total += n
print("  %d files, %.1f MB" % (len(raw["files"]), total / 1e6))
