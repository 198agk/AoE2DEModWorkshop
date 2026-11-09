"""Guards the upgrade engine's refusals, and the one case that LOOKS like a
refusal but must not be one.

Four things must be true, and each is a way this tool could quietly "help"
and destroy a mod instead:

1. A generation we never archived has no "before" at all.  Inventing one (going
   to the nearest generation) would move bytes between record layouts that do
   not agree.  This is the one refusal that cannot be worked around, and it must
   say what to do about it.
2. A mod of a DIFFERENT LENGTH from its own generation is NOT a refusal.  A mod
   that ships its own record set (measured: 19968_Eternal Civilization is
   115,179,469 raw bytes, 168,424 records against the shipped 136,861) is
   legitimately bigger, and the record-set planner exists exactly for that.
   Refusing on length alone once already rejected `unit_added_by_mod`, which the
   fixture suite proves is replayable.  What length difference DOES forbid is the
   byte path: `diff_regions` across two geometries reports tens of millions of
   regions that mean "these are two different files", and calling each one an
   author edit would be fabrication.
3. An explicit ``base_dat`` of a different length is likewise legitimate, and
   must go structural.  The report must SAY the lengths differed, so a caller who
   handed over the wrong file sees it instead of a clean-looking merge.
4. A run with rows it cannot carry must refuse to write unless forced, and the
   refusal must name them.  Silence here is the failure mode the whole module
   exists to prevent.

Run: python -X utf8 -u _probe/test_upgrade_guard.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.game.locations as GL
import aoe2mod.mod.archives as AR
from aoe2mod.mod import upgrade as UP

FAILS = []


def ok(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name
          + ((" :: %s" % detail) if detail else ""))
    if not cond:
        FAILS.append(name)


def installed():
    by = {}
    for r in GL.list_mods(GL.find_profile_root()):
        d = os.path.join(r["path"], AR.DAT_REL)
        if os.path.isfile(d):
            by[r["name"]] = d
    return by


def fx(case, part):
    return os.path.join("_out", "_upgrade_fixtures", case, part,
                        "resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    by = installed()
    new = fx("mod_touches_a", "new")
    if not os.path.isfile(new):
        print("  SKIP no fixtures; run _probe/make_upgrade_fixtures.py first")
        return 2

    # --- 1. a generation we never archived is refused, not guessed ----------
    old = [n for n in by if n.startswith("297820_")]
    if old:
        name = old[0]
        t = time.time()
        why = None
        try:
            UP.analyze(mod_dat=by[name])
        except UP.UpgradeError as exc:
            why = str(exc)
        dt = time.time() - t
        ok("a generation with no archived base is refused", why is not None,
           why and why[:40])
        ok("that refusal says what to do about it",
           why is not None and "记录官方数据" in why, why and why[-40:])
        ok("and it decides from the index, without parsing 48 MB", dt < 2.0,
           "%.2fs" % dt)

    # --- 2. a mod with its own record set goes structural, not refused ------
    own = [n for n in by if n.startswith("19968_")]
    if own:
        name = own[0]
        raw = UP._inflate(by[name])
        t = time.time()
        rep = UP.analyze(mod_dat=by[name], new_dat=new)
        dt = time.time() - t
        ok("a mod with its own record set is analysed, not refused",
           rep["verdict"] in UP.VERDICTS, rep["verdict"])
        ok("and the planner chose the record-set path, not the byte path",
           rep["structural"] is True, str(rep["structural"]))
        ok("the report says the two lengths differed",
           any("长度不同" in n for n in rep["notes"]), rep["notes"][:1])
        ok("the base it chose is a different size from the mod",
           rep["base"]["raw_bytes"] != rep["mod"]["raw_bytes"],
           "%s vs %s" % (rep["base"]["raw_bytes"], rep["mod"]["raw_bytes"]))
        ok("the inventory is real, not a fabricated byte count",
           rep["counts"]["units_added"] > 1000 and rep["counts"]["edits"] > 0,
           str(rep["counts"]))
        ok("every unmapped row says why", all(r.get("why")
                                              for r in rep["unmapped"]),
           "%d rows" % len(rep["unmapped"]))
        print("       (%.1fs, %d unmapped, %d added)"
              % (dt, len(rep["unmapped"]), rep["counts"]["units_added"]))

        # --- 4. rows it cannot carry must block the write -------------------
        if rep["unmapped"]:
            why = None
            try:
                UP.upgrade(mod_dat=by[name], new_dat=new,
                           out_dir=os.path.join("_probe", "_tmp", "guard_out"),
                           title="guard must not write")
            except UP.UpgradeError as exc:
                why = str(exc)
            ok("a run with uncarried rows refuses to write", why is not None,
               (why or "")[:60])
            ok("and the refusal names what was left behind",
               why is not None and "搬不过去" in why, (why or "")[:60])
            ok("and nothing was written to disk",
               not os.path.isdir(os.path.join("_probe", "_tmp", "guard_out",
                                              "guard must not write")))

    # --- 3. an explicit base of a different length goes structural ----------
    mod = fx("unit_added_by_mod", "mod")
    base = fx("unit_added_by_mod", "base")
    new2 = fx("unit_added_by_mod", "new")
    if os.path.isfile(mod):
        rep = UP.analyze(mod_dat=mod, base_dat=base, new_dat=new2)
        ok("a longer mod with an explicit base is analysed",
           rep["verdict"] in (UP.MERGEABLE, UP.CONFLICTS), rep["verdict"])
        ok("and its added record is planned, not refused",
           rep["counts"]["units_added"] == 1, str(rep["counts"]))
        ok("the report says the lengths differed",
           any("长度不同" in n for n in rep["notes"]), rep["notes"][:1])

    # --- registry of sizes is cheap and honest ------------------------------
    sizes = AR.size_candidates("VER 8.9")
    ok("size_candidates lists the shipped length",
       93272287 in sizes["sizes"], str(list(sizes["sizes"])))
    ok("size_candidates on an unknown generation is empty",
       AR.size_candidates("VER 1.0")["entries"] == 0)

    print("")
    if FAILS:
        print("GUARD: %d FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("GUARD: EVERY REFUSAL IS EXPLAINED, EVERY LENGTH IS JUDGED")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
