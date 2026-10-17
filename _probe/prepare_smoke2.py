"""Set the profile up for a CLEAN single-variable in-game test of the build panel.

The earlier attempt measured nothing: the game rewrote ``mod-status.json`` and
switched the mod OFF, so "the panel did not change" may only have meant "the
mod was not loaded".  This script makes exactly one mod the variable:

  * ``aoe2mod Smoke2 BuildPanel``        -> ON   (only file: futuravailableunits.json)
  * ``aoe2mod Smoke HP+Units``           -> OFF  (it also carries a .dat, which
  * ``Smoke Test Villager HP``           -> OFF   would be a second variable)

It backs the status file up first, then re-reads it from disk to report what is
actually on disk rather than what it just wrote -- the whole point of the
exercise is that those two can differ.

Run:  python _probe/prepare_smoke2.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402

TARGET = "aoe2mod Smoke2 BuildPanel"
OFF = ["aoe2mod Smoke HP+Units", "Smoke Test Villager HP"]


def main():
    tk = A.open_toolkit()
    from aoe2mod.game import locations as G
    prof = G.find_profile_root()
    # The status file is <profile>/<account>/mods/mod-status.json -- the account
    # folder is the SteamID64 one, NOT the profile root.  Getting this wrong
    # fails before anything is written, which is the right way to fail.
    acc = G.pick_account(prof)
    status = G.status_path(acc)

    before = tk.mods()
    print("profile     :", prof)
    print("account     :", acc)
    print("status file :", status)
    print()
    print("BEFORE")
    for m in before:
        print("  prio %-2s enabled %-5s %s" % (m["priority"], m["enabled"], m["name"]))

    backup = status + ".before-smoke2"
    if not os.path.exists(backup):
        shutil.copy2(status, backup)
        print("\nbacked up ->", backup)
    else:
        print("\nbackup already exists ->", backup)

    for m in before:
        if m["name"] == TARGET:
            tk.set_mod_enabled(TARGET, True, kind=m["kind"])
            print("enabled  :", TARGET, "(was %s)" % m["enabled"])
        elif m["name"] in OFF:
            tk.set_mod_enabled(m["name"], False, kind=m["kind"])
            print("disabled :", m["name"], "(was %s)" % m["enabled"])

    # Re-read from disk.  Never report the value we just wrote as if it were
    # the truth -- the game rewrites this file.
    after = tk.mods()
    print()
    print("AFTER (re-read from disk)")
    live = []
    for m in after:
        flag = "ON " if m["enabled"] else "off"
        print("  prio %-2s %s %s" % (m["priority"], flag, m["name"]))
        if m["enabled"]:
            live.append(m["name"])

    dat_mods = [m["name"] for m in after if m["enabled"] and m["kind"] != "subscribed"]
    print()
    print("enabled mods:", live)
    tgt = [m for m in after if m["name"] == TARGET]
    ok = bool(tgt) and tgt[0]["enabled"]
    print()
    if ok:
        print("READY: '%s' is enabled and is the only one of my mods that is." % TARGET)
        print()
        print("WHERE TO LOOK -- this was gotten wrong once.  The mod gives")
        print("BRITONS two units it cannot normally build:")
        print("  * Champi Scout (2550) at the BARRACKS (12)")
        print("  * Hand Cannoneer (5) at the ARCHERY RANGE (87)")
        print()
        print("`futuravailableunits.json` sits in the exe's string pool next to")
        print("BOTH CommandPanel and TechTreePreviewPanel, and it covers the")
        print("CASTLE as well -- which is not in the villager build menu.  So it")
        print("is probably the TECH TREE PREVIEW, not the build menu.  Check the")
        print("tech tree screen FIRST (Britons -> Barracks / Archery Range) and")
        print("the in-game build menu SECOND.  Whichever one shows the unit tells")
        print("us which file that screen reads.")
        print()
        print("CHEAPER ALTERNATIVE, needs no mod at all: the two shipped files")
        print("already disagree on 18 real pairs (see probe_shipped_disagreement)")
        print("-- e.g. Jurchens' Archery Range lists Long/Two-Handed/Champion")
        print("Swordsman even though the tree calls them NotAvailable.  Just")
        print("start a normal game as JURCHENS and look at the Barracks.  No mod")
        print("installed means nothing else can explain the result.")
    else:
        print("NOT READY: the mod is not enabled on disk; nothing to test.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
