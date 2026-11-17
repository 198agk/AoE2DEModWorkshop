# -*- coding: utf-8 -*-
"""build_attribute_labels.py -- generate the effect-attribute name tables.

WHY THIS EXISTS
An effect command of the attribute-modifier kind stores its attribute in slot C.
``effect_attributes.json`` (AGE's own table, 89 ids over 0..115) names most of
them, and a command whose attribute has no name is deliberately REFUSED rather
than guessed -- printing "attribute 158" is honest, inventing a name is not.
That refusal was costing 160 shipped commands: probe_refusal_reasons.py split
every refusal into "type not in the operation table" (a missing feature, 1,585)
and "attribute id has no name" (a missing LABEL, 160), and only the first was
addressed.  Measured, the 11 nameless ids the shipped data actually uses are

    81   Special Ability           118  Damage Reflection
    119  Friendly Fire Damage      125  Charge Projectile Unit
    126  Available Unit Flag       127  Disabled Unit Flag
    130  Garrison Firepower        145  Trailing Unit
    146  Trail Mode                147  Trail Density
    158  Train Locations Entry Mod

SOURCE OF TRUTH: THE GAME'S OWN TABLE, NOT AGE'S
The engine ships a contiguous block of attribute names in
resources/<locale>/strings/key-value/key-value-strings-utf8.txt at string ids
12200..12461, i.e. string_id = 12200 + attribute_id.  Evidence it is that table
and not a coincidence (probe_attr_name_blocks.py enumerates every base 0..59999
against four anchors -- 12200 is the ONLY one that matches):

    12200 Hit Points      12201 Line of Sight      12202 Garrison Capacity
    12203 Unit Size X     12204 Unit Size Y        12205 Movement Speed
    12206 Rotation Speed

Those four anchors are attribute ids 0/1/2/5 by AGE's own numbering, and the
block names 96 of the 100 ids this project cares about -- including all 11 AGE
cannot name.  en / zh / tw each cover all 242 named slots, so the Chinese table
is the official translation instead of a hand-written subset.

HONESTY RULES (the project's standing rule: never invent a name)
  * Only ids the game actually names are emitted.
  * Slots the game fills with "Unused ..." (17 of them: 200, 206, 207, 209, 210,
    212, 231, 233, 240, 242..249) and the literal "<!--RESERVED-->" marker at 261
    are DROPPED, so a lookup miss falls back to the bare number rather than
    printing a placeholder as if it were an attribute.
  * This table SUPPLEMENTS AGE's; it does not replace it.  66 of AGE's names
    differ from the game's wording, and 54 of those appear on a live shipped
    command, i.e. 5,194 of 6,420 attribute-modifier commands would change label.
    Most of the difference is AGE annotating its own tool UI ("Movement Speed
    (types 20-80)").  That is a real, measured, deliberately DEFERRED decision --
    this file only fills the gaps, so the same edit cannot silently reword 5,194
    commands while claiming to fix 160.
  * Guarded: every id in ``REQUIRED`` must be named here or the generator raises.
    Those are the ids the shipped data uses and AGE cannot name; if this table
    ever stops covering them the refusals come back, and this is where to say so.

Run:  python _probe/schema/build_attribute_labels.py
"""
import io
import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

# String-id base of the engine's attribute-name block, and the extent measured
# this build.  Both are DATA: a game update that moves the block should fail the
# guards below rather than silently emit a shifted table.
BASE = 12200
TOP = 12461
STRINGS_REL = os.path.join("resources", "%s", "strings", "key-value",
                           "key-value-strings-utf8.txt")
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')

# The ids the shipped data uses and AGE's table cannot name.  If one of these
# stops resolving, the generator must fail: the whole point is that these 160
# commands become editable.
REQUIRED = [81, 118, 119, 125, 126, 127, 130, 145, 146, 147, 158]

# Four ids whose meaning nobody disputes, used to prove the base.  If a game
# update moves the block, these stop matching and the generator refuses to
# emit a silently shifted table -- which is the only failure mode that would
# not show up as a MISSING name.
ANCHORS = {0: "Hit Points", 1: "Line of Sight", 2: "Garrison Capacity",
           5: "Movement Speed"}

OUT_EN = os.path.join(HERE, "attribute_labels.json")
OUT_ZH = os.path.join(HERE, "attribute_labels_zh.json")


def find_root():
    """Prefer the product's own discovery; fall back to the recorded path."""
    try:
        from aoe2mod.game import locations as G
        root = G.find_game_root()
        if root:
            return root
    except Exception:
        pass
    return GP.GAME


def load_block(root, locale, drop_unused=True):
    """(names, seen, dropped) for one locale's attribute block.

    ``drop_unused`` is True only for English.  The English block decides which
    slots are nameable; the other locales are used as TRANSLATIONS of that
    decision.  Filtering zh by the English word "Unused" would match nothing
    (zh ships a translated placeholder) and would therefore ship 242 "names",
    the exact silent failure the resource table's generator documents.
    """
    path = os.path.join(root, STRINGS_REL % locale)
    if not os.path.isfile(path):
        return None, 0, 0
    out, seen, dropped = {}, 0, 0
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            m = LINE.match(ln)
            if not m:
                continue
            sid = int(m.group(1))
            if not (BASE <= sid <= TOP):
                continue
            seen += 1
            val = m.group(2).strip()
            if not val:
                continue
            if drop_unused and (val.lower().startswith("unused")
                                or "RESERVED" in val.upper()):
                dropped += 1
                continue
            out[sid - BASE] = val
    return out, seen, dropped


def main():
    root = find_root()
    print("game root: %s" % root)
    en, en_seen, dropped = load_block(root, "en", drop_unused=True)
    if not en:
        raise SystemExit("FATAL: no attribute strings at %d..%d under %s"
                         % (BASE, TOP, root))
    zh_all, zh_seen, _ = load_block(root, "zh", drop_unused=False)
    if zh_all is None:
        raise SystemExit("FATAL: the game has no zh string file")
    zh = {k: zh_all[k] for k in en if k in zh_all}

    # --- guards -----------------------------------------------------------
    # Unlike the resource block (551 of 551 contiguous), this one has genuine
    # holes: 242 named slots over 262 positions.  A slot COUNT is therefore not
    # a valid check here -- and it is the weaker check anyway, because a shifted
    # base would still count 242.  What proves the base is ANCHORS: ids whose
    # meaning is not in dispute must land on the names the game uses for them.
    span = TOP - BASE + 1
    for off, want in ANCHORS.items():
        got = en.get(off)
        if not got or want.lower() not in got.lower():
            raise SystemExit("FATAL: base %d does not hold -- %d should read "
                             "~%r, got %r" % (BASE, off, want, got))
    if not zh:
        raise SystemExit("FATAL: zh translates none of the %d English-named "
                         "attribute ids" % len(en))
    missing = [i for i in REQUIRED if i not in en]
    if missing:
        raise SystemExit("FATAL: the game does not name %s -- these are the ids "
                         "whose 160 commands this table exists to unlock"
                         % (missing,))
    untranslated = [i for i in REQUIRED if i not in zh]
    if untranslated:
        raise SystemExit("FATAL: zh does not translate %s" % (untranslated,))

    # --- report the section the resource table got wrong ------------------
    for i in REQUIRED:
        print("  %-4d en=%-28r zh=%r" % (i, en[i], zh[i]))
    print()
    print("en: %d slots in %d..%d, %d named, %d 'Unused'/'RESERVED' dropped"
          % (span, BASE, TOP, len(en), dropped))
    print("zh: %d of the %d English-named ids translated"
          % (len(zh), len(en)))

    with io.open(OUT_EN, "w", newline="\n") as fh:
        json.dump({
            "source": "the game's own attribute-name block, "
                      "string_id = %d + attribute id" % BASE,
            "note": "Supplements AGE's effect_attributes.json; it does not "
                    "replace it.  Emitted only where the game names the slot, so "
                    "a miss falls back to the bare number.  'Unused' and "
                    "'<!--RESERVED-->' slots are deliberately absent.",
            "base": BASE,
            "names": {str(k): en[k] for k in sorted(en)},
        }, fh, ensure_ascii=False, indent=1)

    with io.open(OUT_ZH, "w", newline="\n") as fh:
        json.dump({
            "source": "the game's own zh locale for the same block",
            "note": "A translation of the English table's decision.  An id "
                    "absent here falls back to the English name and then to the "
                    "bare number.",
            "base": BASE,
            "names": {str(k): zh[k] for k in sorted(zh)},
        }, fh, ensure_ascii=False, indent=1)

    print()
    print("wrote %s: %d names" % (os.path.basename(OUT_EN), len(en)))
    print("wrote %s: %d names" % (os.path.basename(OUT_ZH), len(zh)))


if __name__ == "__main__":
    main()
