"""How small could a reskin be if it renamed records instead of copying files?

v12 ships 466 .sld files (438 MB) because every target FILENAME needs a copy of
the donor's picture on disk.  The alternative: rewrite the graphics records'
`file` strings so a target record names the donor's picture, which is already
shipped.  Then nothing is copied and the mod is one .dat.

This measures the real scale for the villager family: how many records would
change, how much the .dat grows or shrinks, and whether every target name has a
donor name to point at.
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


def main():
    tk = A.open_toolkit()
    tk._ensure()
    game = tk.game_root
    data, _how = P.load_dat(os.path.join(game, DAT_REL))
    stats = tk._stats
    idx = SP.art_index(game, stats["graphics"])

    for tag, target, donor, fam in (
            ("single villager", 83, 594, False),
            ("whole family", 83, 594, True)):
        rep = RK.plan(game, stats["graphics"], tk._civs, target, donor,
                      families=tk._families(), family_scope=fam, fill=True)
        files = rep.get("files") or {}
        print("\n== %s ==" % tag)
        print("  files a copy-based reskin ships: %d (%.1f MB)"
              % (len(files), sum(
                  os.path.getsize(os.path.join(game, r))
                  for r in files) / (1024.0 * 1024.0)))
        # The retarget needs, for each target basename, the donor basename.
        want = {}
        for rel, src in files.items():
            t = os.path.basename(rel)[:-4]
            d = src[:-4] if src.endswith(".sld") else src
            want[t] = d
        # Which graphics records name one of those target files?
        recs = [g for g in stats["graphics"]
                if (g.get("file") or "") in want]
        delta = sum(len(want[g["file"]]) - len(g["file"]) for g in recs)
        print("  graphics records naming them: %d" % len(recs))
        print("  .dat size delta if renamed: %+d bytes" % delta)
        missing = [g["file"] for g in recs
                   if not os.path.exists(os.path.join(
                       SP.graphics_dir(game), want[g["file"]] + ".sld"))]
        print("  donor pictures missing from disk: %d" % len(missing))
        print("  distinct target names: %d, distinct donor names: %d"
              % (len(set(want)), len(set(want.values()))))

    # Control: a single record retarget round-trips exactly and stays tiny.
    base, _ = W.serialize_dat(stats, raw=data, gv=tk._parsed[3])
    print("\nbaseline reserialize: %d bytes, identical=%s"
          % (len(base), base == data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
