"""Apply the whole-family retarget for real: rename every record, reparse, verify.

The scale probe said a family reskin is 244 record renames and the .dat gets
SMALLER, against 466 files and 438 MB copied.  This builds that file and checks
it the only way a reserializer can be checked: parse the output to EOF and look
at what the records actually say.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.dat.parser as P              # noqa: E402
import aoe2mod.dat.writer as W              # noqa: E402
import aoe2mod.game.sprites as SP           # noqa: E402
import aoe2mod.intent.reskin as RK          # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "out_retarget_family.dat")


def main():
    tk = A.open_toolkit()
    tk._ensure()
    game = tk.game_root
    data, _ = P.load_dat(os.path.join(game, DAT_REL))
    gv = tk._parsed[3]
    stats = tk._stats

    rep = RK.plan(game, stats["graphics"], tk._civs, 83, 594,
                  families=tk._families(), family_scope=True, fill=True)
    want = {}
    clash = {}
    for rel, src in (rep.get("files") or {}).items():
        t = os.path.basename(rel)[:-4]
        d = src[:-4] if src.endswith(".sld") else src
        if t in want and want[t] != d:
            clash.setdefault(t, {want[t]}).add(d)
        want[t] = d
    print("target names %d, donor names %d, conflicting targets %d"
          % (len(want), len(set(want.values())), len(clash)))

    recs = [g for g in stats["graphics"] if (g.get("file") or "") in want]
    print("records to rename: %d" % len(recs))

    # Refuse to guess: every donor picture must already be on disk, because the
    # point of this mod is that it ships no .sld at all.
    gdir = SP.graphics_dir(game)
    absent = sorted(set(d for d in want.values()
                        if not os.path.exists(os.path.join(gdir, d + ".sld"))))
    if absent:
        print("ABORT: %d donor picture(s) not on disk, e.g. %s"
              % (len(absent), absent[:5]))
        return 1

    touched = set()
    for g in recs:
        touched.add(g["id"])
        g["file"] = want[g["file"]]
    out, wrep = W.serialize_dat(stats, raw=data, gv=gv)
    print("serialized %d bytes (delta %+d)" % (len(out), len(out) - len(data)))

    q = P.Parser(out)
    st2 = q.parse()
    print("reparse: consumed %d of %d, clean EOF %s"
          % (q.r.pos, len(out), q.r.pos == len(out)))
    by_id = {g["id"]: g for g in st2["graphics"]}
    donor_names = set(want.values())
    bad = [i for i in touched if by_id[i]["file"] not in donor_names]
    print("renamed records that did NOT end up naming a donor picture: %d"
          % len(bad))
    # Every record we did not touch must still name exactly what it named.
    before = {g["id"]: g["file"] for g in stats["graphics"]}
    drifted = [i for i, f in before.items()
               if i not in touched and by_id[i]["file"] != f]
    print("untouched records whose file changed: %d" % len(drifted))
    with open(OUT, "wb") as fh:
        fh.write(out)
    print("wrote %s (%d bytes)" % (OUT, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
