"""Pick a reskin that is unmistakable on screen and safe to ship.

Criteria, in order of importance:
  1. The change must be VISIBLE FROM THE FIRST SECOND OF A GAME -- a unit the
     player builds in the Dark Age, with no age gate and no research gate.
  2. The donor must be OBVIOUSLY different to the eye.  Archer -> Longbowman is
     a bad test: both are a man with a bow, and a viewer could miss it.
  3. The animation sets must line up, so the test fails for one reason only.
"""
import os
import aoe2mod.api as A
from aoe2mod.game import sprites as S
from aoe2mod.intent import reskin as RK

tk = A.open_toolkit()
tk._ensure()
idx = tk._reskin_art()
civs = tk._parsed[1]
units = {u["id"]: u for u in civs[0]["units"]}

# Every candidate that is a plausible Dark-Age target: the villagers and the
# animals, plus a few military units the player sees immediately.
NAMES = {83: "Villager (male)", 293: "Villager (female)", 594: "Sheep",
         4: "Archer", 93: "Spearman", 74: "Militia", 12: "Barracks",
         109: "Stable", 87: "Archery Range", 66: "Gold Mine", 102: "Stone Mine",
         349: "Oak Tree", 48: "Wild Boar", 126: "Deer", 65: "Wolf"}


def art_of(uid):
    try:
        return idx.art(units[uid])
    except Exception as exc:
        return {"kind": "error", "reason": str(exc)}


print("=== candidate art (Dark-Age visible things) ===")
for uid, nm in sorted(NAMES.items()):
    a = art_of(uid)
    keys = sorted(a.get("tokens") or {})
    print("  %-5d %-18s kind=%-7s keys=%s" % (uid, nm, a.get("kind"), keys))

print()
print("=== which pairs line up completely, and how big is the change? ===")
targets = [83, 293, 4, 93, 74]
donors = [594, 126, 48, 65, 4, 93, 74, 83, 293]
rows = []
for t in targets:
    for d in donors:
        if t == d:
            continue
        rep = tk.plan({"intent": "unit.sprite", "unit": t, "donor": d})
        rows.append((t, d, rep))

rows.sort(key=lambda r: (not r[2]["editable"], -r[2].get("file_count", 0)))
for t, d, rep in rows:
    if not rep["editable"]:
        continue
    warn = rep.get("warnings") or []
    raw = RK.plan(tk.game_root, tk._stats["graphics"], tk._parsed[1], t, d)
    mb = sum(os.path.getsize(os.path.join(tk.game_root, "resources", "_common",
                                          "drs", "graphics", p.rsplit("/", 1)[-1]))
             for p in raw["files"].values()) / 1e6
    print("  %-16s <- %-16s files=%-3d civs=%-3d %6.1f MB  warn=%s"
          % (NAMES.get(t, t), NAMES.get(d, d), rep["file_count"],
             rep["civ_count"], mb, "; ".join(w[:60] for w in warn) or "-"))

print()
print("=== the human-visibility question: what does the donor look like? ===")
for uid in (594, 126, 48, 65):
    a = art_of(uid)
    print("  unit %-4d %-12s stem=%r name=%r"
          % (uid, NAMES[uid], a.get("stem"), a.get("name")))
    for tok, f in sorted((a.get("tokens") or {}).items())[:2]:
        rec = None
        print("        token %-8s file %s" % (tok, f))
