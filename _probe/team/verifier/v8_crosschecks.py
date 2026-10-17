"""v8: independent cross-checks.
(a) how many civs does the GAME ship (CivTechTrees json count) -> the 'all 63 civs' figure,
(b) does the MOD ship any civ tree other than BRITONS.json,
(c) does the GAME's own key-value string table map dllId 5121/5607/5606 to the Villager names?
(d) round-trip: re-inflate the MOD .dat from disk and re-locate the 1701 offsets from scratch,
    confirming hp==1000 there, WITHOUT reading v2_dat_rawdiff.json (fresh derivation).
stdlib only."""
import hashlib
import json
import os
import struct
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
STRINGS = os.path.join(GAME, r"resources\en\strings\key-value\key-value-strings-utf8.txt")

out = []


def p(s=""):
    out.append(s)
    print(s)


p("### (a) civ count from the game install")
treedir = os.path.join(GAME, r"resources\_common\dat\CivTechTrees")
jsons = sorted(f for f in os.listdir(treedir) if f.lower().endswith(".json"))
p("  game CivTechTrees json files: %d" % len(jsons))
p("  first 8: %s" % jsons[:8])
p("  BRITONS.json present: %s" % ("BRITONS.json" in jsons))

p("")
p("### (b) civ trees shipped by the MOD")
modtrees = os.path.join(MOD, r"resources\_common\dat\CivTechTrees")
mt = sorted(os.listdir(modtrees))
p("  mod CivTechTrees entries: %s" % mt)

p("")
p("### (c) game string table lookups")
want = {5121: "expect Villager (Male)", 5607: "expect Villager (Female)",
        5606: "expect Villager", 5124: "expect Hunter"}
found = {}
with open(STRINGS, "r", encoding="utf-8-sig", errors="replace") as f:
    for line in f:
        line = line.rstrip("\r\n")
        if not line or line.startswith("//"):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        k = parts[0].strip()
        if k.isdigit() and int(k) in want:
            found[int(k)] = parts[1]
for k in sorted(want):
    p("  id %-6d -> %-34r  (%s)" % (k, found.get(k), want[k]))
p("  NOTE: separate ids -> distinct Male/Female/Villager entries: %s"
  % (len({found.get(k) for k in (5121, 5607, 5606)}) == 3))

p("")
p("### (d) FRESH round-trip: inflate mod .dat from disk, re-find every 25->1000 int16")
moddat = os.path.join(MOD, r"resources\_common\dat\empires2_x2_p1.dat")
with open(moddat, "rb") as f:
    comp = f.read()
p("  compressed size %d sha256 %s" % (len(comp), hashlib.sha256(comp).hexdigest()))
d = zlib.decompressobj(-15)
raw = d.decompress(comp)
raw += d.flush()
p("  inflated size %d, eof=%s, unused_tail=%d" % (len(raw), d.eof, len(d.unused_data)))
p("  inflated sha256 %s" % hashlib.sha256(raw).hexdigest())

with open(os.path.join(HERE, "raw", "dat_game.raw"), "rb") as f:
    g = f.read()
p("  game raw size %d (equal length: %s)" % (len(g), len(g) == len(raw)))

# fresh scan: every offset where game has int16 25 and mod has int16 1000
hits = []
for i in range(0, len(g) - 1, 2):
    if g[i] == 0x19 and g[i + 1] == 0x00 and raw[i] == 0xE8 and raw[i + 1] == 0x03:
        hits.append(i)
# and the reverse / any other byte difference
diff_off = [i for i in range(len(g)) if g[i] != raw[i]]
p("  fresh scan: int16 25(game)->1000(mod) at %d even offsets" % len(hits))
p("  actual differing byte positions: %d ; all inside hits: %s"
  % (len(diff_off), set(diff_off) == {o + k for o in hits for k in (0, 1)}))
ids = Counter(struct.unpack_from("<h", g, o - 21)[0] for o in hits)
p("  distinct unit IDs at HP-21: %d ; per-ID counts: %s"
  % (len(ids), sorted(ids.values())))
p("  id 83 count: %d" % ids.get(83, 0))
p("  HP identity (game,mod): %s"
  % Counter((struct.unpack_from("<h", g, o)[0], struct.unpack_from("<h", raw, o)[0]) for o in hits))

with open(os.path.join(HERE, "v8_out.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
