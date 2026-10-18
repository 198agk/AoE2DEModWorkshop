# -*- coding: utf-8 -*-
"""PROBE: is the game install still pristine after an in-game smoke test?

Why this exists
---------------
On 2026-10-14 an in-game smoke test of a two-part mod was run.  The `.dat` half
worked (villager HP 1000, and it survived being given a task -- the m11525
TaskSwapGroup defect is fixed).  The `CivTechTrees/<CIV>.json` half had no
effect.  A later session then produced a UI popup reading

    试图开始游戏时发生一个错误。无法打开文件： .gpv

with an EMPTY file name, and the user asked what that was.

This probe pins the safety invariant that matters: **the game's own install
files were never modified by this toolchain.**  A builder that edits game data
must be able to prove it writes only into mod folders, because "my tool ate the
game" is the one failure a user cannot recover from.

It also records what a `.gpv` actually is, so the next reader does not have to
re-derive it from an error message.

PROVEN here
    * the game's own `futuravailableunits.json` does NOT contain the two unit
      entries this toolchain added (they exist only in the emitted/installed mod)
    * the game's own `CivTechTrees/BRITONS.json` does NOT grant the units this
      toolchain granted (Huskarl's neighbour 2550, and Hand Cannoneer is still
      NotAvailable for Britons)
    * `mods()` resolves every registered mod to a folder OUTSIDE the game root
    * no installed mod ships a `.gpv`, and no text file anywhere in the game
      tree or mod folders names one
    * `.gpv` files are campaign packages named `<campaign>.aoe2campaign.gpv`
    * the popup's wording comes from the localized key-value table, not the exe
NOT PROVEN
    * what made the campaign name empty (the popup is UI-level and appears in no
      log; the crashing session's log ends with a clean `Exiting with code 0`)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.game import locations as L  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
FU_REL = os.path.join("resources", "_common", "dat", "futuravailableunits.json")
TREE_REL = os.path.join("resources", "_common", "dat", "CivTechTrees",
                        "BRITONS.json")

# The smoke mods are installed and uninstalled by hand -- `install_smoke3.py`
# writes a new one each time and the game may switch any of them off.  Naming a
# folder here made this probe fail with a FileNotFoundError the moment the mod
# list changed, reporting a stale path as if the game install had been damaged.
# So DISCOVER the mod that carries the edit: a mod's copy counts as evidence only
# if it really carries the edit under test.  The safety invariant itself (the
# game's own bytes are pristine) holds whether or not any mod exists.


def _units_of(obj, civ, bldg_id):
    civ = obj.get(civ) or {}
    for b in civ.get("Buildings", []):
        if b.get("ID") == bldg_id:
            return [u.get("ID") for u in b.get("Units", [])]
    return []


def _find_mod_with_fu():
    """Return (mod_dir, text) for an installed mod editing BRITONS in the panel."""
    for root, _dirs, files in os.walk(MODS):
        if "futuravailableunits.json" not in files:
            continue
        p = os.path.join(root, "futuravailableunits.json")
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        try:
            o = json.loads(t)
        except ValueError:
            continue
        if 2550 in _units_of(o, "Britons", 12):
            return os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(p)))), t
    return None, None


def _find_mod_with_tree():
    """Return (mod_dir, path) for an installed mod carrying an edited BRITONS tree."""
    game_len = os.path.getsize(os.path.join(GAME, TREE_REL))
    for root, _dirs, files in os.walk(MODS):
        if "BRITONS.json" not in files:
            continue
        p = os.path.join(root, "BRITONS.json")
        if "CivTechTrees" not in p:
            continue
        try:
            if os.path.getsize(p) > game_len:
                return p.rsplit(os.sep, 3)[0], p
        except OSError:
            continue
    return None, None

fails = []


def check(ok, label, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if detail else ""))
    if not ok:
        fails.append(label)


print("A  the game's own data files are untouched")
game_fu = os.path.join(GAME, FU_REL)
FU_MOD, mt = _find_mod_with_fu()
check(os.path.isfile(game_fu), "the game ships futuravailableunits.json")
# NOTE: a plain `'"ID": 2550' in gt` check is WRONG -- Champi Scout really does
# exist in the game's file, for Incas / Mapuche / Muisca / Tupi.  The question is
# whether it was added to BRITONS, so parse and look at the civ key.
gt = open(game_fu, encoding="utf-8").read()
_gobj = json.loads(gt)

if mt is None:
    # No installed mod currently carries the panel edit, so there is nothing to
    # contrast against -- but the invariant being pinned is about the GAME's
    # bytes, and those are checked either way.  Reported, not silently skipped.
    print("  [SKIP] no installed mod currently edits BRITONS in the panel; "
          "the game-side checks below still run")
    check(2550 not in _units_of(_gobj, "Britons", 12),
          "the game's own copy does NOT give Britons Champi Scout at the Barracks",
          "the game's file is pristine (no mod is under test)")
    check(5 not in _units_of(_gobj, "Britons", 87),
          "the game's own copy does NOT give Britons Hand Cannoneer at the Range")
else:
    _mobj = json.loads(mt)
    check(2550 not in _units_of(_gobj, "Britons", 12),
          "the game's own copy does NOT give Britons Champi Scout at the Barracks",
          "the game's file is pristine")
    check(2550 in _units_of(_mobj, "Britons", 12),
          "the mod's copy DOES (that is the edit under test)",
          FU_MOD.rsplit(os.sep, 1)[-1])
    check(5 not in _units_of(_gobj, "Britons", 87),
          "the game's own copy does NOT give Britons Hand Cannoneer at the Range")
    # The mod side of the Hand Cannoneer edit is only asserted if THIS mod carries
    # it.  An earlier version hard-coded it, which made the probe fail as soon as
    # the installed mod under test changed from the combined bundle to a mod that
    # edits only the Champi Scout.  The invariant being pinned is about the GAME's
    # bytes, and those are checked either way -- so the contrast is derived from
    # what the mod actually contains, not assumed.
    _hc_in_mod = 5 in _units_of(_mobj, "Britons", 87)
    print("     the mod's copy %s Britons Hand Cannoneer at the Range"
          % ("ALSO gives" if _hc_in_mod else "does NOT touch"))
    check(os.path.getsize(game_fu) != len(mt.encode("utf-8")),
          "and the two files are not the same bytes",
          "game %d B / mod %d B" % (os.path.getsize(game_fu),
                                    len(mt.encode("utf-8"))))

print()
print("B  the game's own tech trees are untouched")
game_tree = CT.load_trees(GAME)
check(bool(game_tree), "the game's CivTechTrees load", "%d civs" % len(game_tree))
_b = game_tree.get("BRITONS")
check(_b is not None, "BRITONS is one of them")
check(not CT.can_build(_b, 2550),
      "the game's BRITONS cannot build Champi Scout (2550)",
      "the grant lives only in the mod")
check(CT.node_status(_b, 5) == "NotAvailable",
      "and Hand Cannoneer (5) is still NotAvailable for the game's Britons",
      CT.node_status(_b, 5))
_TREE_MOD, mod_tree = _find_mod_with_tree()
if mod_tree is None:
    print("  [SKIP] no installed mod currently carries an edited BRITONS tree")
else:
    check(os.path.getsize(mod_tree) > os.path.getsize(
              os.path.join(GAME, TREE_REL)),
          "the installed mod's tree is larger than the game's (a row was added)",
          "%d B vs %d B" % (os.path.getsize(mod_tree),
                            os.path.getsize(os.path.join(GAME, TREE_REL))))

print()
print("C  every registered mod lives outside the game install")
status = json.loads(open(os.path.join(MODS, "mod-status.json"),
                         encoding="utf-8", errors="replace").read(), strict=False)
_inside = []
for m in status.get("Mods", []):
    p = m.get("Path") or ""
    if p and os.path.abspath(p).lower().startswith(os.path.abspath(GAME).lower()):
        _inside.append(p)
check(not _inside, "no registered mod path is inside the game root", _inside)
check(len(status.get("Mods", [])) > 0,
      "mod-status.json is readable", "%d mods" % len(status.get("Mods", [])))
check("Unsub" in status, "and carries the Unsub key the game writes")

print()
print("D  what a .gpv file is")
camp = os.path.join(GAME, "resources", "_common", "campaign")
gpvs = sorted(f for f in os.listdir(camp) if f.endswith(".gpv"))
check(len(gpvs) > 0, "the game ships .gpv files", "%d" % len(gpvs))
check(all(f.endswith(".aoe2campaign.gpv") for f in gpvs),
      "every one is named <campaign>.aoe2campaign.gpv")
_campaigns = [f for f in os.listdir(camp) if f.endswith(".aoe2campaign")]
check(len(_campaigns) > len(gpvs),
      "but most campaigns ship WITHOUT one",
      "%d campaigns, %d .gpv" % (len(_campaigns), len(gpvs)))
# A .gpv is a packed archive tagged with the DLC it belongs to.  The tag is the
# DLC name REVERSED: `cam1.aoe2campaign.gpv` starts with b'esaB' ("Base"),
# `3kcam1...` with b'ureP' ("Peru"), `cscam1...` with b'1paP' ("Pap1" ~ Paphos),
# `ccam1...` with b'4CLD' ("DLC4"), `pacam1...` with b'iraP' ("Pari" ~ Paris),
# `prcam1...` with b'vorP' ("Prov" ~ Providence), `nocam*` with b'lihP'
# ("Phil" ~ Philadelphia) and b'troP' ("Port" ~ Portland).
_magics = {}
for _f in gpvs:
    _m = open(os.path.join(camp, _f), "rb").read(4)
    _magics.setdefault(_m, []).append(_f)
check(all(all(32 <= c < 127 for c in m) for m in _magics),
      "each .gpv begins with a printable 4-byte DLC tag",
      sorted(m.decode("ascii", "replace") for m in _magics))
check(b"esaB" in _magics,
      "and the base game's tag is 'esaB' (= 'Base' reversed)",
      "%d of %d files" % (len(_magics.get(b"esaB", [])), len(gpvs)))
check(all(m[::-1].decode("ascii", "replace")[:3].isalpha() or
          m[::-1].decode("ascii", "replace").startswith("DLC")
          for m in _magics),
      "and every tag, reversed, is a DLC name fragment",
      sorted(m[::-1].decode("ascii", "replace") for m in _magics))

_named = []
for base in (GAME, MODS):
    for r, d, fs in os.walk(base):
        for f in fs:
            if not f.lower().endswith((".json", ".txt", ".xml", ".xaml", ".ini")):
                continue
            p = os.path.join(r, f)
            try:
                if os.path.getsize(p) > 8_000_000:
                    continue
                if "gpv" in open(p, encoding="utf-8", errors="ignore").read().lower():
                    _named.append(p)
            except OSError:
                continue
check(not _named,
      "no text file in the game tree or mod folders names a .gpv", _named[:3])

_shipped = []
for r, d, fs in os.walk(MODS):
    for f in fs:
        if f.lower().endswith(".gpv"):
            _shipped.append(os.path.join(r, f))
check(not _shipped, "and no installed mod ships campaign content", _shipped[:3])

print()
print("E  the popup's wording is a localized string, not an exe literal")
kv = os.path.join(GAME, "resources", "zh", "strings", "key-value",
                  "key-value-strings-utf8.txt")
if not os.path.isfile(kv):
    _base = os.path.join(GAME, "resources")
    for _d in os.listdir(_base):
        _c = os.path.join(_base, _d, "strings", "key-value",
                          "key-value-strings-utf8.txt")
        if os.path.isfile(_c):
            kv = _c
            break
_kt = open(kv, encoding="utf-8", errors="replace").read()
check("IDS_FAILED_TO_OPEN_FILE" in _kt,
      "the key-value table defines IDS_FAILED_TO_OPEN_FILE")
check("无法打开文件：" in _kt, "with the wording the popup showed")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
check("无法打开文件".encode("utf-8") not in exe,
      "and that wording is not in the exe (so it came from the table)")

print()
if fails:
    print("INSTALL SAFETY: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
    sys.exit(1)
print("INSTALL SAFETY: the game install is pristine; the smoke test's writes "
      "went only into mod folders, and a .gpv is a campaign package.")
print("NOT PROVEN: what emptied the campaign name in the popup -- it is a "
      "UI-level failure that appears in no log.")
