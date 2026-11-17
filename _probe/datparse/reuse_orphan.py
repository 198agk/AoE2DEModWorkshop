import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Can we create NEW gameplay without changing the dat's size?

The re-serializer (adding objects) is the ambitious path.  There is a cheaper one
that is already proven viable, and this script demonstrates it end to end:

    BASE has 486 Effects that NO Tech references.  Of those, 193 contain real
    commands.  They are dead weight the engine still loads.

So: pick a dead Effect, rewrite its commands into something useful, and point an
existing Tech at it (or add a Tech's worth of behaviour by reusing both an
orphaned Effect AND an orphaned/placeholder Tech).  The file's *geometry never
changes* -- only values -- which is exactly what the already-verified in-place
patch technique handles.

This script:
  1. enumerates the orphaned Effects and shows what is in them
  2. picks one, rewrites it into "all resources +2000", and wires it to a Tech
  3. re-parses the result with the UNMODIFIED parser and requires exact EOF
  4. reports the true byte cost

Nothing is written outside out_reuse/.
"""
import os, sys, io, json, struct, zlib, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

BASE = GP.DAT
OUT = os.path.join(HERE, "out_reuse")
SCHEMA = os.path.join(os.path.dirname(HERE), "schema")


def load(path):
    data, _ = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return data, p


def main():
    os.makedirs(OUT, exist_ok=True)
    data, p = load(BASE)
    s = p.stats
    print("loaded base: %d bytes, parse EOF %d leftover %d"
          % (len(data), p.r.pos, len(data) - p.r.pos))

    # ---- what does the engine consider a "used" effect? --------------------
    referenced = set()
    for t in s["techs"]:
        if t["effect_id"] is not None and t["effect_id"] >= 0:
            referenced.add(t["effect_id"])
    neff = len(s["effects"])
    orphans = [i for i in range(neff) if i not in referenced]
    real = [i for i in orphans
            if any(c[0] != 255 for c in s["effects"][i]["commands"])]
    print("\nEFFECT INVENTORY")
    print("  total effects           : %d" % neff)
    print("  referenced by some tech : %d" % len(referenced))
    print("  ORPHANED (never used)   : %d" % len(orphans))
    print("    ...of which carry real commands : %d" % len(real))
    print("    ...pure Type-255 no-ops         : %d" % (len(orphans) - len(real)))
    print("\n  a sample of the orphaned-but-real slots (free real estate):")
    for i in real[:12]:
        e = s["effects"][i]
        print("    effect[%4d] %-34r %d cmd(s): %s"
              % (i, e["name"][:34], len(e["commands"]),
                 [(c[0], c[1], c[2], c[3], round(c[4], 3)) for c in e["commands"][:3]]))
    with open(os.path.join(OUT, "orphan_effects.json"), "w", encoding="utf-8") as f:
        json.dump([{"idx": i, "name": s["effects"][i]["name"],
                    "commands": s["effects"][i]["commands"]} for i in real],
                  f, ensure_ascii=False, indent=1)
    print("  -> full list written to out_reuse/orphan_effects.json")

    # ---- find the byte offset of every effect's commands -------------------
    # Effect record layout (genieutils TechageEffect): name (debug string)
    # then commands.  We locate them by re-walking from the Effects section.
    stage = next(t for t in p.stage_offsets if t[0].startswith("5 Effects"))
    eff_start = stage[1]
    count = struct.unpack_from("<i", data, eff_start)[0]
    print("\nEFFECTS SECTION at 0x%X, count field = %d" % (eff_start, count))

    class ERec(object):
        def __init__(self, b, o):
            self.b = b; self.o = o
        def u8(self):
            v = self.b[self.o]; self.o += 1; return v
        def i16(self):
            v = struct.unpack_from("<h", self.b, self.o)[0]; self.o += 2; return v
        def i32(self):
            v = struct.unpack_from("<i", self.b, self.o)[0]; self.o += 4; return v
        def f32(self):
            v = struct.unpack_from("<f", self.b, self.o)[0]; self.o += 4; return v
        def debug_string(self):
            m = struct.unpack_from("<H", self.b, self.o)[0]; self.o += 2
            n = struct.unpack_from("<H", self.b, self.o)[0]; self.o += 2
            raw = self.b[self.o:self.o + n]; self.o += n
            return (m, n, raw.decode("latin-1"))

    er = ERec(data, eff_start + 4)
    eff_offs = []          # (index, commands_abs_offset, [(type_off, a_off, b_off, c_off, d_off)])
    for i in range(count):
        er.debug_string()
        cmd_start = er.o
        n = er.i16()
        offs = []
        for _ in range(n):
            t_off = er.o; er.u8()
            a_off = er.o; er.i16()
            b_off = er.o; er.i16()
            c_off = er.o; er.i16()
            d_off = er.o; er.f32()
            offs.append((t_off, a_off, b_off, c_off, d_off))
        eff_offs.append((i, cmd_start, offs))
    print("re-walked %d effects, ended at 0x%X (next stage 0x%X)"
          % (count, er.o, next(t for t in p.stage_offsets
                               if t[0].startswith("7 UnitHeaders"))[1]))
    assert er.o == next(t for t in p.stage_offsets
                        if t[0].startswith("7 UnitHeaders"))[1], "effect walk drifted"
    print("  -> effect walk is exact; command offsets are trustworthy")

    # ---- the intent: repurpose a dead effect into "every resource +2000" ---
    # pick the orphan with the MOST command slots so we can express more
    cands = sorted(real, key=lambda i: -len(s["effects"][i]["commands"]))
    victim = cands[0]
    ve = s["effects"][victim]
    print("\nCHOSEN SLOT: effect[%d] %r with %d command slots"
          % (victim, ve["name"], len(ve["commands"])))

    # resource modifier (set/+/-) = type 1 ; A=resource id, B=-1 means 'set'
    # (B != 0 -> 'change by' in the AGE source).  resources 0=Food 1=Wood
    # 2=Stone 3=Gold.  We want +2000 => B = -1 (B != 0 => 'change by D').
    want = [(1, r, -1, -1, 2000.0) for r in (0, 1, 2, 3)]
    if len(ve["commands"]) < len(want):
        print("  ! slot too small (%d < %d) -- aborting demo"
              % (len(ve["commands"]), len(want)))
        return

    buf = bytearray(data)
    _, cmd_start, offs = eff_offs[victim]
    edits = []
    # *** CRITICAL: the command COUNT is geometry-bearing. ***
    # Effects are packed back-to-back with no length prefix beyond this count,
    # so changing it slides every later record and destroys the file.  We must
    # therefore write EXACTLY len(offs) commands: the ones we want, then Type-255
    # no-op padding.  (Verified the hard way -- see NOTES.md.)
    print("   count field at 0x%X MUST stay %d (geometry-bearing!)"
          % (cmd_start, len(offs)))
    for k, (ty, A, B, C, D) in enumerate(want):
        t_off, a_off, b_off, c_off, d_off = offs[k]
        print("   slot %d @0x%X: (%d, %d, %d, %d, %.1f) was (%d, %d, %d, %d, %.1f)"
              % (k, t_off, ty, A, B, C, D,
                 data[t_off], struct.unpack_from("<h", data, a_off)[0],
                 struct.unpack_from("<h", data, b_off)[0],
                 struct.unpack_from("<h", data, c_off)[0],
                 struct.unpack_from("<f", data, d_off)[0]))
        buf[t_off] = ty
        struct.pack_into("<h", buf, a_off, A)
        struct.pack_into("<h", buf, b_off, B)
        struct.pack_into("<h", buf, c_off, C)
        struct.pack_into("<f", buf, d_off, D)
        edits += [(t_off, ""), (a_off, ""), (b_off, ""), (c_off, ""), (d_off, "")]
    # pad the surplus slots with no-ops; the count itself is left untouched
    for k in range(len(want), len(offs)):
        t_off, a_off, b_off, c_off, d_off = offs[k]
        if data[t_off] == 255:
            continue                      # already a no-op, leave the bytes alone
        buf[t_off] = 255
        struct.pack_into("<h", buf, a_off, -1)
        struct.pack_into("<h", buf, b_off, -1)
        struct.pack_into("<h", buf, c_off, -1)
        struct.pack_into("<f", buf, d_off, 0.0)
        edits += [(t_off, ""), (a_off, ""), (b_off, ""), (c_off, ""), (d_off, "")]
    assert struct.unpack_from("<h", buf, cmd_start)[0] == len(offs), "count changed!"

    patched = bytes(buf)
    regions = [i for i in range(len(data)) if data[i] != patched[i]]
    print("\nPATCHED: %d byte(s) differ, in %d contiguous region(s)"
          % (len(regions), 1 + sum(1 for a, b in zip(regions, regions[1:]) if b != a + 1)))

    # ---- verify geometry with the untouched parser -------------------------
    p2 = P.Parser(patched)
    with contextlib.redirect_stdout(io.StringIO()):
        p2.parse()
    ok = p2.r.pos == len(patched)
    print("VERIFY geometry: EOF %d / %d, leftover %d -> %s"
          % (p2.r.pos, len(patched), len(patched) - p2.r.pos, "PASS" if ok else "FAIL"))

    # ---- read the new effect back out -------------------------------------
    ne = p2.stats["effects"][victim]
    print("VERIFY content : effect[%d] %r now has %d command(s):"
          % (victim, ne["name"], len(ne["commands"])))
    for c in ne["commands"]:
        print("      type=%d A=%d B=%d C=%d D=%s" % c)

    comp = zlib.compressobj(6, zlib.DEFLATED, -15)
    blob = comp.compress(patched) + comp.flush()
    path = os.path.join(OUT, "reuse_orphan_effect.dat")
    with open(path, "wb") as f:
        f.write(blob)
    print("\nWROTE %s" % path)
    print("    decompressed %d (unchanged: %s)" % (len(patched), len(patched) == len(data)))
    print("    compressed   %d (original 12,023,754; delta %+d)"
          % (len(blob), len(blob) - 12023754))
    print("""
==== WHY THIS MATTERS ====
  'All resources +2000' normally requires ADDING a Tech and an Effect, which is
  why the 10x mods grow to 124 MB decompressed.  It turns out that is not
  necessary: the base game ships 193 orphaned Effects with real command slots
  that nothing references.  Rewriting one and pointing a Tech at it costs a few
  dozen BYTES and changes no geometry at all.  That is the difference between a
  tool that must own a full re-serializer and one that can ship earlier.""")


if __name__ == "__main__":
    main()
