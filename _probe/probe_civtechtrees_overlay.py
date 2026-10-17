# -*- coding: utf-8 -*-
"""Is the mode's CivTechTrees an OVERLAY (fall back to base) or its own COMPLETE set?

`probe_civtechtrees_override.py` found `modes/Pompeii/` ships 17 CivTechTrees
files while the base tree has 62, and that 3 of the 17 DIFFER from their base
counterparts.  That looks like overlay semantics -- but it is only overlay
semantics if the mode ALSO relies on base files it does not ship.  If the mode's
`.dat` simply has 17 civilizations, then its 17 files are its complete world and
the comparison proves nothing about substitution.

So: count the civilizations in the mode's own `.dat`.  The mode's `.dat` is a
different file from the base one, so this is a direct measurement.

  17 shipped files == mode civ count  -> the mode is self-contained; the layer is
                                         NOT shown to be an overlay.
  17 shipped files <  mode civ count  -> the mode leaves civs to the base tree,
                                         which IS fallback, and a mod's file at the
                                         same path would exercise the same lookup.
"""
import contextlib
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from aoe2mod.dat import parser as P                              # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODE_DAT = os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat",
                        "empires2_x2_p1.dat")
BASE_DAT = os.path.join(GAME, "resources", "_common", "dat",
                        "empires2_x2_p1.dat")
MODE_CT = os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat",
                       "CivTechTrees")


def civ_names(dat_path):
    data, _how = P.load_dat(dat_path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    # The parser records civilizations as it walks them.
    civs = p.stats.get("civs") or []
    names = []
    for c in civs:
        if isinstance(c, dict):
            names.append(c.get("name"))
        else:
            names.append(getattr(c, "name", None))
    return names


def norm(name):
    """Normalise a civ name for Set comparison, tolerating the spelling splits
    between the .dat's civ names and the file names.

    This is not cosmetic.  The mode's `.dat` says `Egyptian`, `Macedonian`,
    `Carthage`, `Lac Viet`, `Hittite`, `Palmyra` while its files are
    `EGYPTIANS.json`, `MACEDONIANS.json`, `CARTHAGIANS.json`, `LACVIET.json`,
    `HITTITES.json`, `PALMYRANS.json`.  Comparing raw names first reported 15
    "civs with no file" and then, after a naive de-pluralisation, still reported
    4 -- both false alarms that pushed the verdict toward "fallback exists".
    Matching by a shared prefix of the alphanumeric form handles every observed
    pair without an ever-growing suffix list.
    """
    s = "".join(ch for ch in str(name or "").upper() if ch.isalnum())
    # Trim to a common stem: 8 characters is enough to separate every civ pair in
    # this data (CARTHAG.., HITTIT.., PALMYR.., EGYPTIA.., MACEDON..) while
    # collapsing plural/singular forms.
    return s[:8]


def matches(a, b):
    """True when two normalised names denote the same civ."""
    na, nb = norm(a), norm(b)
    return bool(na) and bool(nb) and (na.startswith(nb) or nb.startswith(na))


def main():
    print("mode .dat exists: %s" % os.path.exists(MODE_DAT))
    print("base .dat exists: %s" % os.path.exists(BASE_DAT))
    shipped = sorted(f[:-5] for f in os.listdir(MODE_CT)
                     if f.lower().endswith(".json"))
    print("mode CivTechTrees files: %d" % len(shipped))
    print()

    try:
        names = civ_names(MODE_DAT)
    except Exception as exc:                                     # noqa: BLE001
        print("could not parse the mode .dat: %r" % (exc,))
        print("  -> report the file counts only; do NOT infer overlay semantics.")
        return 1
    clean = [n for n in names if n]
    print("civilizations in the MODE .dat: %d" % len(clean))
    print("  %s" % clean)
    print()

    # Match by prefix rather than by set equality: the two sources spell names
    # differently (dat `Egyptian` vs file `EGYPTIANS.json`).
    unexplained = [n for n in clean
                   if not any(matches(n, s) for s in shipped)]
    extra = [s for s in shipped
             if not any(matches(n, s) for n in clean)]
    print("mode civs with NO shipped CivTechTrees file: %d %s"
          % (len(unexplained), unexplained))
    print("shipped files for civs the mode does not have: %d %s"
          % (len(extra), extra))
    print()
    if not unexplained or all(str(n).upper() == "GAIA" for n in unexplained):
        print("VERDICT: the mode ships a file for EVERY PLAYABLE civ it has (the")
        print("only unmatched name is Gaia, which has no file in the BASE tree")
        print("either).  So the mode is SELF-CONTAINED, and this comparison does")
        print("NOT demonstrate fallback to the base tree.  It therefore does not")
        print("by itself prove a mod's file at that path would be consulted.")
        print()
        print("WHAT IS STILL TRUE: the layer is resolved relative to a ROOT (the")
        print("mode's own tree is read instead of the base one), which is the")
        print("property a mod override needs.  Whether the mod root participates")
        print("is not settled by static evidence on this machine.")
    else:
        print("VERDICT: the mode has %d civilizations with no file of their own, so"
              % len(unexplained))
        print("the layer IS resolved with fallback -- the base tree supplies the")
        print("rest.  A mod shipping the same relative path exercises the same")
        print("lookup.  Still: no direct in-game observation on this machine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
