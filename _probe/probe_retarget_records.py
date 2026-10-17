"""How small can a reskin possibly be?

Two ways to make unit X draw unit Y's art:

  A. COPY (what v12 does): write donor pixels under every target filename.
     466 files, 438.1 MB -- but only 8 distinct pictures, so 431 MB of it is
     the same 8 images repeated under 233 names.

  B. RETARGET (this probe): the .dat graphics record carries the filename in
     its `file` field.  Point the target's records at the donor's files, which
     already ship with the game, and copy nothing.

This probe measures B: which records would change, what the new file strings
are, and what the .dat grows by when those strings change length.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, collections

sys.path.insert(0, _HERE_PATH(".."))

import aoe2mod.api as A
from aoe2mod.game import sprites as SP
from aoe2mod.intent import reskin as RK

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(GAME)
tk._ensure()
tk._reskin_art()

idx = tk._sprites
gfx = tk._stats["graphics"]
fam = tk._families().get(83) or [83]
tables = RK._units_by_id(tk._parsed[1])

# donor = sheep 594
d_rec = tables[0].get(594)
d_art = idx.art(d_rec)
print("donor Sheep stem=%r files=%d" % (d_art["stem"], len(d_art["files"])))
print()

# For each family member, its own records per animation, and where each would
# point: donor token -> donor file; animations the donor lacks need a stand-in.
need = collections.Counter()
changes = []            # (gid, old_file, new_file, animation, member)
for m in fam:
    rec = tables[0].get(m)
    if rec is None:
        continue
    a = idx.art(rec)
    if a.get("kind") != "loose":
        continue
    for anim, gid in sorted((a.get("tokens") or {}).items()):
        src = (d_art.get("tokens") or {}).get(anim)
        if src is None:
            fb = SP.fill_for(a, d_art, anim)
            if fb is None:
                need["(no stand-in)"] += 1
                continue
            src, _grid, _why = fb
            need["filled " + anim] += 1
        rec_old = (gfx.get(gid) or {}).get("file") or ""
        rec_new = (d_art.get("tokens") or {}).get(src) or ""
        if not rec_old or not rec_new:
            continue
        if not rec_new.endswith("_x1"):
            continue
        changes.append((gid, rec_old, rec_new, anim, m))

print("records that would change their `file` field: %d" % len(changes))
print("distinct (old -> new) pairs: %d" % len(set((c[1], c[2]) for c in changes)))
print()
print("sample:")
for gid, old, new, anim, m in changes[:8]:
    print("   gfx %-6d unit %-5d %-8s %s -> %s" % (gid, m, anim, old, new))
print()

# .dat delta: each changed string changes record length by len(new)-len(old)
delta = 0
for gid, old, new, anim, m in set((c[0], c[1], c[2], c[3], c[4]) for c in changes):
    delta += len(new) - len(old)
print("naive sum(len(new)-len(old)) over %d records: %+d bytes" % (len(changes), delta))

# what each pic actually is (dedupe by content)
by_new = collections.Counter(c[2] for c in changes)
print()
print("distinct donor files they would point at: %d" % len(by_new))
for f, n in by_new.most_common():
    print("   %-40s %d record(s)" % (f, n))

dat = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
print()
print("=== size comparison ===")
out = os.path.join(_HERE_PATH("_probe"), "out_dshtest_v12")
copy_bytes = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(out) for f in fs)
print("A copy     : %10d B  (%.1f MB)" % (copy_bytes, copy_bytes / 1e6))
print("B retarget : %10d B  (%.1f MB)   <- the .dat, unchanged pixel count"
      % (os.path.getsize(dat), os.path.getsize(dat) / 1e6))
print("B/A        : %.1fx smaller" % (copy_bytes / os.path.getsize(dat)))
