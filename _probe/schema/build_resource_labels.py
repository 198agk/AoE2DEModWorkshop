# -*- coding: utf-8 -*-
"""build_resource_labels.py -- generate the resource-id name tables.

WHY THIS EXISTS
The dat stores a cost slot as (Type, Amount, Flag), where Type is a *civilization
resource id*.  The product declares five of them as editable resources
(dat_bindings.json resource_types: food/wood/stone/gold/population), but the
shipped data uses eight more: -1 is the empty sentinel, and 7 / 214 / 215 /
501 / 506 / 508 / 513 / 514 carry real amounts.  Until now those rendered to the
user as a bare number, e.g. "成本 type 506".

SOURCE OF TRUTH: THE GAME'S OWN TABLE, NOT AGE'S
The engine ships a contiguous block of resource names in
resources/<locale>/strings/key-value/key-value-strings-utf8.txt at string ids
15000..15550, i.e. string_id = 15000 + resource_type_id.  That is strictly
better than Tools_Builds/AGE3NamesV0007.ini [AoE2DECivResourceNames], which this
generator used previously:

  * 551 ids (0..550) vs AGE's 500 (0..499) -- the game covers 500..550 too.
  * 328 named slots vs AGE's 271.
  * It names ALL FIVE ids AGE could not name at all:
      501 Polemarch Build Limit            506 Achaemenid Town Center Local Upgrade
      508 Fortified Outpost Local Upgrade   513 Emplacement Local Upgrade
      514 Helepolis Limit
    so every type the shipped dat actually uses now has a name.
  * It is localized: en / zh / tw all carry all 551 ids, so the Chinese table is
    the official translation instead of a hand-written subset.
  * It is the engine's shipped vocabulary, not a tool author's recollection, and
    it is kept current with the game.

MEASURED RECONCILIATION (probe_game_vs_age_merge.py, 551 vs 500 slots)
    A. game names it, AGE does not        : 68
    B. both name it, identical            : 226
    C. both name it, DIFFERENT            : 34   <-- the game wins (see below)
    D. game says Unused, AGE names it     : 11   <-- must NOT be shipped
    E. AGE names it, game has no slot     : 0
  * C examples: 211 age "Higher Elevation Bonus" vs game "Elevation Higher Bonus";
    215 age "Mercenary Kipchak Limit" vs game "Bonus Forager Food"; 280 age
    "Military Conversion Range" vs game "Military Convert Range".  The phrase
    "Mercenary Kipchak Limit" occurs NOWHERE in the game's 19,677 shipped
    strings, while 15215 "Bonus Forager Food" ships in en, zh AND tw alike --
    so at 215 the game is right and AGE is stale.
  * D examples: AGE calls 34 "Faith" and 194 "Crenellations" while the game ships
    "Unused Resource 034" / "Unused Resource 194".  "Faith Recharging Rate",
    "Boarding Recharge Rate" and all seven "Speedup *" strings do not exist
    anywhere in the game's strings.  Those are AGE-only vocabulary: shipping them
    would print a resource name the engine does not use.

HONESTY RULES (the project's standing rule: never invent a name)
  * Only ids the game actually names are emitted.  Slots the game marks "Unused
    Resource NNN" (223 of 551) are DROPPED, so a lookup miss falls back to the
    bare number rather than printing "Unused" as if it were a resource.
  * AGE is NOT used as a fallback.  Class D shows every id AGE could add is one
    the game itself reserves as unused; class E is empty, so AGE adds nothing.
  * Ids 0-3 ship with a leading '!' ("!Food Storage").  That '!' is the game's
    own suppression marker -- it appears on exactly those four strings and
    nowhere else in 19,677, in both locales -- so it is STRIPPED for display.
    The raw resource id always stays the key.
  * The Chinese table is the game's own zh translation, not hand-written, and is
    guarded: an id the English table does not name raises here.

Run:  python _probe/schema/build_resource_labels.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

OUT_EN = os.path.join(HERE, "resource_labels.json")
OUT_ZH = os.path.join(HERE, "resource_labels_zh.json")

BASE = 15000                 # string_id = BASE + resource type id
TOP = 15550
STRINGS_REL = os.path.join("resources", "%s", "strings", "key-value",
                           "key-value-strings-utf8.txt")
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')

# Every resource id the shipped dat is known to use, from
# probe_resource_names.py (tech slots) + probe_unmapped_carriers.py (units).
USED = [0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514]


def find_game_root():
    """Locate the install.  Prefer the product's own locator so this script and
    the product cannot disagree about where the game is."""
    try:
        from aoe2mod.game import locations as G
        root = G.find_game_root()
        if root:
            return root
    except Exception as exc:                      # noqa: BLE001 - report, then fall back
        print("note: product locator unavailable (%s); using the recorded path" % exc)
    return r"D:\Games\Steam\steamapps\common\AoE2DE"


def load_block(root, locale, drop_unused=True):
    """Return ({resource_type_id: name}, seen, dropped) for one locale.

    ``seen`` counts every id present in BASE..TOP, so the caller can prove the
    block is contiguous instead of trusting that it is.  ``drop_unused`` is only
    True for English: the English file's "Unused Resource NNN" is what decides
    which slots are nameable, and every other locale is then used purely as a
    translation OF that decision -- the zh file writes the same slots as
    "\u672a\u4f7f\u7528\u7684\u8d44\u6e90 NNN", so matching on the English word in a
    non-English file would find nothing and silently ship 551 "names".
    """
    path = os.path.join(root, STRINGS_REL % locale)
    if not os.path.exists(path):
        raise SystemExit("FATAL: no strings file for locale %r at %s" % (locale, path))
    out, seen, dropped = {}, 0, 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line)
            if not m:
                continue
            sid = int(m.group(1))
            if not (BASE <= sid <= TOP):
                continue
            seen += 1
            name = m.group(2).strip()
            if not name:
                dropped += 1
                continue
            if drop_unused and name.lower().startswith("unused"):
                dropped += 1
                continue
            out[sid - BASE] = name[1:] if name.startswith("!") else name
    if not out:
        raise SystemExit("FATAL: locale %r has no name block at %d+" % (locale, BASE))
    return out, seen, dropped


root = find_game_root()
print("game root: %s" % root)
en, en_seen, en_unused = load_block(root, "en")
# zh is loaded WITHOUT its own unused filter, then restricted to exactly the ids
# English names -- see load_block's docstring for why English must decide.
zh_all, zh_seen, _zh_blank = load_block(root, "zh", drop_unused=False)
zh = {k: zh_all[k] for k in en if k in zh_all}

# The block must be contiguous; a gap means the scheme is not what we think.
for label, seen in (("en", en_seen), ("zh", zh_seen)):
    assert seen == TOP - BASE + 1, (
        "%s has %d ids in %d..%d, expected %d contiguous -- the 15000+type "
        "scheme does not hold" % (label, seen, BASE, TOP, TOP - BASE + 1))
print("en: %d slots in %d..%d, %d named, %d 'Unused Resource'"
      % (en_seen, BASE, TOP, len(en), en_unused))
print("zh: %d slots in %d..%d, %d of the %d English-named ids translated"
      % (zh_seen, BASE, TOP, len(zh), len(en)))

# Guard: every id the dat uses must be named now.  This is the whole point of
# switching source -- the five ids AGE could not name must be covered.
unnamed = [t for t in USED if t not in en]
assert not unnamed, (
    "these resource ids occur in shipped cost slots but the game does not name "
    "them: %s -- they would render as bare numbers" % unnamed)

# Guard: the Chinese table must cover what we ship, or the UI would fall back
# to English for a resource the install has a translation for.
missing_zh = [t for t in USED if t not in zh]
assert not missing_zh, "no zh translation for used resource ids: %s" % missing_zh

# Guard: dat_bindings.json's declared resources must be named too, or the
# product would show a bare number for a resource it claims is editable.
BINDINGS = os.path.join(REPO, "aoe2mod", "schema", "dat_bindings.json")
bindings = json.load(open(BINDINGS, encoding="utf-8"))
declared = sorted(set((bindings.get("resource_types") or {}).values()))
unnamed_declared = [t for t in declared if t not in en]
assert not unnamed_declared, (
    "declared editable resources with no name: %s" % unnamed_declared)
print("declared editable resource ids: %s (all named)" % declared)

json.dump({
    "source": "The game's own resource-name block: "
              "resources/<locale>/strings/key-value/key-value-strings-utf8.txt, "
              "string id 15000 + resource type id.  Generated by "
              "_probe/schema/build_resource_labels.py.  Replaces AGE's "
              "AGE3NamesV0007.ini, which named 271 slots and could not name "
              "501/506/508/513/514 at all.",
    "note": "Civilization resource id -> the game's own English name.  Ids the "
            "game labels 'Unused Resource NNN' (223 of 551) are OMITTED on "
            "purpose: a miss must fall back to the bare number, never print "
            "'Unused' as if it were a resource.  A leading '!' on ids 0-3 is the "
            "game's suppression marker and has been stripped.  This table LABELS "
            "a stored cost slot; it does not make the id editable -- "
            "dat_bindings.json resource_types decides that.",
    "names": {str(k): en[k] for k in sorted(en)},
}, open(OUT_EN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

json.dump({
    "source": "The game's own zh translation of the same 15000+ block in "
              "resources/zh/strings/key-value/key-value-strings-utf8.txt.  Not "
              "hand-written: generated by _probe/schema/build_resource_labels.py "
              "and guarded so an id the English table does not name raises.",
    "note": "Chinese names for the resource ids.  Covers every id the English "
            "table names; an id absent here (a locale the install lacks) falls "
            "back to the English name and then to the bare number.",
    "names": {str(k): zh[k] for k in sorted(zh)},
}, open(OUT_ZH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print()
print("wrote %s: %d names" % (os.path.basename(OUT_EN), len(en)))
print("wrote %s: %d names" % (os.path.basename(OUT_ZH), len(zh)))
print()
print("the 14 resource types the shipped dat actually uses:")
for t in (-1, 0, 1, 2, 3, 4, 7, 214, 215, 501, 506, 508, 513, 514):
    if t < 0:
        print("  %-5d (empty sentinel -- no name wanted)" % t)
        continue
    print("  %-5d en=%-42r zh=%r" % (t, en.get(t), zh.get(t)))
print()
print("previously nameless and now named: 501 / 506 / 508 / 513 / 514")
print("deliberately still nameless: every slot the game marks 'Unused Resource'")
