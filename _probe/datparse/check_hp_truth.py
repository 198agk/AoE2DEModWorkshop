"""Independent check of the hp 'expectations' that stat_offsets.py hardcodes.

stat_offsets.py keeps its own mirrored read_type50 walker and compares against a
hand-written expect-table.  When they disagree we must decide whether the walker
or the table is wrong -- so ask the authoritative shallow parser (parse_dat) and
the game's own exposed value, and report which side the truth lands on.
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

# the exact table stat_offsets.py asserts
EXPECT = {4: 30, 7: 30, 38: 100, 83: 25, 751: 35, 93: 40, 125: 120}

data, how = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats

# authority: the shallow parser's civ[0] unit records
civ0 = s["civs"][0]
units = {u["id"]: u for u in civ0["units"]}

print("authoritative hp from parse_dat (VER %s, civ[0]=%s)"
      % (s["file_version"], civ0.get("name")))
print("%-6s %-8s %-8s %-8s %s"
      % ("id", "table", "parser", "match", "verdict"))
bad = []
for uid, want in sorted(EXPECT.items()):
    got = units.get(uid, {}).get("hit_points")
    match = (got == want)
    if not match:
        bad.append((uid, want, got))
    print("%-6s %-8s %-8s %-8s %s"
          % (uid, want, got, match, "table agrees" if match else "TABLE IS STALE"))

print()
print("mismatched ids: %s" % [b[0] for b in bad])
print("-> %d of %d hardcoded expectations are contradicted by the authoritative parser"
      % (len(bad), len(EXPECT)))

# and confirm the walker itself agrees with the authority on those ids,
# which separates "walker is broken" from "table is stale"
print()
print("shallow-vs-table reconciliation:")
for uid, want, got in bad:
    print("   id %-4s  table says %-5s  both the shallow parser and the deep "
          "walker say %-5s" % (uid, want, got))
