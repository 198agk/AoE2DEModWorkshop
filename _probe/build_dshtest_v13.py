"""v13: the same villager-to-sheep reskin, done by renaming records instead of copying files.

v12 ships 466 .sld files and 438 MB because every target FILENAME needs the
donor's picture copied onto it.  But the .dat already says, per graphics record,
which file to load -- and one donor picture can serve any number of records.
So the reskin can be 244 record renames and ONE mod file.

WHAT IS PROVEN HERE: the records say what we asked, the stream reparses to its
own length, and no record we did not touch moved.
WHAT IS NOT PROVEN: that the running game resolves a record by `file` rather
than by the `slp` id baked beside it.  One in-game look settles it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.dat.parser as P              # noqa: E402
import aoe2mod.dat.writer as W              # noqa: E402
import aoe2mod.game.sprites as SP           # noqa: E402
import aoe2mod.intent.reskin as RK          # noqa: E402
import aoe2mod.mod.emitter as E             # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testmod_name as TN                   # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out_dshtest_v13")
V = 13


def main():
    tk = A.open_toolkit()
    tk._ensure()
    game = tk.game_root
    data, _ = P.load_dat(os.path.join(game, DAT_REL))
    gv = tk._parsed[3]
    stats = tk._stats

    rep = RK.plan(game, stats["graphics"], tk._civs, 83, 594,
                  families=tk._families(), family_scope=True, fill=True)
    files = rep.get("files") or {}
    want = {}
    for rel, src in files.items():
        t = os.path.basename(rel)[:-4]
        d = src[:-4] if src.endswith(".sld") else src
        if t in want and want[t] != d:
            raise SystemExit("target %r wants two donors: %r and %r"
                             % (t, want[t], d))
        want[t] = d
    gdir = SP.graphics_dir(game)
    absent = sorted(set(d for d in want.values()
                        if not os.path.exists(os.path.join(gdir, d + ".sld"))))
    if absent:
        raise SystemExit("donor picture(s) not on disk: %s" % absent[:5])

    recs = [g for g in stats["graphics"] if (g.get("file") or "") in want]
    referenced = set(g["file"] for g in recs)
    print("copy-based reskin: %d files / %.1f MB"
          % (len(files), sum(os.path.getsize(os.path.join(game, r))
                             for r in files) / (1024.0 * 1024.0)))
    # The half that is never named is the `_x2` siblings: no record ever names
    # an _x2 (measured 0 of 8,291), the engine derives it by appending.  A copy
    # model must ship them anyway because the engine will ask; a retarget model
    # needs only the donor's copy, which is already shipped art.
    print("files named directly by a record: %d; derived (_x2) siblings: %d"
          % (len(referenced), len(set(want) - referenced)))
    print("records to rename: %d, donor pictures: %d"
          % (len(recs), len(set(want.values()))))

    touched = set()
    for g in recs:
        touched.add(g["id"])
        g["file"] = want[g["file"]]
    out, _wrep = W.serialize_dat(stats, raw=data, gv=gv)
    print("serialized %d bytes (delta %+d)" % (len(out), len(out) - len(data)))

    q = P.Parser(out)
    st2 = q.parse()
    if q.r.pos != len(out):
        raise SystemExit("reparse stopped at %d of %d" % (q.r.pos, len(out)))
    by_id = {g["id"]: g for g in st2["graphics"]}
    donor_names = set(want.values())
    bad = [i for i in touched if by_id[i]["file"] not in donor_names]
    before = {g["id"]: g["file"] for g in stats["graphics"]}
    drifted = [i for i, f in before.items()
               if i not in touched and by_id[i]["file"] != f]
    print("reparse clean EOF True; renamed-but-wrong %d; untouched-drifted %d"
          % (len(bad), len(drifted)))
    if bad or drifted:
        raise SystemExit("refusing to ship a file that fails its own checks")

    title = TN.name_for(V, "村民变羊（改记录名，不复制贴图）")
    desc = TN.description_for(
        V, "村民全族 244 条图形记录改指向羊的贴图；不再复制任何 .sld",
        "整族（含建造/砍树/挖矿/搬运/播种）都应是羊",
        extra_lines=[
            "体积从 438 MB 降到约 12 MB：同一张羊图被 244 条记录共用，"
            "而旧做法要为每个文件名各存一份拷贝。",
            "这是新的做法，游戏是否按记录里的文件名去取图，需要你开局看一眼。",
            "六个 Chronicles 文明（阿契美尼德/雅典/马其顿/普鲁/斯巴达/色雷斯）"
            "的攻击帧网格仍是 45 帧，不要用它们判断。",
        ])
    print("title %r (%d bytes)" % (title, TN.utf8_len(title)))

    man = E.emit_data_mod(
        OUT, out,
        E.make_info(title, author="aoe2mod test", description=desc,
                    CacheStatus=0),
        thumbnail=None, base_dir=game, overwrite=True)
    print("emitted: %d file(s)" % len(man["files"]))
    for f in man["files"]:
        print("   %-46s %d B" % (f["rel"], f["bytes"]))
    print("dat_raw_bytes %d  changes_dat %s  dat_is_carrier %s"
          % (man["dat_raw_bytes"], man["changes_dat"], man["dat_is_carrier"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
