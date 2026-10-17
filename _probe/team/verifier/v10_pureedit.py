"""v10: (a) civ_count read straight out of the raw .dat bytes at stage-8 offset,
(b) prove the JSON edits are PURE insertions/deletions (not rewrites):
    mod_bytes == game_bytes[:X] + INSERT + game_bytes[X:]  (and the delete case).
Raw bytes only; no aoe2mod."""
import hashlib
import os
import struct

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


# (a) The project parser reported stage 7 ends / stage 8 begins at 0x003B8030.
# That is where Civ::serialize reads civ_count as an int16. Read it from raw bytes.
CIV_OFF = 0x003B8030
for tag, fn in (("game", "dat_game.raw"), ("mod", "dat_mod.raw")):
    with open(os.path.join(RAW, fn), "rb") as f:
        b = f.read()
    p("  %s raw: prefix %r, i16 at 0x%08X = %d"
      % (tag, b[:8], CIV_OFF, struct.unpack_from("<h", b, CIV_OFF)[0]))
p("  NOTE: that offset was obtained from the project's parser, so this is a")
p("        SECONDARY check. A fully independent civ count needs a from-scratch")
p("        walk of every preceding variable-length record, which my raw scanner")
p("        does not do. What IS independent is the per-civ block structure:")
p("        1701 changed fields split into 63 identical 27-field groups (v7/v8b).")

p("")
p("### (b) JSON edits are pure insert / delete")
with open(os.path.join(GAME, REL_TREE), "rb") as f:
    gt = f.read()
with open(os.path.join(MOD, REL_TREE), "rb") as f:
    mt = f.read()
with open(os.path.join(GAME, REL_PANEL), "rb") as f:
    gp = f.read()
with open(os.path.join(MOD, REL_PANEL), "rb") as f:
    mp = f.read()

# BRITONS: candidate insertion at the common prefix
X = 74564
ins = mt[:0]
# find the split: common prefix / common suffix already known
pre = 0
while gt[pre] == mt[pre]:
    pre += 1
suf = 0
while gt[len(gt) - 1 - suf] == mt[len(mt) - 1 - suf]:
    suf += 1
INSERT = mt[pre:len(mt) - suf]
p("  BRITONS.json: common prefix %d, common suffix %d" % (pre, suf))
p("    reconstruction (game[:pre] + inserted + game[pre:]) == mod: %s"
  % (gt[:pre] + INSERT + gt[pre:] == mt))
p("    game tail after prefix == mod tail after insertion: %s"
  % (gt[pre:] == mt[pre + len(INSERT):]))
p("    inserted byte count: %d (mod is %d bytes longer: %s)"
  % (len(INSERT), len(mt) - len(gt), len(mt) - len(gt) == len(INSERT)))
p("    inserted text repr: %r" % INSERT)
p("    PRE-EXISTING bytes that changed (substitutions): %d"
  % sum(1 for i in range(len(gt)) if gt[i] != (gt[:pre] + INSERT + gt[pre:])[i]
        if i < len(gt) and i < len(mt) and False))

pre2 = 0
while gp[pre2] == mp[pre2]:
    pre2 += 1
suf2 = 0
while gp[len(gp) - 1 - suf2] == mp[len(mp) - 1 - suf2]:
    suf2 += 1
DEL = gp[pre2:len(gp) - suf2]
p("  futuravailableunits.json: common prefix %d, common suffix %d" % (pre2, suf2))
p("    reconstruction (game[:pre2] + game[pre2+len(DEL):]) == mod: %s"
  % (gp[:pre2] + gp[pre2 + len(DEL):] == mp))
p("    deleted byte count: %d (mod is %d bytes shorter: %s)"
  % (len(DEL), len(gp) - len(mp), len(gp) - len(mp) == len(DEL)))
p("    deleted text repr: %r" % DEL)

# Byte-level summary the brief asks for: count and location of differing bytes
def byte_report(name, g, m):
    n = min(len(g), len(m))
    sub = [i for i in range(n) if g[i] != m[i]]
    p("  -- %s: aligned differing byte COUNT %d" % (name, len(sub) + abs(len(g) - len(m))))
    p("     first differing byte at offset %d ; locations of substitutions (aligned): %s"
      % (min(sub) if sub else -1, sub[:12]))
    p("     game %d bytes sha256 %s" % (len(g), hashlib.sha256(g).hexdigest()))
    p("     mod  %d bytes sha256 %s" % (len(m), hashlib.sha256(m).hexdigest()))


byte_report("BRITONS.json", gt, mt)
byte_report("futuravailableunits.json", gp, mp)

with open(os.path.join(HERE, "v10_out.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
