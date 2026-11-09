import sys, io, os, collections, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
from aoe2mod.dat import parser as P, locate as L
from aoe2mod.game import locations as LOC
import os
g = LOC.find_game_root()
raw, _ = P.load_dat(os.path.join(g,"resources","_common","dat","empires2_x2_p1.dat"))
with contextlib.redirect_stdout(io.StringIO()):
    civs, start, gv, end = L.locate(raw)
print("civ names:", [c["name"] for c in civs])
def trainmap(c):
    m = {}
    for u in c["units"]:
        tl = u.get("train_locations") or []
        ids = tuple(sorted(t["unit_id"] for t in tl if t["unit_id"] and t["unit_id"] > 0))
        if ids: m[u["id"]] = ids
    return m
for c in civs:
    if c["name"].upper().startswith("BRIT"):
        m = trainmap(c)
        b = m.get(12, ())
        print("BRITONS(civ name %r) building 12 -> %d unit ids" % (c["name"], len(b)))
        print("  ", b)
        # total unit records
        print("  unit records:", len(c["units"]))
