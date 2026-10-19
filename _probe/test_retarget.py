"""Test the product-side rename-based reskin (aoe2mod.intent.retarget)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.api as A                     # noqa: E402
import aoe2mod.dat.parser as P              # noqa: E402
import aoe2mod.dat.writer as W              # noqa: E402
import aoe2mod.intent.retarget as RT        # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    tk = A.open_toolkit()
    tk._ensure()
    game = tk.game_root
    data, _ = P.load_dat(os.path.join(game, DAT_REL))
    gv = tk._parsed[3]
    stats = tk._stats
    fails = []

    def chk(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    print("A. single record, no family")
    r = RT.plan(game, stats["graphics"], tk._civs, 4, 8)
    chk(r["editable"] is True, "archer <- longbowman is expressible as renames")
    chk(r["retarget"]["no_sld_shipped"] is True, "the plan ships no .sld")
    chk(r["retarget"]["rename_count"] > 0,
        "rename_count %d" % r["retarget"]["rename_count"])
    chk("不复制" in r["description"],
        "the description says no picture is copied")

    print("B. apply it and reparse")
    edits = RT.apply(stats, r["retarget"])
    out, _ = W.serialize_dat(stats, raw=data, gv=gv)
    q = P.Parser(out)
    st2 = q.parse()
    chk(q.r.pos == len(out), "reparsed to clean EOF (%d bytes, delta %+d)"
        % (len(out), len(out) - len(data)))
    after = {g["id"]: g["file"] for g in st2["graphics"]}
    touched = set(e["graphic_id"] for e in edits)
    chk(all(after[e["graphic_id"]] == e["now"] for e in edits),
        "every renamed record names its donor picture")
    chk(all(e["now"].endswith("_x1") for e in edits),
        "every renamed record names an _x1 (x2 is derived)")
    chk(len(touched) == len(edits), "one edit per record, no duplicates")

    print("C. a refusal must say something a person can act on")
    bad = RT.plan(game, stats["graphics"], tk._civs, 8, 4)
    chk(bad["editable"] is False, "longbowman <- archer is refused")
    # Assert the message is a SENTENCE about these two units, not which words it
    # happens to use: an earlier version of this check demanded "record" or
    # "picture" and failed on a perfectly readable message that said "art".
    # This version had the same bug in a smaller font -- it pinned "already
    # share", which is the English spelling of the fact rather than the fact.
    # What actually has to be true: it names a real shared file, so the reader
    # can go and look at it.
    _why = bad["reason"] or ""
    chk(len(_why) > 30 and ".sld" in _why,
        "the refusal explains itself, and names the shared file: %r" % _why[:110])

    print("D. whole family costs the same .dat, not 614 MB of pictures")
    fam = RT.plan(game, stats["graphics"], tk._civs, 83, 594,
                  families=tk._families(), family_scope=True, fill=True)
    chk(fam["editable"] is True, "the whole villager family is expressible")
    rt = fam["retarget"]
    chk(rt["rename_count"] > 200, "rename_count %d" % rt["rename_count"])
    chk(rt["donor_names"] == 8, "the family needs only %d donor picture(s)"
        % rt["donor_names"])
    chk(rt["copy_based_equivalent"]["files"] > 400,
        "the copy model would ship %d files / %.1f MB"
        % (rt["copy_based_equivalent"]["files"],
           rt["copy_based_equivalent"]["megabytes"]))
    chk(rt["derived_siblings_missing"] == [],
        "every donor picture has its _x2 sibling")

    print("E. the PRODUCT delivers the model that was asked for")
    # The defect this pins: `plan` honoured `mode: rename` while `build` silently
    # produced the copy model -- 466 picture files and no .dat -- for a sentence
    # that asked for 244 record renames.  A plan/build disagreement is invisible
    # unless both sides are asked the same question, so both are asked here.
    import shutil
    import tempfile
    _it = {"intent": "unit.sprite", "unit": 83, "donor": 594,
           "whole_family": True, "mode": "rename"}
    _p = tk.plan(_it)
    chk(_p["sprite_mode"] == "rename", "plan reports sprite_mode 'rename'")
    chk(_p["edit_count"] == _p["rename_count"] > 200,
        "plan counts %d records" % _p["edit_count"])
    _tmp = tempfile.mkdtemp(prefix="retarget_build_")
    try:
        _m = tk.build(_it, os.path.join(_tmp, "m"), title="t", author="aoe2mod")
    finally:
        pass
    try:
        _rels = [f["rel"] for f in _m["files"]]
        chk(not any(r.endswith(".sld") for r in _rels),
            "the build ships no .sld at all: %r" % (_rels,))
        chk(any(r.endswith("empires2_x2_p1.dat") for r in _rels),
            "the build ships exactly the .dat")
        chk(_m["edit_count"] == _p["edit_count"],
            "preview %d == manifest %d" % (_p["edit_count"], _m["edit_count"]))
        chk(_m["sprite"]["mode"] == "rename", "the manifest names the model")
        chk(_m["verification"]["ok"] is True
            and not _m["verification"]["renamed_but_wrong"]
            and not _m["verification"]["untouched_but_moved"],
            "the shipped .dat renames %d records and touches nothing else"
            % _m["verification"]["renamed"])
        chk(_m["changes_dat"] is True and _m["mod_contains_dat"] is True,
            "a rename mod changes and contains the .dat")
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)

    print("F. a bundle delivers BOTH models, each counted in its own unit")
    _tmp2 = tempfile.mkdtemp(prefix="retarget_bundle_")
    try:
        _bi = [{"intent": "unit.stat", "unit": "村民", "stat": "hit_points",
                "value": 1000},
               {"intent": "unit.sprite", "unit": 83, "donor": 594,
                "whole_family": True, "mode": "rename"}]
        _bp = tk.plan_bundle(_bi)
        _bm = tk.build_bundle(_bi, os.path.join(_tmp2, "b"), title="tb",
                              author="aoe2mod")
        chk(_bp["sprite_rename_count"] == _bm["rename_edits"] > 200,
            "preview %d renames == manifest %d"
            % (_bp["sprite_rename_count"], _bm["rename_edits"]))
        chk(_bp["edit_count"] == _bm["edit_count"],
            "bundle preview %d == manifest %d"
            % (_bp["edit_count"], _bm["edit_count"]))
        chk(_bp["sprite_file_count"] == 0,
            "a rename sentence copies no file")
        chk(_bm["mod_contains_dat"] is True,
            "the bundle ships the .dat its rename sentence needs")
        _bl = [f["rel"] for f in _bm["files"]]
        chk(not any(r.endswith(".sld") for r in _bl),
            "the bundle ships no picture: %r" % (_bl,))
        # Both edits must survive in the SAME file: the villager's hit points
        # and its picture live in different sections, and one overwriting the
        # other is exactly what a two-stage fold can do wrong.
        _raw2, _ = P.load_dat(_bm["dat"])
        _p2 = P.Parser(_raw2)
        import contextlib
        import io as _io
        with contextlib.redirect_stdout(_io.StringIO()):
            _p2.parse()
        from aoe2mod.dat import locate as _L
        _civs, _c, _g, _t = _L.locate(_raw2, parser=_p2)
        _hp = [u["hit_points"] for u in _civs[0]["units"] if u["id"] == 83]
        chk(_hp == [1000], "the hit-point edit survived the rename fold")
        _gfx = {g["id"]: g for g in _p2.stats["graphics"]}
        _sg = [u["standing_graphic"][0] for u in _civs[0]["units"]
               if u["id"] == 83]
        _file = (_gfx.get(_sg[0]) or {}).get("file") if _sg else None
        chk(_file == "a_herd_sheep_idleA_x1",
            "the picture edit survived too: %r" % (_file,))
        chk(_p2.r.pos == len(_raw2), "the bundle's .dat reparses to its own end")
    finally:
        shutil.rmtree(_tmp2, ignore_errors=True)

    print()
    print("RETARGET: a reskin can be a few hundred record renames instead of "
          "hundreds of megabytes of copied pictures.")
    if fails:
        print("FAILURES: %d" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
