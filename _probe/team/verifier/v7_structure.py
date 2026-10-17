"""v7: (a) prove the 63-civ x 27-record block structure of the .dat change,
(b) raw-byte prefix/suffix diffs of the two JSON files as TEXT,
(c) mod inventory incl. hidden files, (d) info.json content. stdlib only."""
import hashlib
import json
import os
import struct
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
REL_TREE = r"resources\_common\dat\CivTechTrees\BRITONS.json"
REL_PANEL = r"resources\_common\dat\futuravailableunits.json"

out = []


def p(s=""):
    out.append(s)
    print(s)


with open(os.path.join(RAW, "dat_game.raw"), "rb") as f:
    g = f.read()
with open(os.path.join(RAW, "dat_mod.raw"), "rb") as f:
    m = f.read()
with open(os.path.join(HERE, "v2_dat_rawdiff.json"), encoding="utf-8") as f:
    runs = json.load(f)["runs"]

p("### (a) .dat change block structure")
offs = sorted(r["start"] for r in runs)
ids = [struct.unpack_from("<h", g, o - 21)[0] for o in offs]
uniq = sorted(set(ids))
p("  changed field count        : %d" % len(offs))
p("  distinct unit IDs          : %d" % len(uniq))
p("  changed count per unit ID  : %s" % sorted(Counter(ids).values()))
p("  unit IDs (file order, first 27): %s" % ids[:27])
p("  unit IDs sorted            : %s" % uniq)

blocks = [ids[i:i + 27] for i in range(0, len(ids), 27)]
p("  blocks of 27               : %d" % len(blocks))
p("  every block identical      : %s" % all(b == blocks[0] for b in blocks))
p("  every block is a permutation of the ID set: %s"
  % all(sorted(b) == uniq for b in blocks))

# intra/inter-block stride structure
deltas = [offs[i + 1] - offs[i] for i in range(len(offs) - 1)]
intra = []
inter = []
for bi in range(len(blocks)):
    for j in range(26):
        intra.append(deltas[bi * 27 + j])
    if bi < len(blocks) - 1:
        inter.append(deltas[bi * 27 + 26])
ci, cinter = Counter(intra), Counter(inter)
p("  intra-block strides: %d values, %d distinct, all counts==63: %s"
  % (len(intra), len(ci), sorted(set(ci.values()))))
for k in sorted(ci):
    p("     stride %-6d x%d" % (k, ci[k]))
p("  inter-block gaps: %d values, %d distinct, counts: %s"
  % (len(inter), len(cinter), sorted(set(cinter.values()))))
for k in sorted(cinter):
    p("     gap %-8d x%d" % (k, cinter[k]))
p("  block start offsets (first 6, last 3): %s ... %s"
  % ([offs[i * 27] for i in range(6)], [offs[i * 27] for i in range(len(blocks) - 3, len(blocks))]))

# exact HP field identity: game vs mod at every changed offset
p("  every changed field, game -> mod (LE int16): %s"
  % Counter((struct.unpack_from("<h", g, o)[0], struct.unpack_from("<h", m, o)[0]) for o in offs))

# raw prefix/suffix
pre = 0
while pre < len(g) and g[pre] == m[pre]:
    pre += 1
suf = 0
while suf < len(g) - pre and g[len(g) - 1 - suf] == m[len(m) - 1 - suf]:
    suf += 1
p("  .dat raw common prefix      : %d bytes" % pre)
p("  .dat raw common suffix      : %d bytes" % suf)
p("  first differing byte offset : %d ; last : %d" % (pre, len(g) - 1 - suf))
p("  bytes strictly between      : %d (= changed byte count 3402): %s"
  % (len(g) - 1 - suf - pre, len(g) - 1 - suf - pre == 3402))

p("")
p("### (b) JSON raw-byte diffs (TEXT)")


def raw_pair(path):
    with open(path, "rb") as f:
        return f.read()


for tag, rel in (("BRITONS.json", REL_TREE), ("futuravailableunits.json", REL_PANEL)):
    gb = raw_pair(os.path.join(GAME, rel))
    mb = raw_pair(os.path.join(MOD, rel))
    n = min(len(gb), len(mb))
    pre = 0
    while pre < n and gb[pre] == mb[pre]:
        pre += 1
    suf = 0
    while suf < n - pre and gb[len(gb) - 1 - suf] == mb[len(mb) - 1 - suf]:
        suf += 1
    dif = sum(1 for i in range(n) if gb[i] != mb[i]) + abs(len(gb) - len(mb))
    p("  -- %s --" % tag)
    p("     game size %d sha256 %s" % (len(gb), hashlib.sha256(gb).hexdigest()))
    p("     mod  size %d sha256 %s" % (len(mb), hashlib.sha256(mb).hexdigest()))
    p("     common prefix %d bytes ; common suffix %d bytes" % (pre, suf))
    p("     differing byte count (aligned) %d" % dif)
    p("     first differing byte offset %d" % pre)
    p("     GAME span [%d,%d) = %r" % (pre, len(gb) - suf, gb[pre:len(gb) - suf]))
    p("     MOD  span [%d,%d) = %r" % (pre, len(mb) - suf, mb[pre:len(mb) - suf]))

p("")
p("### (c) mod inventory incl. hidden + info.json")
total = 0
for root, dirs, files in os.walk(MOD):
    rel = os.path.relpath(root, MOD)
    for fn in sorted(files):
        fp = os.path.join(root, fn)
        total += 1
        with open(fp, "rb") as f:
            b = f.read()
        p("  %-64s %9d  %s" % (os.path.join(rel, fn), len(b), hashlib.sha256(b).hexdigest()))
    for d in sorted(dirs):
        dp = os.path.join(root, d)
        if not os.listdir(dp):
            p("  EMPTY DIR: %s" % os.path.relpath(dp, MOD))
p("  total files in mod: %d (claim: 4)" % total)
with open(os.path.join(MOD, "info.json"), "rb") as f:
    p("  info.json content: %s" % f.read().decode("utf-8"))

p("")
p("### (d) sibling mods under mods\\local")
localroot = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local"
for d in sorted(os.listdir(localroot)):
    p("  %s" % d)

with open(os.path.join(HERE, "v7_out.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
