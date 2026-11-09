# -*- coding: utf-8 -*-
"""End to end: say a sentence, get a mod installed in the game's mod folder.

This is the whole product promise in one script:
    open_toolkit() -> build(intent) -> install() -> the engine's own file lists it

Everything is sandboxed.  The real profile is READ (to prove the flow works
against the machine's true 7-mod setup) but never written.

The strongest check is last: the .dat that ends up inside the installed mod is
re-inflated and re-parsed with the UNMODIFIED parser, from the installed
location, and must reach exact EOF.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import aoe2mod.api as A  # noqa: E402
from aoe2mod.dat import parser as P  # noqa: E402
from aoe2mod.game import locations as G  # noqa: E402

REAL_PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
REAL_ACCOUNT = "76561198406248391"
FAILS = []


def check(label, cond, detail=""):
    print("  [%s] %s%s" % ("OK " if cond else "FAIL", label,
                           ("  -- " + detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def _snapshot(mods_dir):
    """Every file under the live mods directory with its size + mtime."""
    seen = {}
    for root, _dirs, files in os.walk(mods_dir):
        for f in files:
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            seen[os.path.relpath(p, mods_dir)] = (st.st_size, st.st_mtime_ns)
    return seen


def main():
    tmp = tempfile.mkdtemp(prefix="aoe2e2e_")
    try:
        # Sandbox profile: two accounts, the real status file copied in.
        prof = tmp
        accdir = os.path.join(prof, REAL_ACCOUNT, "mods")
        os.makedirs(os.path.join(accdir, "local"))
        os.makedirs(os.path.join(accdir, "subscribed"))
        real_status = os.path.join(REAL_PROFILE, REAL_ACCOUNT, "mods",
                                   "mod-status.json")
        before = open(real_status, "rb").read()
        shutil.copy2(real_status, os.path.join(accdir, "mod-status.json"))
        os.makedirs(os.path.join(prof, "0", "mods", "local", "x"))
        # The live profile is MUTABLE -- it gains and loses entries (the product
        # itself installed a local mod; the user removed test mods).  Every count
        # below is therefore stated relative to the fixture, never as a literal:
        # a literal goes stale and then the suite fails for a reason that says
        # nothing about install().  `_snapshot` keeps the absolute promise ("THIS
        # run wrote nothing to the real profile") in the form it can be checked.
        _live = json.loads(open(real_status, encoding="utf-8-sig").read())
        n0 = len(_live["Mods"])
        real_before = _snapshot(os.path.dirname(real_status))

        print("=== 1. open the real game ===")
        tk = A.open_toolkit()
        check("toolkit opened", tk is not None)
        d = tk.describe(4)
        check("describe(4) is the Archer", d.get("name") == "步弓手", str(d.get("name")))
        # Do NOT hardcode the count: `costs` is reported alongside the stats, and
        # the number of stats is whatever the schema declares.  A literal here
        # goes stale the moment a field is bound (it said 11 after min_range and
        # accuracy were added), and a stale literal is a test that fails for the
        # wrong reason -- or worse, passes while the schema moved on.
        _declared = tk.schema()["intents"]["intents"]["unit.stat"]["fields"]["stat"]["options"]
        _stats = [k for k in d.get("stats", {}) if k != "costs"]
        check("it reports every declared stat (%d)" % len(_declared),
              sorted(_stats) == sorted(_declared),
              "reported %s / declared %s" % (sorted(_stats), sorted(_declared)))
        check("costs is reported separately", "costs" in d.get("stats", {}))

        print("=== 2. ask for something in plain language ===")
        # The selector key is "intent" (NOT "kind": "kind" is itself a *field*
        # of unit.attack_class, so using it there silently resolves to None).
        intent = {"intent": "unit.stat", "unit": "步弓手",
                  "stat": "displayed_attack", "delta": 1}
        plan = tk.plan(intent)
        check("plan is accepted", plan["edit_count"] > 0, str(plan["edit_count"]))
        check("plan names the unit", "步弓手" in plan["description"],
              plan["description"])
        check("plan writes both panel and damage slots",
              plan["edit_count"] >= 63 and plan.get("mirror_count"), str(plan))

        print("=== 3. build into a scratch folder (NOT the game yet) ===")
        out = os.path.join(tmp, "_build", "弓箭手攻击力+1")
        man = tk.build(intent, out, title="弓箭手攻击力+1", author="E2E",
                       description="end to end test")
        check("build wrote a folder", os.path.isdir(man["mod_dir"]))
        check("built .dat reparses to exact EOF", man["reparse_ok"] is True,
              "leftover %s" % man.get("reparse_leftover"))
        check("all 63 civs were edited", man["civs_edited"] == 63,
              str(man["civs_edited"]))
        check("verification says ok", bool(man["verification"].get("ok")),
              str(man["verification"])[:200])
        check("nothing installed yet (build is not install)",
              not os.path.exists(os.path.join(accdir, "local", "弓箭手攻击力+1")))

        print("=== 4. install it into the game's mod folder ===")
        inst = tk.install(out, title="弓箭手攻击力+1", position=0,
                          profile_root=prof)
        check("installed", inst["installed"] is True)
        check("status backup taken", os.path.exists(inst["status_backup"]))
        check("list grew by exactly one", inst["status_entries"] == n0 + 1,
              "%s vs %s" % (inst["status_entries"], n0 + 1))
        check("it is priority 1", inst["priority"] == 1, str(inst["priority"]))
        check("path field is local//", inst["path_field"].startswith("local//"),
              inst["path_field"])
        check("the installed .dat exists", inst["dat"] is not None)

        print("=== 5. read back what the engine would read ===")
        doc, acc, raw = G.read_status_doc(prof)
        check("the engine's list now has the mod first",
              doc["Mods"][0]["Path"] == "local//弓箭手攻击力+1",
              doc["Mods"][0]["Path"])
        check("it is enabled", doc["Mods"][0]["Enabled"] is True)
        check("title round-trips as UTF-8",
              doc["Mods"][0]["Title"] == "弓箭手攻击力+1",
              doc["Mods"][0]["Title"])
        check("every original mod is still present, in order",
              [e["Title"] for e in doc["Mods"][1:]] ==
              [e["Title"] for e in _live["Mods"]])
        check("priorities are 1..n0+1",
              [e["Priority"] for e in doc["Mods"]] == list(range(1, n0 + 2)))

        print("=== 6. the installed .dat, re-parsed from where it landed ===")
        raw_dat, how = P.load_dat(inst["dat"])
        check("inflated with the game's own path", how is not None, str(how))
        p = P.Parser(raw_dat)
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()):
            p.parse()
        check("parses to exact EOF", p.r.pos == len(raw_dat),
              "pos=%d len=%d" % (p.r.pos, len(raw_dat)))
        # Do NOT pin the byte count.  What this check is for is "the installer
        # copied the WHOLE stream, not a truncated or re-compressed one" -- and a
        # literal only says "the game had this many bytes on the day I wrote the
        # pin".  The shipped .dat moved on 2026-10-28 (93268152 -> 93272287) and
        # this line then failed on a perfectly good install, which is the same
        # defect as pinning the player's mod list.  Compare against the stream
        # this run actually started from.
        _base, _how = P.load_dat(tk.dat_path)
        check("same size as the base game's raw stream",
              len(raw_dat) == len(_base),
              "installed %d vs base %d" % (len(raw_dat), len(_base)))

        # The edit must actually be in the installed bytes.  Use the same
        # locator the product uses -- `P.Parser.stats` has no attack entries,
        # only locate()'s walk produces them.
        from aoe2mod.dat import locate as L
        civs, _, _, _ = L.locate(raw_dat, parser=p)
        archer_atk = []
        for cv in civs:
            for u in cv["units"]:
                if u["id"] == 4:
                    archer_atk.append([a["amount"]
                                       for a in u["type50"]["attacks"]
                                       if a["class"] == 3])
        check("every civ's installed Archer has base attack 5 (was 4, +1 shown)",
              all(a == [5] for a in archer_atk) and len(archer_atk) == 63,
              "%d civs, sample %s" % (len(archer_atk), archer_atk[:3]))

        print("=== 7. install() is idempotent-ish and reversible ===")
        try:
            tk.install(out, title="弓箭手攻击力+1", profile_root=prof)
            check("duplicate install refused", False, "no error")
        except FileExistsError:
            check("duplicate install refused", True)
        res = tk.uninstall("弓箭手攻击力+1", profile_root=prof)
        check("uninstalled: 1 entry gone", res["entries_removed"] == 1)
        check("uninstalled: folder gone", res["folder_removed"])
        doc2, _, _ = G.read_status_doc(prof)
        check("back to n0 entries", len(doc2["Mods"]) == n0,
              str(len(doc2["Mods"])))
        check("priorities back to 1..n0",
              [e["Priority"] for e in doc2["Mods"]] == list(range(1, n0 + 1)))

        print("=== 8. the real profile was never touched ===")
        check("real status file byte-identical",
              open(real_status, "rb").read() == before)
        _after = _snapshot(os.path.dirname(real_status))
        check("nothing added to the real profile",
              not (set(_after) - set(real_before)),
              str(sorted(set(_after) - set(real_before))))
        check("nothing removed from the real profile",
              not (set(real_before) - set(_after)),
              str(sorted(set(real_before) - set(_after))))
        check("nothing modified in the real profile",
              not [k for k in set(real_before) & set(_after)
                   if real_before[k] != _after[k]],
              str([k for k in set(real_before) & set(_after)
                   if real_before[k] != _after[k]]))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("FAILED %d CHECK(S):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("END-TO-END: BUILT, INSTALLED, AND READ BACK PASSES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
