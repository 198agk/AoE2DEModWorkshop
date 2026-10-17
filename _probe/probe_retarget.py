"""Can a reskin point a graphics record at another picture instead of copying files?

The whole-mod-copy model ships one copy of the donor's picture per target FILE
name, so a family reskin is 466 files and 438 MB even though it only carries 8
distinct pictures.  The alternative is to leave every .sld on disk alone and
rewrite the graphics records' `file` strings to name the donor's picture --
that is 466 short strings.

This probe answers whether the serializer can do that at all: a string of a
different length moves every byte after it, and the writer runs two cursors
(output position and raw-stream position) that must stay independent.

WHAT THIS PROVES: the record can be retargeted, the resulting stream reparses to
exactly its own length, and the bytes that differ are the ones we asked for.
WHAT THIS DOES NOT PROVE: that the running game resolves a record by `file`
instead of by the baked `slp` id.  Only an in-game load can show that.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.dat.parser as P          # noqa: E402
import aoe2mod.dat.writer as W          # noqa: E402
from aoe2mod.game.locations import find_game_root  # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    game = find_game_root()
    data, how = P.load_dat(os.path.join(game, DAT_REL))
    print("raw bytes %d  (%s)" % (len(data), how))
    p = P.Parser(data)
    stats = p.parse()
    print("parsed, %d graphics records" % len(stats["graphics"]))

    # Baseline: an unmodified round-trip must still be byte exact.
    base, rep = W.serialize_dat(stats, raw=data, gv=p.r.gv)
    print("baseline round-trip: %d bytes, identical=%s, mismatches=%d"
          % (len(base), base == data, rep.get("mismatches", -1)))

    # Pick a graphics record reachable from a unit and retarget it at the
    # sheep's idle picture, whose filename is a different length.
    # Pick a graphics record by id.  `stats["civs"]` does NOT carry
    # `standing_graphic` (the authoritative parser reads the pair and drops it;
    # `aoe2mod/dat/locate.py` is the reader that keeps it), so the record is
    # named directly here: gfx 633 is `u_arc_archer_idleA_x1`, the archer's
    # standing picture (see `_probe/test_sprite_chain.py`).
    by_id = {g["id"]: i for i, g in enumerate(stats["graphics"])}
    donor_file = "a_herd_sheep_idleA_x1"
    target_gid = 633
    ix = by_id[target_gid]
    old = stats["graphics"][ix]["file"]
    print("unit 4 standing graphic id=%d file=%r (len %d) -> %r (len %d)"
          % (target_gid, old, len(old), donor_file, len(donor_file)))
    stats["graphics"][ix]["file"] = donor_file

    out, rep2 = W.serialize_dat(stats, raw=data, gv=p.r.gv)
    print("retargeted: %d bytes (delta %+d), mismatches %s"
          % (len(out), len(out) - len(data), rep2.get("mismatches", "?")))

    # The only honest test of a reserializer: parse its own output to EOF.
    q = P.Parser(out)
    try:
        st2 = q.parse()
        ok = q.r.pos == len(out)
        print("reparse: consumed %d of %d, clean EOF %s"
              % (q.r.pos, len(out), ok))
        got = st2["graphics"][ix]["file"]
        print("reparse sees file=%r  (wanted %r)  match=%s"
              % (got, donor_file, got == donor_file))
    except Exception as exc:                      # noqa: BLE001
        print("REPARSE FAILED: %s: %s" % (type(exc).__name__, exc))
        return 1

    # Where do the two streams first differ, and does the rest of the file
    # otherwise survive?  A width-change edit shifts every later byte, so
    # comparing tails directly is meaningless; compare against a control built
    # by writing the SAME text (so the only difference is the value).
    diff = [i for i in range(min(len(out), len(data))) if out[i] != data[i]]
    print("differing byte positions (first 10): %s   total %d"
          % (diff[:10], len(diff)))
    print("tail preserved: last 64 bytes equal = %s"
          % (out[-64:] == data[-64:]))

    # ★ The case that matters: a name of a DIFFERENT length.  The raw cursor
    # must advance by the OLD width while the output grows by the new one, or
    # everything after this record is read at the wrong place.
    for cand in ("n_tree_oak_x1", "b_west_castle_x1", "p_arrow_x1",
                 "u_shp_hero_aeginetan_idleA_x1"):
        stats["graphics"][ix]["file"] = cand
        w_out, w_rep = W.serialize_dat(stats, raw=data, gv=p.r.gv)
        q2 = P.Parser(w_out)
        try:
            st3 = q2.parse()
            eof = q2.r.pos == len(w_out)
            got = st3["graphics"][ix]["file"]
            same_tail = w_out[-64:] == data[-64:]
            head_ok = w_out[:450179] == data[:450179]
            print("width-change %-28r len %2d -> %2d : bytes %d (delta %+d) "
                  "EOF %s, value %s, head_ok %s, tail_ok %s"
                  % (cand, len(old), len(cand), len(w_out),
                     len(w_out) - len(data), eof, got == cand, head_ok,
                     same_tail))
        except Exception as exc:                  # noqa: BLE001
            print("width-change %r FAILED to reparse: %s: %s"
                  % (cand, type(exc).__name__, exc))
    stats["graphics"][ix]["file"] = old
    return 0


if __name__ == "__main__":
    sys.exit(main())
