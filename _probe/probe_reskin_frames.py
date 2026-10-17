"""Is the graphics record's (frame_count, angle_count) a reliable stand-in for
what the .sld file actually contains?

The product currently says nothing about frame grids, and the survey of this
layer found that a frame-count mismatch "plays the wrong frames rather than
erroring".  If copying the donor's file over the target's NAME changes the frame
count the engine sees, a garbled sprite would not cleanly answer "does a loose
.sld override the packed one".

So: read the real 16-byte SLD header (num_frames) of both files and compare it
with the record's frame_count * angle_count.  If the record is a faithful proxy,
the planner can use it without touching any file.
"""
import os
import struct
import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()
idx = tk._reskin_art()
civs = tk._parsed[1]
graphics = tk._stats["graphics"]
gdir = os.path.join(tk.game_root, "resources", "_common", "drs", "graphics")


def sld_frames(name):
    p = os.path.join(gdir, name + ".sld")
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as fh:
        head = fh.read(16)
    if len(head) < 16 or head[:4] != b"SLDX":
        return None
    _sig, _ver, nframes = struct.unpack_from("<4sHH", head, 0)
    return nframes


def recs_for(fname):
    return [g for g in graphics if (g.get("file") or "").strip() == fname]


def unit_of(uid):
    for c in civs:
        for u in c["units"]:
            if u["id"] == uid:
                return u
    return None


def report(tid, tname, did, dname):
    ta, da = idx.art(unit_of(tid)), idx.art(unit_of(did))
    print("=== %s (%d) <- %s (%d) ===" % (tname, tid, dname, did))
    for anim in sorted(set(ta["tokens"]) & set(da["tokens"])):
        tf, df = ta["tokens"][anim], da["tokens"][anim]
        tr, dr = recs_for(tf), recs_for(df)
        tgrid = sorted({(r.get("frame_count"), r.get("angle_count")) for r in tr})
        dgrid = sorted({(r.get("frame_count"), r.get("angle_count")) for r in dr})
        tsl, dsl = sld_frames(tf), sld_frames(df)
        tprod = sorted({(r.get("frame_count") or 0) * (r.get("angle_count") or 0)
                        for r in tr})
        dprod = sorted({(r.get("frame_count") or 0) * (r.get("angle_count") or 0)
                        for r in dr})
        print("   %-8s" % anim)
        print("      target %-30s record=%-10s product=%-10s sld=%s"
              % (tf, tgrid, tprod, tsl))
        print("      donor  %-30s record=%-10s product=%-10s sld=%s"
              % (df, dgrid, dprod, dsl))
        fits = tgrid == dgrid and tsl == dsl
        print("      %s" % ("OK -- same grid AND same real frame count" if fits
                            else "DIFFERENT"))
    print()


for args in ((83, "Villager (male)", 594, "Sheep"),
             (83, "Villager (male)", 4, "Archer"),
             (4, "Archer", 83, "Villager (male)")):
    report(*args)

print("=== how faithful is record product vs the real header, across the corpus? ===")
same = diff = nosld = 0
examples = []
for g in graphics:
    f = (g.get("file") or "").strip()
    if not f:
        continue
    n = sld_frames(f)
    if n is None:
        nosld += 1
        continue
    prod = (g.get("frame_count") or 0) * (g.get("angle_count") or 0)
    if prod == n:
        same += 1
    else:
        diff += 1
        if len(examples) < 6:
            examples.append((g.get("id"), f, g.get("frame_count"),
                             g.get("angle_count"), prod, n))
print("  record product == sld header : %d" % same)
print("  record product != sld header : %d" % diff)
print("  no such .sld on disk         : %d" % nosld)
for e in examples:
    print("    gfx %-6d %-32s fc=%-3s ang=%-3s prod=%-6s sld=%s" % e)
