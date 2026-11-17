"""Cross-civ check: does the stat_offsets expect-table describe Gaia or a playable civ?

Earlier work established that the 62 playable civs carry byte-identical unit
blocks while Gaia differs.  stat_offsets.py walks civ[0] == Gaia, so its
hand-written expect-table must be compared against the right reference.
"""
import os
import _gamepaths as GP
import sys
import contextlib
import io

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import parse_dat as P

BASE = GP.DAT
EXPECT = {4: 30, 7: 30, 38: 100, 83: 25, 751: 35, 93: 40, 125: 120}

data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats
civs = s["civs"]

IDS = sorted(EXPECT)
print("hp per civ for the ids stat_offsets.py asserts")
print("%-6s %-8s | %s" % ("id", "table", "  ".join("c%-3d%-5s" % (i, civs[i].get("name", "?")[:4])
                                                   for i in range(0, 6))))
for uid in IDS:
    row = []
    for ci in range(0, 6):
        u = next((x for x in civs[ci]["units"] if x["id"] == uid), None)
        row.append(str(u["hit_points"]) if u else "-")
    print("%-6s %-8s | %s" % (uid, EXPECT[uid], "  ".join("%-8s" % v for v in row)))

# Which single value do all 63 civs agree on (if any)?
print()
print("consensus across ALL 63 civs:")
for uid in IDS:
    vals = set()
    n = 0
    for c in civs:
        u = next((x for x in c["units"] if x["id"] == uid), None)
        if u:
            vals.add(u["hit_points"])
            n += 1
    tag = "UNANIMOUS" if len(vals) == 1 else "VARIES"
    agree = "== table" if vals == {EXPECT[uid]} else "!= table"
    print("   id %-4s %-34s present in %2d civs  %s  %s"
          % (uid, sorted(vals), n, tag, agree))

# Specifically: is the table the Gaia value or the playable value?
print()
print("verdict:")
for uid in IDS:
    g = next((x for x in civs[0]["units"] if x["id"] == uid), None)
    b = next((x for x in civs[1]["units"] if x["id"] == uid), None)
    gv = g["hit_points"] if g else None
    bv = b["hit_points"] if b else None
    which = ("Gaia" if EXPECT[uid] == gv and gv != bv else
             "playable" if EXPECT[uid] == bv and gv != bv else
             "both" if EXPECT[uid] == gv == bv else "NEITHER -> stale")
    print("   id %-4s table=%-5s gaia=%-5s british=%-5s  -> table records: %s"
          % (uid, EXPECT[uid], gv, bv, which))
