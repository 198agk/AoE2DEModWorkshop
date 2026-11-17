"""Verify walk_effect mirrors the parser, and that every command field is marked.

The new walker opens a capability (editing what a tech DOES) that did not exist
before, so it has to be checked the same way every other walker was: by
comparing it against the authoritative parser and refusing to trust a match
that could be a coincidence.

Checks
  1. effect count and every command tuple agree with parse_dat's own read
  2. every command field has a distinct, in-section offset
  3. offsets actually point at the right bytes (read back independently)
  4. the walk consumes the section exactly (no drift into stage 7)
  5. the writer can re-emit one edited command and the parser reads it back

Read-only against BASE; writes only under _probe/out_effect/.
"""
import os, sys, io, json, struct, contextlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "datparse"))
import parse_dat as P
import intent_patch as IP

BASE = GP.DAT
OUT = os.path.join(HERE, "out_effect")
os.makedirs(OUT, exist_ok=True)

fails = []
def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", label, (" -- " + detail) if detail else ""))
    if not ok:
        fails.append(label)


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return data, p


print("=== 1. walk_effect vs the authoritative parser ===")
data, p = load(BASE)
raw_effs = p.stats["effects"]
effs, eff_start = IP.locate_effects(data, parser=p)
check("effect count agrees", len(effs) == len(raw_effs),
      "walker %d vs parser %d" % (len(effs), len(raw_effs)))

stage5 = next(t for t in p.stage_offsets if t[0].startswith("5 Effects"))
check("section start is stage 5", eff_start == stage5[1],
      "walker %d vs parser %d" % (eff_start, stage5[1]))

mism_name = mism_cmd = 0
for a, b in zip(effs, raw_effs):
    if a["name"] != b["name"]:
        mism_name += 1
    if len(a["commands"]) != len(b["commands"]):
        mism_cmd += 1
        continue
    for ca, cb in zip(a["commands"], b["commands"]):
        got = (ca["type"], ca["a"], ca["b"], ca["c"], ca["d"])
        if got != tuple(cb):
            mism_cmd += 1
            break
check("every name matches", mism_name == 0, "%d mismatched" % mism_name)
check("every command tuple matches", mism_cmd == 0, "%d effects mismatched" % mism_cmd)

print("\n=== 2. every command field is marked ===")
total_cmds = sum(len(e["commands"]) for e in effs)
marked = 0
offs = []
for e in effs:
    for c in e["commands"]:
        for k in ("_off_type", "_off_a", "_off_b", "_off_c", "_off_d"):
            if k in c:
                marked += 1
                offs.append(c[k])
expected = total_cmds * 5
check("all five fields marked on every command", marked == expected,
      "%d/%d" % (marked, expected))
check("offsets are unique", len(set(offs)) == len(offs),
      "%d marks, %d distinct" % (len(offs), len(set(offs))))

print("\n=== 3. offsets point at the right bytes (independent read-back) ===")
bad = 0
for e in effs:
    for c in e["commands"]:
        if data[c["_off_type"]] != c["type"]:
            bad += 1
        for key, fmt in (("_off_a", "<h"), ("_off_b", "<h"), ("_off_c", "<h")):
            v = struct.unpack_from(fmt, data, c[key])[0]
            fld = key.replace("_off_", "")
            if v != c[fld]:
                bad += 1
        dv = struct.unpack_from("<f", data, c["_off_d"])[0]
        if dv != c["d"]:
            bad += 1
check("every mark reads back the value the walker decoded", bad == 0,
      "%d wrong" % bad)

print("\n=== 4. the walk consumes the section exactly ===")
r = IP.Orec(data, eff_start, gv=p.r.gv)
n = r.i32()
for i in range(n):
    IP.walk_effect(r, i)
check("walk ends at stage 7", r.o == stage5[2],
      "walker ended %d, stage5 ends %d, drift %d" % (r.o, stage5[2], r.o - stage5[2]))

print("\n=== 5. edit one command and read it back ===")
# Longbow (make avail) -> effect 251 -> type=2 (enable unit) A=8 B=1
target = 251
c0 = effs[target]["commands"][0]
print("  effect[251] before: type=%d a=%d b=%d c=%d d=%s"
      % (c0["type"], c0["a"], c0["b"], c0["c"], c0["d"]))
patched = bytearray(data)
struct.pack_into("<h", patched, c0["_off_a"], 14)      # 8 -> 14
# DERIVE the expected byte count instead of hardcoding it: 8 -> 14 differs only
# in the low byte, so this is 1, not 2.  Hardcoding "one change per field" has
# been wrong every time this project counted changed bytes.
expect_bytes = len([1 for x, y in zip(struct.pack("<h", c0["a"]),
                                      struct.pack("<h", 14)) if x != y])
n_changed = sum(1 for i in range(len(data)) if data[i] != patched[i])
check("changed byte count matches the fields written", n_changed == expect_bytes,
      "changed %d, expected %d (8->14 alters only the low byte)"
      % (n_changed, expect_bytes))

p2 = P.Parser(bytes(patched))
with contextlib.redirect_stdout(io.StringIO()):
    p2.parse()
check("patched stream parses to exact EOF", p2.r.pos == len(patched),
      "pos %d of %d" % (p2.r.pos, len(patched)))
after_cmds = p2.stats["effects"][target]["commands"]
c0b = after_cmds[0]
print("  effect[251] after : type=%d a=%d b=%d c=%d d=%s" % tuple(c0b))
check("the parser reads the new value", c0b[1] == 14, "a=%d" % c0b[1])

# Build the expectation from the walker's own decode, with only the edited
# field changed.  Comparing against a hand-written literal would let a second
# quiet edit slip through as long as I wrote the same literal twice.
# NOTE: use c0, not `c` -- `c` is a stale loop variable from section 3 and
# silently refers to the last command of the last effect.
expect_cmds = [tuple([c0["type"], 14, c0["b"], c0["c"], c0["d"]])]
expect_cmds += [tuple([x["type"], x["a"], x["b"], x["c"], x["d"]])
                for x in effs[target]["commands"][1:]]
check("only the edited command changed, neighbours intact",
      [tuple(c) for c in after_cmds] == expect_cmds,
      "got %r want %r" % ([tuple(c) for c in after_cmds], expect_cmds))
for i, (x, y) in enumerate(zip(effs[target]["commands"], after_cmds)):
    print("     cmd%d before=%s after=%s"
          % (i, (x["type"], x["a"], x["b"], x["c"], x["d"]), tuple(y)))

print("\n=== 6. would an effect edit change file size? ===")
import zlib
import _gamepaths as GP
comp = zlib.compressobj(6, zlib.DEFLATED, -15)
blob = comp.compress(bytes(patched)) + comp.flush()
print("  decompressed %d (unchanged) | recompressed %d (game original 12,023,754)"
      % (len(patched), len(blob)))

print("\n%s" % ("ALL EFFECT WALK CHECKS PASSED" if not fails
                else "FAILURES: %s" % fails))
sys.exit(1 if fails else 0)
