# -*- coding: utf-8 -*-
"""One mod, one row -- and the rebuild takes the old copy's place.

Two promises are checked here, both measured on 2026-11-10 against the live
profile (28 entries, 19 carrying a .dat):

1. A mod that exists as `subscribed//X` AND `local//X` gets ONE row, and the
   row is the copy a rebuild would write over.  Two rows made "全部一键适配"
   rebuild the same mod forever, because the subscribed copy never stops
   looking out of date.

2. The rebuild is installed as `local` at the 0-BASED index the player's
   1-based priority names, and the subscribed copy it replaced is switched
   off.  Before this, the Number was passed through as an index, so the new
   copy landed one slot BELOW the stale one, and the stale one stayed on.

Runs on a throwaway profile built to mimic the real one; the live profile is
only ever read.
"""
import json
import _gamepaths as GP
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aoe2mod import api as A                       # noqa: E402
from aoe2mod.game import locations as G            # noqa: E402
from aoe2mod.mod import archives as AR             # noqa: E402

REAL_PROFILE = GP.PROFILE
ACC = GP.STEAMID
FAILS = []


def check(label, cond, detail=""):
    print("  [%s] %s%s" % ("OK " if cond else "FAIL", label,
                           ("  -- " + detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def write_status(acc_root, entries):
    doc = {"Mods": []}
    for i, (kind, name, enabled) in enumerate(entries):
        doc["Mods"].append({"Enabled": bool(enabled), "Priority": i + 1,
                            "Path": "%s//%s" % (kind, name)})
    p = os.path.join(acc_root, ACC, "mods", "mod-status.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    return p


def make_mod(root, kind, name):
    d = os.path.join(root, ACC, "mods", kind, name)
    os.makedirs(os.path.join(d, "resources", "_common", "dat"))
    with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as fh:
        json.dump({"Author": "probe", "CacheStatus": 0, "Description": "d",
                   "Title": name}, fh, ensure_ascii=False)
    with open(os.path.join(d, "resources", "_common", "dat",
                           "empires2_x2_p1.dat"), "wb") as fh:
        fh.write(b"\x78\x9cFAKE")
    return d


def make_build(root, title):
    """A rebuilt folder, shaped like what `upgrade()` leaves behind."""
    d = os.path.join(root, "_out", title)
    os.makedirs(os.path.join(d, "resources", "_common", "dat"))
    with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as fh:
        json.dump({"Author": "probe", "CacheStatus": 0, "Description": "d",
                   "Title": title}, fh, ensure_ascii=False)
    with open(os.path.join(d, "resources", "_common", "dat",
                           "empires2_x2_p1.dat"), "wb") as fh:
        fh.write(b"\x78\x9cNEW")
    return d


def status_of(root):
    """`[(kind, name, enabled, priority)]` in the order the engine reads them."""
    doc = G.read_status_doc(root)[0]
    out = []
    for e in doc.get("Mods", []):
        kind, _, name = (e.get("Path") or "").partition("//")
        out.append((kind, name, bool(e.get("Enabled")), e.get("Priority")))
    return out


def main():
    # Records go to a throwaway file: the real `builds.json` is the player's.
    os.environ["AOE2MOD_STATE_DIR"] = tempfile.mkdtemp(prefix="upg_state_")
    root = tempfile.mkdtemp(prefix="upg_hand_")
    try:
        os.makedirs(os.path.join(root, ACC, "mods"))
        make_mod(root, "subscribed", "aaa_first")
        make_mod(root, "subscribed", "MINE")
        make_mod(root, "local", "MINE")
        make_mod(root, "subscribed", "ccc_after")
        write_status(root, [("subscribed", "aaa_first", True),
                            ("subscribed", "MINE", True),
                            ("local", "MINE", False),
                            ("subscribed", "ccc_after", True)])
        print("-- one row per mod, and it is the local copy")
        rows = A.Toolkit._upgrade_targets(None, root, limit=0)
        names = [r["name"] for r in rows]
        check("three mods on disk give three rows, not four",
              len(rows) == 3, str(names))
        check("the duplicated name appears once", names.count("MINE") == 1, str(names))
        mine = [r for r in rows if r["name"] == "MINE"][0]
        check("the surviving row is the local copy", mine["kind"] == "local",
              mine["kind"])
        check("the list still keeps the player's own order",
              names == ["aaa_first", "MINE", "ccc_after"], str(names))

        print("-- an enabled subscriber beats a disabled local of the same name")
        write_status(root, [("local", "aaa_first", False),
                            ("subscribed", "aaa_first", True),
                            ("subscribed", "MINE", True),
                            ("subscribed", "ccc_after", True)])
        rows2 = A.Toolkit._upgrade_targets(None, root, limit=0)
        first = [r for r in rows2 if r["name"] == "aaa_first"][0]
        check("a disabled local does not win over a live subscribed copy",
              first["kind"] == "subscribed" and first["enabled"], str(first))

        print("-- limit still cuts the list")
        rows3 = A.Toolkit._upgrade_targets(None, root, limit=2)
        check("limit=2 gives two rows", len(rows3) == 2, str(len(rows3)))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # -- the rebuild takes the old copy's place -----------------------------
    print("-- a rebuild from subscribed/ lands in local/, one slot up, old copy off")
    root2 = tempfile.mkdtemp(prefix="upg_hand2_")
    try:
        os.makedirs(os.path.join(root2, ACC, "mods"))
        make_mod(root2, "subscribed", "aaa_first")
        make_mod(root2, "subscribed", "MINE")
        make_mod(root2, "subscribed", "ccc_after")
        write_status(root2, [("subscribed", "aaa_first", True),
                             ("subscribed", "MINE", True),
                             ("subscribed", "ccc_after", True)])
        rows = A.Toolkit._upgrade_targets(None, root2, limit=0)
        mine = [r for r in rows if r["name"] == "MINE"][0]
        build = make_build(root2, "MINE")
        notes = []
        tk = A.Toolkit.__new__(A.Toolkit)
        man = A.Toolkit._upgrade_install(tk, build, mine, "MINE 标题",
                                         root2, notes)
        after = status_of(root2)
        print("     ", after)
        check("the rebuild is registered as local",
              (("local", "MINE") in [(k, n) for k, n, _e, _p in after]),
              str(after))
        old = [e for e in after if e[0] == "subscribed" and e[1] == "MINE"]
        check("the subscribed copy is still listed (nothing was deleted)",
              len(old) == 1, str(after))
        check("the subscribed copy is switched off",
              old and old[0][2] is False, str(old))
        new = [e for e in after if e[0] == "local" and e[1] == "MINE"]
        check("the rebuild sits exactly where the old copy sat",
              new and new[0][3] == 2, str(new))
        check("it is on, so the game actually reads it",
              new and new[0][2] is True, str(new))
        check("nothing else moved",
              [(k, n) for k, n, _e, _p in after]
              == [("subscribed", "aaa_first"), ("local", "MINE"),
                  ("subscribed", "MINE"), ("subscribed", "ccc_after")],
              str([(k, n) for k, n, _e, _p in after]))
        check("the manifest names the copy it replaced",
              (man.get("previous") or {}).get("kind") == "subscribed"
              and (man.get("previous") or {}).get("disabled") is True,
              str(man.get("previous")))
        check("the report says so out loud, in one sentence",
              len(notes) == 1 and "订阅目录" in notes[0], str(notes))

        print("-- a rebuild of a local mod touches no other entry")
        rows2 = A.Toolkit._upgrade_targets(None, root2, limit=0)
        loc = [r for r in rows2 if r["name"] == "MINE" and r["kind"] == "local"][0]
        build2 = make_build(root2, "MINE2")
        notes2 = []
        man2 = A.Toolkit._upgrade_install(tk, build2, loc, "MINE 标题",
                                          root2, notes2)
        check("no previous block for a local rebuild",
              man2.get("previous") is None, str(man2.get("previous")))
        check("and no extra sentence", notes2 == [], str(notes2))
        still = [e for e in status_of(root2) if e[0] == "subscribed" and e[1] == "MINE"]
        check("the subscribed copy is left exactly as it was",
              still and still[0][2] is False, str(still))
    finally:
        shutil.rmtree(root2, ignore_errors=True)

    # -- the game's own write must not leave the rebuild switched off --------
    #
    # Measured 2026-11-21 on the real profile: `_upgrade_install` asked for
    # `enabled=True`, and the status file ended up with `"Enabled": false` for
    # the rebuilt copy.  A running game rescans `mods/local`, registers what it
    # finds and writes the entry itself -- off.  Whichever write lands second
    # wins, and the player then reports exactly what happened: "the update did
    # nothing", with `data = 0` in every session log.
    #
    # The fake game here is the only way to exercise the window: patch install so
    # that, right after the folder lands, the entry is written off the way the
    # engine writes it.
    print("-- the rebuild is on even when the game writes its own entry off")
    root3 = tempfile.mkdtemp(prefix="upg_hand3_")
    real_install = A.Toolkit.install

    def install_then_engine_writes(root, mod_dir, name=None, title=None,
                                   kind="local", enabled=True, position=0,
                                   profile_root=None, account=None,
                                   overwrite=False):
        man = real_install(root, mod_dir, name=name, title=title, kind=kind,
                           enabled=enabled, position=position,
                           profile_root=profile_root, account=account,
                           overwrite=overwrite)
        G.set_mod_enabled(profile_root, man["name"], False, kind="local")
        return man

    try:
        os.makedirs(os.path.join(root3, ACC, "mods"))
        make_mod(root3, "subscribed", "MINE")
        write_status(root3, [("subscribed", "MINE", True)])
        rows = A.Toolkit._upgrade_targets(None, root3, limit=0)
        mine = [r for r in rows if r["name"] == "MINE"][0]
        build3 = make_build(root3, "MINE")
        notes3 = []
        A.Toolkit.install = install_then_engine_writes
        try:
            man3 = A.Toolkit._upgrade_install(tk, build3, mine, "MINE 标题",
                                              root3, notes3)
        finally:
            A.Toolkit.install = real_install
        after3 = status_of(root3)
        new3 = [e for e in after3 if e[0] == "local" and e[1] == "MINE"]
        check("新装的那份最后是开着的",
              new3 and new3[0][2] is True, str(after3))
        check("manifest 如实记了「重新打开过」",
              (man3.get("reopened") or {}).get("enabled") is True,
              str(man3.get("reopened")))
        check("报告里有一句话说明这件事",
              any("没启用" in n for n in notes3), str(notes3))
    finally:
        shutil.rmtree(root3, ignore_errors=True)

    print()
    if FAILS:
        print("HANDOVER: %d CHECK(S) FAILED" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("HANDOVER: ONE ROW PER MOD, AND THE NEW COPY TAKES THE OLD ONE'S SLOT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
