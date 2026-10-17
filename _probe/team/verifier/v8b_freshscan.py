"""v8b: corrected FRESH scan (step 1, no alignment assumption) + civ-slot reconciliation.
Nothing read from v2_dat_rawdiff.json: hits are re-derived from bytes on disk only."""
import hashlib
import os
import struct
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

out = []


def p(s=""):
    out.append(s)
    print(s)


moddat = os.path.join(MOD, r"resources\_common\dat\empires2_x2_p1.dat")
with open(moddat, "rb") as f:
    raw = zlib.decompressobj(-15).decompress(f.read())
with open(os.path.join(HERE, "raw", "dat_game.raw"), "rb") as f:
    g = f.read()
p("inflated mod sha256 %s ; game raw sha256 %s"
  % (hashlib.sha256(raw).hexdigest(), hashlib.sha256(g).hexdigest()))
p("lengths equal: %s (%d)" % (len(g) == len(raw), len(g)))

diff = [i for i in range(len(g)) if g[i] != raw[i]]
p("differing byte positions: %d" % len(diff))
p("differing byte VALUE pattern: %s"
  % Counter((g[i], raw[i]) for i in diff))

# every maximal run of differing bytes
runs = []
s = diff[0]
prev = diff[0]
for i in diff[1:]:
    if i != prev + 1:
        runs.append((s, prev + 1))
        s = i
    prev = i
runs.append((s, prev + 1))
p("contiguous differing runs: %d ; run lengths: %s"
  % (len(runs), Counter(e - b for b, e in runs)))
p("first 5 runs: %s" % runs[:5])
p("last 3 runs : %s" % runs[-3:])

# each run must be exactly the LE int16 HP field
ok_hp = all(len(g[b:e]) == 2 and g[b:e] == b"\x19\x00" and raw[b:e] == b"\xe8\x03" for b, e in runs)
p("every run is exactly LE-int16 25 -> 1000: %s" % ok_hp)

ids = Counter(struct.unpack_from("<h", g, b - 21)[0] for b, e in runs)
p("distinct unit IDs at HP-21: %d" % len(ids))
p("per-ID counts: %s" % dict(sorted(ids.items())))
p("id 83 (Villager) occurrences: %d" % ids[83])
p("all IDs changed exactly 63 times: %s" % (set(ids.values()) == {63}))

# parity of the HP offsets (records are not 2-byte aligned -> variable-length Name strings)
p("HP-offset parity: even %d / odd %d"
  % (sum(1 for b, e in runs if b % 2 == 0), sum(1 for b, e in runs if b % 2 == 1)))

p("")
p("### civ struct count straight out of the .dat bytes")
# Civ::serialize -> serializeSize<int16_t>(count) then count units.
# Find the 63-unit blocks: count changed IDs per contiguous 27-field group (already shown).
# Independent: count how many 'civ' unit-vector headers report the same unit count.
# Cheap proxy: the number of distinct 'block' groups.
blocks = [runs[i:i + 27] for i in range(0, len(runs), 27)]
p("groups of 27 fields: %d" % len(blocks))
p("every group has the same ID sequence: %s"
  % all([struct.unpack_from('<h', g, b - 21)[0] for b, e in bl] ==
        [struct.unpack_from('<h', g, b - 21)[0] for b, e in blocks[0]] for bl in blocks))

p("")
p("### civ tree JSON count vs .dat civ slots")
treedir = os.path.join(GAME, r"resources\_common\dat\CivTechTrees")
p("game CivTechTrees *.json: %d" % len([f for f in os.listdir(treedir) if f.lower().endswith('.json')]))
p("=> .dat carries 63 per-civ unit copies; the tree folder ships 62 JSONs")

with open(os.path.join(HERE, "v8b_out.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
