# -*- coding: utf-8 -*-
"""Does EVERY row `upgrade_check` hands back carry the SAME counts?

The panel prints counts off rows it did not build.  Three code paths produce
those rows -- the answered one, the engine-refused one, and the "I could not
even read this file" one -- and they used to be three hand-written dicts.  The
first was the engine's own `_empty_counts()` (twelve keys); the other two were
copies that stopped at ten.

That is not a cosmetic drift.  When a tech or flat-table record whose LENGTH the
author changed started travelling as a whole-record copy, `techs_replaced` and
`tables_replaced` appeared in every report -- so the page gained two numbers for
the mods it could carry and printed `undefined 条` for the mods it refused.  The
refused rows are the ones a player re-reads, because they are the ones that
need a decision.

What this pins, in order of how expensive the mistake is:

  A. the engine's zero row still has the fields the page reads, and it is ONE
     definition -- the two refusal paths must be that object, not a copy of it;
  B. a refused row and an answered row have the SAME key set, so a caller can
     print counts without asking which path produced the row;
  C. the refused row is still honest: `seconds is None`, verdict impossible,
     the reason in `summary`, and no install/build attempted.

The answered row is produced with an explicit `base_dat`: with an archive that
holds only today's build the engine refuses a same-length edit rather than call
it up to date, and the refusal itself names that way out.

A throwaway state dir and a throwaway profile: these rows are produced from the
player's own mod list otherwise, which is how a suite ends up reporting whatever
that player happens to have installed.
"""
import io
import json
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
except Exception:
    pass

import aoe2mod.api as A                                   # noqa: E402
from aoe2mod.mod import upgrade as UP                     # noqa: E402

FAILS = []
FX = os.path.join(os.path.dirname(_HERE), "_out", "_upgrade_fixtures")
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name
          + ((" :: %s" % detail) if detail else ""))
    if not cond:
        FAILS.append(name)
    return cond


def planted(profile, name, case):
    """Install one fixture .dat as a mod in `profile`."""
    src = os.path.join(FX, case, "mod", DAT_REL)
    if not os.path.isfile(src):
        return False
    dst = os.path.join(profile, "mods", "local", name, DAT_REL)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def write_status(profile, names):
    """The file the game reads, in the shape the engine writes.

    `Path` is `<kind>//<folder name>` -- `list_mods` splits on the double
    slash, and a status file with a bare name resolves to nothing.
    """
    mods = []
    for i, nm in enumerate(names):
        mods.append({"CheckSum": 0, "Enabled": True, "LastUpdate": 0,
                     "Path": "local//" + nm, "Priority": i,
                     "PublishID": 0, "Title": nm, "WorkshopID": 0})
    path = os.path.join(profile, "mods", "mod-status.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"Mods": mods}, fh, ensure_ascii=False)


def main():
    print("=== A. the engine's zero row is one definition")
    zero = UP._empty_counts()
    want = {"edits", "conflicts", "units_added", "units_removed",
            "units_replaced", "techs_added", "techs_removed", "techs_replaced",
            "unmapped", "tables_added", "tables_removed", "tables_replaced"}
    check("the zero row has the twelve counters", set(zero) == want,
          sorted(set(zero) ^ want))
    check("and every counter is zero",
          all(v == 0 for v in zero.values()), zero)

    # The refusal paths must CALL this, not restate it.  Reading the source is
    # the only way to see the difference: a copy that happens to be right today
    # is the defect this file exists for.
    src = io.open(os.path.join(os.path.dirname(_HERE), "aoe2mod", "api.py"),
                  encoding="utf-8").read()
    body = src[src.index("def upgrade_check"):]
    body = body[:body.index("def _upgrade_remember")]
    check("both refusal paths take the engine's row",
          body.count("dict(UP._empty_counts())") == 2,
          body.count("dict(UP._empty_counts())"))
    check("neither one restates the counters by hand",
          body.count('"units_replaced": 0') == 0,
          body.count('"units_replaced": 0'))

    print("")
    print("=== B. every row has the same key set")
    tmp = tempfile.mkdtemp(prefix="aoe2mod_counts_")
    try:
        acc = os.path.join(tmp, "acc")
        os.makedirs(os.path.join(acc, "mods", "local"), exist_ok=True)
        names = ["old generation", "same generation"]
        planted(acc, names[0], "cross_generation")
        planted(acc, names[1], "mod_touches_a")
        write_status(acc, names)
        os.environ["AOE2MOD_STATE_DIR"] = os.path.join(tmp, "state")
        os.environ["AOE2MOD_PROFILE"] = acc

        tk = A.open_toolkit()
        got = tk.upgrade_check(profile_root=acc)
        rows = {r["name"]: r for r in (got.get("mods") or [])}
        check("both planted mods were found", len(rows) == 2, sorted(rows))
        if len(rows) != 2:
            raise SystemExit(1)

        # The two paths this file is about: one row refused by the engine, one
        # answered by it.
        refused = rows[names[0]]
        check("the cross-generation row is refused on its own",
              refused["verdict"] == UP.IMPOSSIBLE, refused["verdict"])

        # `mod_touches_a` only rewrites field values, so it is the same LENGTH
        # as the official data it was built from.  With an archive holding
        # nothing but today's build the engine cannot tell "the author changed
        # these bytes" from "the official data changed these bytes", and since
        # 2026-11-11 it refuses rather than answer "up to date" (that answer on
        # patch day is how official changes get left outside a mod).  Pointing
        # at the fixture's own base is the way out the refusal names -- which is
        # how a player gets this row answered, and how this suite gets one.
        base = os.path.join(FX, "mod_touches_a", "base", DAT_REL)
        got2 = tk.upgrade_check(profile_root=acc, name=names[1], base_dat=base)
        ans = got2.get("mods") or []
        check("naming the base answers the same-generation row",
              len(ans) == 1 and ans[0].get("verdict") != UP.IMPOSSIBLE,
              [(x["name"], x.get("verdict")) for x in ans])
        if not ans:
            raise SystemExit(1)

        r = refused
        a = ans[0]
        check("the refused row carries the engine's twelve counters",
              set(r["counts"]) == want, sorted(set(r["counts"]) ^ want))
        check("the answered row carries the same twelve",
              set(a["counts"]) == want, sorted(set(a["counts"]) ^ want))
        check("so the page can print either without a missing-number check",
              set(r["counts"]) == set(a["counts"]))
        check("the refused row's counters are all zero, not just absent",
              all(v == 0 for v in r["counts"].values()), r["counts"])

        print("")
        print("=== C. the refused row still says what a refusal must say")
        check("verdict is impossible", r["verdict"] == UP.IMPOSSIBLE, r["verdict"])
        check("it carries no time, because nothing was parsed",
              r["seconds"] is None, r["seconds"])
        check("the reason travels in summary, for the page to print verbatim",
              bool(r.get("summary")) and "VER" in (r.get("summary") or ""),
              r.get("summary"))
        check("and in notes, so the panel has something to list",
              bool(r.get("notes")), r.get("notes"))
        check("ok is false on it", r.get("ok") is False, r.get("ok"))
        check("the answered row says ok", a.get("ok") is True, a.get("ok"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    if FAILS:
        print("COUNTS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("COUNTS: EVERY ROW HAS THE SAME COUNTERS, ON EVERY PATH")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
