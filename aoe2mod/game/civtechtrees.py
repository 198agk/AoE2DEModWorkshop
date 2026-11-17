# -*- coding: utf-8 -*-
"""Can a given civilization obtain a given unit?  Read the layer that decides it.

WHY THIS MODULE EXISTS INSTEAD OF A `.dat` FIELD
================================================

The unit record has two u8 fields that genieutils calls `Enabled`/`Disabled`
(``parser.read_unit()``, right after OldPortraitPict), and it is very tempting to
treat them as the availability switch.  Measured, they are not:

  * across 2,693 unit ids only **7** carry a different value in different civs;
  * between British and Goths, **0** of 2,164 shared ids differ in those bytes,
    while the game's own data gives British 24 ids Goths cannot have and Goths 14
    British cannot.  0 versus 24 settles it: no per-record byte can express this.
  * the `.dat` TechTree section is read ONCE (``parser.read_tech_tree``) -- a
    single global table, structurally unable to differ per civ.

The mechanism is this JSON layer:

    <game_root>/resources/_common/dat/CivTechTrees/<CIV>.json

Evidence that the engine READS it rather than merely shipping it:

  * the executable contains the path template ``CivTechTrees/%s.json``
    (offset 0x3261A18), **exactly once**, and it is the LAST string run of its
    own generated schema cluster: the 17 row-field names that are their own runs
    sit immediately before it in alphabetical order, then the file's three
    top-level keys in order (``civ_id`` -> ``civ_techs_buildings`` ->
    ``civ_techs_units``), and the ``Draw Node Type`` / ``Node Status`` value
    clusters follow it in the order the schema declares them
    (``_probe/test_tree_form.py``);
  * it lives beside the other `.dat`-adjacent JSON inputs, and the game's own
    ``modes/Pompeii`` ships an aggregate ``civTechTrees.json`` covering its 17
    Rome civs -- a per-mode data layer, semantically identical to the per-civ
    files (2,142 shared rows, 0 value differences).

⚠ HONESTY BOUNDARY ON THE WRITE SIDE -- DO NOT UPGRADE THIS WITHOUT A NEW
IN-GAME RESULT.  The tree is a demonstrated READER, not a demonstrated LEVER.
On 2026-10-14 a single mod shipped a rewritten
``CivTechTrees/BRITONS.json`` (one ``add_row``, one ``set_status``) alongside a
`.dat` edit; the log proves the mod loaded
(``Enabling mod #0 (aoe2mod smoke villager HP + Britons units)``) and the `.dat`
half worked, while **neither tree edit changed the game**.  Later probes cleared
the two cheapest explanations: "the overlay does not recurse into
subdirectories" is FALSE (``_probe/test_overlay_depth.py``: the WIDGETUI storage
root holds 550 nested mod files, deepest 4 levels, and the chibi emblem three
levels down is visible in the HUD), and "the file name or form is wrong" is
FALSE (``_probe/test_tree_form.py``, above).  So the survivors are scheduling
(the tree may be read before mods are mounted) and SCREEN (the panel the user
checked may be fed by ``futuravailableunits.json``, the file the exe names
beside ``CommandPanel`` and ``TechTreePreviewPanel``).

**And the SCREEN candidate got stronger, which downgraded that test from
"disproven" to merely "unproven".**  ``_probe/probe_panel_provenance.py`` shows
``futuravailableunits.json`` is a SHIPPED artifact, not a runtime cache: its
mtime (2026-09-23 13:04:40) is the same unpack as the .dat and all 62 tree
files, the exe postdates it by 19 days, and **11 game launches since have not
rewritten it**.  If the menu that was checked is fed by that file, rewriting the
tree could not have changed it -- so the 2026-10-14 run tested the wrong object
for that question.

**★★★ 2026-10-17: NEITHER JSON LAYER REMOVES A BUILD BUTTON.  THE `.dat` IS THE
ONLY LAYER SHOWN TO DRIVE THE BUILD MENU (m29132).**  `dsh test v9` carried three
sentences: A villagers 1000 hp, B grant unit 2550 to the British, C REVOKE unit
2550 from the Incas.  C deleted the Incas' tree row AND their panel entry while
leaving the `.dat` alone -- so the global `type 2` enable in tech 1350 still said
"yes".  **The user reported the Incas Barracks STILL shows the Champi Scout.**

The bytes were then checked (`_probe/test_revoke_is_not_enough.py`) so the
observation is about a real edit and not about a mod that failed to load:

  * v9's `INCAS.json` really has no 2550 row (56 -> 55 unit rows).
  * v9's panel really does not list 2550 for the Incas.
  * v9's `.dat` is shipped-plus-one-appended-effect (+80 B) -- the B sentence's --
    and still contains `tech 1350 -> type 2 enable 2550`.

**Therefore the "AND gate" reading recorded here earlier was WRONG.**  Deleting
both JSON layers did not take the button away, so no JSON layer is vetoing the
`.dat` on this path.  But the replacement model written here next was too
strong, and an independent review cut it down.  What the evidence supports:

    the `.dat` is the only layer SHOWN to move the build menu; it is not
    shown to be the only layer that CAN move it

  * v6 -> v7 changes only which technology carries the `type 2` enable, with
    both JSON layers byte-identical, and the button's age gate moved.  So the
    `.dat` can drive the menu.
  * v9 revoke left the button in place with both JSON layers removed.  That
    observation is PROVISIONAL, for two reasons of its own:
      - v9's `INCAS.json` was left with a dangling `Link ID 2550`
        (`civ_techs_units[16]`) after its `Node ID 2550` row was deleted.  All
        62 shipped tree files have ZERO dangling link ids, so the game was
        handed a state it never ships and may have fallen back to the `.dat`
        default tree -- in which case the button staying says nothing about
        whether the tree layer is read.
      - that session ran 43 s after the mod loaded, with no map load, so it
        cannot be confirmed that a match was ever entered and no interface is
        known to have been inspected.
  * the 2026-10-15 JSON-only grant has no surviving log, so it cannot be cited.

**The reason the `.dat` cannot be the whole story**: for units whose `type 2`
enable is global (`civ = -1`) and which have no per-civ enable, the shipped
`.dat` contains no per-civ availability signal at all.  32 such units ship,
including the Champi Scout (2550: one global enable from tech 1350, one global
disable from tech 1215, and per-civ enable = per-civ disable = 0; the discarded
tech-tree connection fields are all -1 too).  The `.dat` DOES use per-civ
enables for other units (8 -> civ 1, 11 -> civ 12, 763 -> civ 16), so this is
not a blind spot of the mechanism, it is a fact about those 32.  Something
outside the `.dat` decides which civilizations see their button, and the two
`resources/_common/dat` JSON layers are the only shipped data that encodes that
4-civ split -- yet v9's deletion of both did not move the button, and that is
the observation now marked provisional above.

**That these files are read at all** is still supported, but by weaker evidence
than this docstring used to claim: the file name ``futuravailableunits.json``
sits 96 bytes from `CommandPanel` and within three occurrences of
`TechTreePreviewPanel` in the executable, and
``widgetui/futuravailableunits.json`` is an 81-byte stub redirecting to
``resources/_common/dat/futuravailableunits.json``.  That makes the path a
fixed engine entry point; it does not say what the engine does with it.
``linkedTechs.json`` separately carries Cycle groupings the `.dat` cannot
express.  The tech-tree screen `widgetui/screentechtree.json` has 17 icon
widgets named in tree vocabulary (``NotAvailIcon``, ``UpgradeRequiredIcon``,
``RegionalUnitIcon`` ...), while the preview panel layout
`techtreepreviewpanel.json` mentions none of them -- so "the preview reads the
tree" rests on the screen's own asset names, not on a layout binding.

**ANSWERED HALF WAY 2026-10-18, THEN WALKED BACK 2026-10-19**: the panel is
excluded in both directions, but **the tree is NOT shown to be what the menu
follows**.  The user ran the two half-experiments the shipped game already
contained, and together they exclude ``futuravailableunits.json`` from BOTH
directions:

  * NOT NECESSARY -- Sicilians, Imperial, siege workshop (2026-10-15): the panel
    lists neither unit 588 nor its upgrade tech 320, and the game offered both the
    "升级到重型投石车" upgrade and the 重型投石车 button.
  * NOT SUFFICIENT -- Poles, dock (2026-10-18, the observation that used to be
    missing): the panel lists unit 691 in ``Units`` *and* upgrade tech 376 in
    ``Techs``, and **no Elite Cannon Galleon upgrade button appeared**.

What that pair does NOT establish is that the tree supplies the menu.  This
module's docstring said it did; that was an overreach.  **2026-10-19, `dsh test
v15`** sent the two ``CivTechTrees/<CIV>.json`` files and *nothing else* (the
``.dat`` was a byte-identical carrier, the panel untouched, both trees asserted
chain-closed): Incas lose unit 2550's row, Britons gain one.  The user's in-game
reading was **neither side changed** -- Incas still had the Champi Scout, Britons
still did not.  So writing this layer alone does not move the button.

The ``.dat`` is where the one *proven* lever lives: ``dsh test v5`` (2026-10-16)
changed a single byte -- ``train_location.ButtonID`` 1 -> 4 on British unit 2550
-- and the button appeared, because slot 1 was already full with the five-unit
militia line.  That is the only layer in this project ever observed moving the
facility menu.  Measured 2026-10-16.

**★★★ 2026-10-19 `dsh test v16`: THE BUTTON BYTE ALONE IS NOT ENOUGH EITHER.**
v16 sent one `.dat` and no JSON at all, with exactly two byte edits: British
unit 2550 ``train_location.ButtonID`` 1 -> 4 (the byte v5 was credited with) and
Incas unit 2550 gate ``Disabled`` 0 -> 1.  The artifact was verified byte by
byte (bare-deflate container, `CheckSum` computed, patched stream parses to EOF)
and the log shows the engine mounted it.  **The user's reading: neither side
changed.**  So v5's single byte was not a self-sufficient lever -- it was the
last missing byte in a set that already carried the `type 2` enable effect.

Corrected reading of v5, which is what this docstring got wrong: v5 changed ONE
byte *relative to v4*, but v4 already carried the enable effect.  What v5 showed
is that the button slot decides **which cell** a granted unit appears in, not
that the slot alone makes a unit appear.

Where this leaves the model, stated as narrowly as the evidence allows:

  * The ``.dat`` enable command (``type 2, a=<unit>, b=1``) hung on a
    civilization-owned free technology is the one ingredient that has ever been
    observed producing a button (v5/v6/v7), and it is the one the product's
    ``datgrant`` recipe writes.
  * Nothing observed so far needs the ``CivTechTrees`` layer to explain a
    screen, and the one experiment that isolated it (v15) showed no effect.
  * Nothing observed so far shows the ``.dat`` bit to be *sufficient* on its
    own for a civilization that does not already ship the unit: v16 changed the
    British slot and the British still did not get the button.
  * ``futuravailableunits.json`` is excluded in both directions (Poles /
    Sicilians), which is the strongest single result in this file.

**Open, and the reason `dsh test v17` exists**: whether ``type 2, b=0`` DISABLES
a unit for one civilization -- i.e. whether ``unit.availability.revoke`` can be
given a `.dat` half at all.  The shipped precedent is Armenians/Georgians
losing the Lumber Camp (``tech 932/940`` -> ``effect 944`` ->
``(2, 562, 0)``, ``(2, 584, 0)``, with their trees saying ``NotAvailable``), but
that precedent never has to out-vote an enable: nothing ever enables 562.  Unit
2550 IS enabled, globally, by ``tech 1350`` -- so a disable must land after it.
``_probe/probe_inca_late_carrier.py`` measured that no Incas-owned free tech sits
at a higher index than 1350, so v17 hangs the same disable on two carriers with
different firing times instead (``tech 495`` at 0:00, ``tech 508`` in the Castle
Age), plus the villager 1000 hp control.

What that leaves untouched: v9's surprise (deleting the row did not remove the
button) and v15's (adding one did not create it) are consistent with each other
-- this layer is written, loaded (``MainLog.txt`` shows ``Enabling mod``), and
still not what the menu reads.

And it separates perfectly: Huskarl is `ResearchedCompleted` for GOTHS and the
row is ABSENT for all 61 other civs; Archer/Villager are `ResearchedCompleted`
for all 62.

THREE FACTS THIS MODULE ENCODES, EACH LEARNED THE HARD WAY
=========================================================

1. **Absent means absent.**  A civ with no row at all cannot obtain the node, and
   that is different from "unknown" -- so a reader that treats a missing row as
   "no answer" loses the whole answer.  But a missing row is NOT the only way to
   be unable: a row reading ``NotAvailable`` is listed and still unobtainable,
   and the two states need different sentences (see :func:`plan`).

2. **The `Name` field is stale and must never be shown.**  Cross-checked against
   the string tables, it disagrees with them on 44 rows, all in the Chronicles
   civs, and the string table wins 44/44 (see ``semantic/index.py``).  Use
   ``Name String ID`` -- that is what :func:`name_string_id` returns.

3. **The status vocabulary is three words, and they are the engine's own**:
   ``ResearchedCompleted`` (available now), ``ResearchRequired`` (in the tree,
   gated behind a prerequisite), ``NotAvailable`` (listed but not obtainable).
   They are returned verbatim, never translated here -- an unrecognised status
   must surface as itself rather than be folded into a plausible-sounding word.

4. **"Has it" and "can build it" are different predicates** and were conflated
   here once.  ``ResearchRequired`` sits between them: War Galley reads
   ``ResearchRequired`` for all 56 dock-owning civs, so a reader that requires
   ``ResearchedCompleted`` reports that NOBODY can build a War Galley.  Use
   :func:`has` for "right now, no research" and :func:`can_build` for "ever".
   Verified against known answers in ``_probe/probe_status_meaning.py``.
"""
import collections
import json
import os

CIVTECHTREES_REL = os.path.join("resources", "_common", "dat", "CivTechTrees")

#: The three statuses the engine's own string table names.  Kept as a tuple so a
#: caller can assert "I handled every status" instead of never noticing a fourth.
STATUSES = ("ResearchedCompleted", "ResearchRequired", "NotAvailable")
#: `.dat` civ name -> CivTechTrees file stem.  Verified against this install: the
#: file names are UPPERCASE names, and exactly these six differ from a plain
#: upper() of the `.dat` name.  The value is the FILE STEM, which is not always a
#: plural of the dat name -- `Hindustanis` ships as `INDIANS.json` and `Magyars`
#: as `MAGYAR.json` (no trailing S), and guessing a plural here silently made both
#: civs report "has no CivTechTrees file", i.e. "cannot build anything".
#: `_probe/probe_availability_design.py` measures this bridge over all 63 civs;
#: `test_civtechtrees.py` asserts it is complete.
CIV_FILE_OVERRIDES = {
    "British": "BRITONS",
    "French": "FRANKS",
    "Byzantine": "BYZANTINES",
    "Mayan": "MAYANS",
    "Hindustanis": "INDIANS",
    "Magyars": "MAGYAR",
}


def civ_file_stem(civ_name):
    """The ``<CIV>`` in ``CivTechTrees/<CIV>.json`` for a `.dat` civ name."""
    return CIV_FILE_OVERRIDES.get(civ_name, (civ_name or "").upper())


def trees_dir(game_root):
    return os.path.join(game_root, CIVTECHTREES_REL)


def load_trees(game_root):
    """``{civ_name_as_in_the_file: <the parsed file itself>}``.

    The returned value IS the parsed JSON document, with one extra key
    ``"path"`` recording where it came from.  That matters: an earlier version
    reshaped each file into ``{"units": [...], "buildings": [...]}``, which read
    fine but BROKE THE WRITE PATH -- :func:`serialize` re-dumps whatever dict it
    is given, so it emitted ``"units"`` where the engine expects
    ``"civ_techs_units"``, producing a file the game cannot parse.  The failure
    was invisible to the reader tests and only the end-to-end test caught it,
    because reading never consults the key names.

    Use :func:`rows_of` / :func:`unit_rows` to read rows, and
    :func:`serialize` (which drops ``"path"``) to write.  Never rebuild the dict.

    Returns ``{}`` when the directory is missing rather than raising: a caller
    that cannot answer "can this civ have X" should say so, not crash.  Callers
    that need to distinguish "no directory" from "no rows" check
    :func:`trees_dir` with :func:`os.path.isdir` themselves.
    """
    d = trees_dir(game_root)
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".json"):
            continue
        path = os.path.join(d, fn)
        try:
            with open(path, encoding="utf-8") as fh:
                j = json.load(fh)
        except (OSError, ValueError):
            # A malformed file must not take out the other 61 civs.
            continue
        if not isinstance(j, dict):
            continue
        civ = j.get("civ_id") or fn[:-5]
        j["path"] = path
        out[civ] = j
    return out


#: The engine's key names inside one civ file.  Named once so the reader and the
#: writer cannot disagree about them (see the note in :func:`load_trees`).
UNITS_KEY = "civ_techs_units"
BUILDINGS_KEY = "civ_techs_buildings"


def rows_of(tree):
    """Every row of a tree, units first.  Reads the ENGINE's key names."""
    return (list(tree.get(UNITS_KEY) or []) + list(tree.get(BUILDINGS_KEY) or []))


def _rows(tree):
    return rows_of(tree)


#: `Node ID` is NOT one namespace, and this is the trap the whole module would be
#: worthless without.  39 ids appear under more than one `Use Type`, because a
#: node id is a UNIT id in a Unit row and a TECH id in a Tech row: id 8 is
#: Longbowman for BRITONS and `Town Watch` for the other 61 civs, id 692 is
#: Berserk for VIKINGS and (same integer) something else elsewhere.  Reading ids
#: without filtering by `Use Type` therefore reported Tarkan as owned by both HUNS
#: and BURGUNDIANS and Berserk by both VIKINGS and LITHUANIANS -- two false
#: positives that looked exactly like real sharing.
#:
#: `Unit` nodes are what the unit-record world refers to.  `Tech`/`Building` rows
#: use ids from a DIFFERENT space (the tech id space) and must not be compared
#: with a unit id at all.
UNIT_USE_TYPES = ("Unit",)

#: Rows for a TECHNOLOGY.  Measured: a tech row's ``Node ID`` is the ``.dat`` tech
#: ARRAY INDEX -- all 238 distinct tech node ids fall inside the 1510-record array
#: (``_probe/probe_tech_node_id.py``), while unit-use ids are unit ids.  Tech rows
#: live in the SAME ``civ_techs_units`` list as unit rows (there is no separate
#: tech key), separated only by this field, so every lookup must say which space
#: it means.  Asking the unit-filtered :func:`node_status` about a tech id returns
#: ``None`` for all 62 civs -- which reads as "no civilization has Loom".
TECH_USE_TYPES = ("Tech",)

#: Rows for a BUILDING.  The 63 building rows live in their own engine key
#: (``civ_techs_buildings``) with ``Use Type`` = ``Building``, and their
#: ``Node ID`` IS the ``.dat`` unit id of the building (Castle is 82 in both).
#: Measured 2026-10-31 across all 62 files: no id appears in both the Unit list
#: and the Building list under two different names (0 collisions), so widening a
#: unit question to ``UNIT_USE_TYPES + BUILDINGS_USE_TYPES`` cannot turn an
#: answer about a unit into an answer about a building.
#:
#: The reason this needs its own constant: asking the Unit space about a
#: building returns ``None`` for all 62 civs, which reads as "not in any tech
#: tree" -- a sentence that is false about the Castle and false about the
#: Barracks, and the exact shape of the mistake :data:`UNIT_USE_TYPES` warns
#: about one id space over.
BUILDINGS_USE_TYPES = ("Building",)


def unit_rows(tree):
    """Only the rows whose ``Node ID`` is a UNIT id.

    Everything user-facing about "can this civ build X" must go through here;
    :func:`node_status` on a raw tree would happily match a tech row.
    """
    return [e for e in _rows(tree)
            if isinstance(e, dict) and e.get("Use Type") in UNIT_USE_TYPES]


def tech_rows(tree):
    """Only the rows whose ``Node ID`` is a TECH id (see :data:`TECH_USE_TYPES`).

    The mirror of :func:`unit_rows`, and needed for the same reason: 5,244 tech
    rows share the ``civ_techs_units`` list with the unit rows and would otherwise
    be invisible to, or mistaken for, units.
    """
    return [e for e in _rows(tree)
            if isinstance(e, dict) and e.get("Use Type") in TECH_USE_TYPES]


def node_status(tree, node_id, use_types=UNIT_USE_TYPES):
    """The ``Node Status`` this civ gives ``node_id`` IN THE GIVEN SPACE, or ``None``.

    ``None`` means THE CIV DOES NOT HAVE IT -- not "unknown" and not "false".
    ``use_types`` selects the id space and defaults to units, because ``Node ID``
    is shared between the unit and tech spaces (see :data:`UNIT_USE_TYPES`); pass
    :data:`TECH_USE_TYPES` for a technology.  When the node appears more than once,
    a status that grants access wins over one that does not, so the answer does not
    depend on row order.
    """
    found = set()
    for e in _rows(tree):
        if (isinstance(e, dict) and e.get("Use Type") in use_types
                and e.get("Node ID") == node_id):
            found.add(e.get("Node Status"))
    if not found:
        return None
    for st in STATUSES:
        if st in found:
            return st
    return sorted(str(x) for x in found)[0]


def name_string_id(tree, node_id, use_types=UNIT_USE_TYPES):
    """The string-table id to DISPLAY for ``node_id`` IN THE GIVEN SPACE, or ``None``.

    Deliberately not the row's ``Name`` field: it is stale on 44 rows (all
    Chronicles) and the string table is right in 44/44 of those disagreements.
    Unit-filtered by default, for the same namespace reason as :func:`node_status`.
    """
    for e in _rows(tree):
        if (isinstance(e, dict) and e.get("Use Type") in use_types
                and e.get("Node ID") == node_id):
            sid = e.get("Name String ID")
            if sid is not None:
                return sid
    return None


def has(tree, node_id, use_types=UNIT_USE_TYPES):
    """True when this civ HAS ``node_id`` RIGHT NOW, with no research needed.

    Only ``ResearchedCompleted`` counts.  This is deliberately NOT the question
    "can this civ build it" -- use :func:`can_build` for that.  The two differ on
    14 real nodes: ``ResearchRequired`` is reachable (War Galley, Cannon Galleon,
    Hand Cannoneer for most civs) and ``NotAvailable`` is a UI listing.  Asking
    this function "can they build it" under-reports, e.g. it says 0 civs can build
    War Galley when 56 can.

    Pass :data:`TECH_USE_TYPES` to ask the same question about a technology, where
    ``ResearchedCompleted`` means "available to research", NOT "already researched"
    (Loom reads ``ResearchedCompleted`` for all 62 civs and nobody starts with Loom).
    """
    return node_status(tree, node_id, use_types) == "ResearchedCompleted"


def can_build(tree, node_id, use_types=UNIT_USE_TYPES):
    """True when this civ can EVER obtain ``node_id``.

    ``ResearchedCompleted`` (has it from the start) and ``ResearchRequired``
    (reachable by researching the prerequisite) both mean yes; ``NotAvailable``
    and a missing row both mean no.

    The three status words were pinned down against known answers
    (``_probe/probe_status_meaning.py``): no civ marks Galley ``NotAvailable``
    and no civ marks Huskarl ``ResearchRequired``, while Galley reads
    ``ResearchRequired`` for all 56 civs that own a Dock.  Folding
    ``ResearchRequired`` into "does not have it" is how a tool tells a player
    their civ cannot build something it demonstrably can.

    For a technology this answers "can this civ EVER research it", which is the
    same predicate one id space over.
    """
    st = node_status(tree, node_id, use_types)
    return st is not None and st != "NotAvailable"


def owners(trees, node_id, status="ResearchedCompleted", use_types=UNIT_USE_TYPES):
    """Every civ (sorted) whose exact status for ``node_id`` is ``status``."""
    return sorted(c for c, t in trees.items()
                  if node_status(t, node_id, use_types) == status)


def builders(trees, node_id, use_types=UNIT_USE_TYPES):
    """Every civ (sorted) that can EVER build ``node_id`` -- see :func:`can_build`.

    This is the list a UI asks for when it says "who can build this"; it is
    larger than ``owners(trees, node_id)`` on 14 nodes.  Pass
    :data:`TECH_USE_TYPES` for the "who can research this" list.
    """
    return sorted(c for c, t in trees.items()
                  if can_build(t, node_id, use_types))


def status_counts(tree):
    """``{status: n}`` over every row, for asserting a file was really read."""
    out = {}
    for e in _rows(tree):
        if isinstance(e, dict):
            out[e.get("Node Status")] = out.get(e.get("Node Status"), 0) + 1
    return out


#: One letter per status, because the compact table repeats it thousands of
#: times.  The letters match the `CivTechTrees/<CIV>.json` spelling already
#: shipped in ``_golden/civ_trees.json`` -- the page and both engines must not
#: disagree about what "C" means.
STATUS_LETTER = {"ResearchedCompleted": "C",     # available from the start
                 "ResearchRequired": "R",        # available, a tech gates it
                 "NotAvailable": "N"}            # this civ cannot have it

#: `Use Type` -> the one-letter bucket, the same spelling as the shipped table.
USE_LETTER = {"Building": "b", "Unit": "u", "Tech": "t"}


def compact(tree):
    """One civ's tree as ``{"b": {...}, "u": {...}, "t": {...}}``.

    WHY THIS EXISTS: the native backend answers ``/api/civ`` with this shape and
    the Python backend had no such route at all (see ``App.civ`` in
    ``aoe2mod/ui/server.py``).  A page that can draw the tree from one engine and
    not the other is the "the shipped build knows less than the repo" defect this
    project keeps re-finding, so the reader both engines share grows the method
    rather than the server inventing a private shape.

    A node can carry SEVERAL rows: MAPUCHE lists Skirmisher under buildings 87
    and 2556, because a row is keyed on ``(Use Type, Node ID, Building ID)`` and
    not on ``(Use Type, Node ID)``.  Keeping only the first would answer "this
    civ builds it in one place" while the game offers it in two, so every
    distinct row survives and only exact repeats collapse (measured: 0 of them).
    """
    out = {"b": {}, "u": {}, "t": {}}
    for e in _rows(tree):
        if not isinstance(e, dict):
            continue
        use = USE_LETTER.get(e.get("Use Type") or "")
        node = e.get("Node ID")
        letter = STATUS_LETTER.get(e.get("Node Status") or "")
        if use is None or node is None or letter is None:
            continue
        row = [e.get("Building ID"), letter, e.get("Age ID")]
        bucket = out[use].setdefault(str(node), [])
        if row not in bucket:
            bucket.append(row)
    return out


def collide_with_tech_space(trees):
    """Ids that are ambiguous WITHIN one civ file -- the namespace trap.

    Returns ``{node_id: {civ, ...}}`` for every id that appears BOTH as a unit
    row and as a non-unit row in the *same* civ's file.  Measured on this
    install: **22** ids are ambiguous within a file.  Do not confuse that with
    corpus-wide totals, which are larger because they mix civs together (39 ids
    appear under more than one `Use Type` when only the units lists are pooled;
    48 if the building rows are pooled too).  Only the within-one-file collision
    can actually mislead a lookup, so 22 is the number the filter is justified
    against.

    Exposed rather than hidden so a caller can explain the ambiguity, and so the
    regression test can assert the collision is real -- if a future data update
    ever gave the two spaces disjoint ranges this would go empty and the
    filtering could be relaxed.
    """
    out = {}
    for civ, t in (trees or {}).items():
        for e in _rows(t):
            if not isinstance(e, dict) or e.get("Use Type") in UNIT_USE_TYPES:
                continue
            nid = e.get("Node ID")
            if nid is None:
                continue
            for u in unit_rows(t):
                if u.get("Node ID") == nid:
                    out.setdefault(nid, set()).add(civ)
    return out


# =============================================================================
# WRITING THE LAYER
# =============================================================================
#
# Serialisation is byte-exact for all 62 shipped files, and the rule is not the
# obvious one.  `json.dumps(..., ensure_ascii=False, indent=2)` alone reproduces
# only 60 of 62: DANES.json and MAYANS.json each differ by 5 bytes because the
# game writes an apostrophe as the six characters `\u0027` while Python leaves `'`
# literal under `ensure_ascii=False`.  The apostrophe escape is the ONLY unicode
# escape anywhere in the corpus (2 occurrences, both in tech names: `Northmen's
# Fury`, `Hul'che Javelineers`), and there are no other backslash escapes at all.
#
# So the contract, verified 62/62:
#
#   1. json.dumps(obj, ensure_ascii=False, indent=2)
#   2. text.replace("'", "\\u0027")
#   3. text.replace("\n", "\r\n")
#   4. encode UTF-8 -- no BOM, and NO trailing newline
#
# A "close enough" writer would have shipped a file that parses identically and
# still differs on bytes nobody asked to change, which is exactly the kind of
# diff a mod author cannot explain.

_APOSTROPHE_ESCAPE = ("'", "\\u0027")


def serialize(tree):
    """Bytes for one tree, byte-identical to the shipped files."""
    obj = dict(tree)
    obj.pop("path", None)          # load_trees adds this; it is not part of the file
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    text = text.replace(_APOSTROPHE_ESCAPE[0], _APOSTROPHE_ESCAPE[1])
    text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


def verify_serializer(tree):
    """Re-parse what :func:`serialize` produced and require the same object.

    Guards the one way the apostrophe rule could go wrong: a name that already
    contains a literal ``\\u0027`` sequence would be double-escaped.  Returns
    ``(ok, reason)``; ``reason`` is ``""`` when ok.
    """
    blob = serialize(tree)
    try:
        back = json.loads(blob.decode("utf-8"))
    except ValueError as exc:
        return False, "the serialised bytes do not parse: %s" % exc
    expect = dict(tree)
    expect.pop("path", None)
    if back != expect:
        return False, ("the serialised bytes re-parse to a different object "
                       "(an escape round-trip problem)")
    return True, ""


def row_for(tree, node_id, use_types=UNIT_USE_TYPES):
    """The raw row dict this tree holds for ``node_id``, or ``None``.

    ``None`` means the civ does not have it.  Returning the ROW (not a status
    word) is what lets a caller copy it into another civ's file.
    """
    rows = [e for e in rows_of(tree) if isinstance(e, dict)]
    for e in rows:
        if e.get("Node ID") == node_id and e.get("Use Type") in use_types:
            return e
    return None


def _row_key(row):
    """The row's identity for "do these civs agree?" -- status excluded.

    ``Node Status`` is the field a grant REWRITES, so two civs whose rows differ
    only in status carry the same presentation and must not be counted as
    disagreeing variants.
    """
    return tuple(sorted((k, str(v)) for k, v in row.items()
                        if k != "Node Status"))


def donor_row(trees, node_id, use_types=UNIT_USE_TYPES):
    """``(civ, row)`` for the best civ to copy ``node_id``'s row from.

    Returns ``(None, None)`` when literally nobody can build it, which is what a
    grant must refuse with -- see :func:`availability.plan`.

    Only civs that can ACTUALLY build the node are considered (:func:`can_build`),
    because the copy inherits the donor's presentation -- ``Name String ID``,
    ``Picture Index``, ``Help String ID``, and on one node even ``Age ID`` and
    ``Link ID``.  Taking the first row in sorted order instead would, on 12 nodes,
    copy from a civ whose own row reads ``NotAvailable`` (node 5 Hand Cannoneer
    from ACHAEMENIDS, when ATHENIANS has a real one); on 5 of those the two rows
    differ in exactly those inherited fields.

    Ranked, because "first in sorted order" is deterministic but not MEANINGFUL:

    1. a donor whose own row reads ``ResearchedCompleted`` beats one that is
       merely ``ResearchRequired`` -- prefer a civ that already has it over one
       still working toward it.  (``grant`` writes ``Node Status`` explicitly, so
       this chooses WHICH row is copied, not what the receiver ends up with.)
    2. the row VARIANT the most civilizations use wins -- so the receiver gets
       the name and icon its neighbours show.  Measured: the old sorted-order
       pick handed the receiver a different visible NAME on 112 tech grants and
       3 unit grants (node 45 'Exorcism' vs the 56 civs' 'Faith'; node 125
       'Priestess' vs 'Monk'), because ``ACHAEMENIDS`` sorts first and is a
       Chronicles civ with its own localisation.  This rank takes that to 0.
    3. civ name last, so the emitted mod never depends on dict iteration order.
    """
    able = [c for c in sorted(trees or {})
            if can_build(trees[c], node_id, use_types)]
    if not able:
        return None, None
    freq = collections.Counter(
        _row_key(row_for(trees[c], node_id, use_types)) for c in able)

    def rank(civ):
        ready = node_status(trees[civ], node_id, use_types) == "ResearchedCompleted"
        r = row_for(trees[civ], node_id, use_types)
        return (0 if ready else 1, -freq[_row_key(r)], civ)

    civ = min(able, key=rank)
    return civ, row_for(trees[civ], node_id, use_types)


def reaches_building(tree, building_id):
    """Does ``tree`` contain ``building_id`` anywhere?

    True when the id appears as a node id in the tree OR is referenced as a
    ``Building ID`` by one of its own rows.  Used to warn that a copied
    ``Building ID`` may have no building to appear at in the receiving civ.

    Both tests are needed because the two halves of the file use the field
    differently: a building's own row carries the id under ``Node ID``, while a
    unit or tech row carries the id of the building that produces it under
    ``Building ID``.  A civ can legitimately have neither (ARMENIANS has no
    building 104 -- its Monk row reads 1806 -- so a granted Missionary, whose
    donor row says 104, has no Monastery to be trained at).
    """
    want = str(building_id)
    for r in rows_of(tree):
        if not isinstance(r, dict):
            continue
        if str(r.get("Node ID")) == want or str(r.get("Building ID")) == want:
            return True
    return False


#: The ten JSON keys ``grant`` copies from the donor row, in the player's words.
#: The keys themselves are the game's own field names and must not be translated
#: -- they are what the file says -- but a sentence that only reads
#: ``inherited Picture Index=12`` tells a Chinese player nothing about what went
#: wrong, so each one gets a name here.  Unknown keys fall back to the raw one
#: rather than disappearing.
_FIELD_ZH = {
    "Name": "名字",
    "Name String ID": "名字文本编号",
    "Picture Index": "图标编号",
    "Help String ID": "帮助文本编号",
    "Building ID": "建筑编号",
    "Age ID": "时代",
    "Link ID": "升级自哪个节点",
    "Trigger Tech ID": "触发科技编号",
    "Prerequisite IDs": "前置节点",
    "Prerequisite Types": "前置类型",
}


def grant(tree, node_id, source_row, status="ResearchedCompleted",
          use_types=UNIT_USE_TYPES):
    """Add ``node_id`` to ``tree`` as a COPY of ``source_row``.

    Returns ``(row, warnings)``.  Warnings are returned rather than raised: they
    describe fields the copy inherited that are arguably the donor civ's, and the
    caller decides (``Name``/``Name String ID``/``Picture Index``/``Help String
    ID``/``Building ID``/``Age ID``).

    The sentences are Chinese because they reach the player: the preview prints
    them verbatim, and 1,497 of 14,687 unit grants carry the receiver warning
    below, so "inherited Building ID" was a sentence a Chinese player had to read
    in English.

    One warning is about the RECEIVER, not the donor: measured on this install,
    1,497 of 14,687 unit grants and 224 of 10,369 tech grants inherit a
    ``Building ID`` the receiving civ cannot reach at all, and no other donor
    would fix it (0 of those are fixable by a different choice in the unit
    space).  ``Building ID`` is where the thing is produced or shown, so the copy
    would have nowhere to appear.  Generic "inherited X from the donor row" would
    bury that among six cosmetic fields, so it gets its own sentence.

    Refuses to duplicate: if the tree already has the node, the existing row is
    returned untouched with a warning, because "grant something already granted"
    is far more likely a caller bug than an intent.
    """
    warnings = []
    existing = row_for(tree, node_id, use_types)
    if existing is not None:
        # The tree's own `civ_id` is the FILE stem ("ARMENIANS"), which is not
        # what a player calls that civilization.  These sentences reach the
        # screen through `availability.plan`'s `warnings`.
        from .civnames import chinese as _civ_zh
        return existing, ["%s 本来就有第 %s 号节点，什么都没加"
                          % (_civ_zh(tree.get("civ_id")), node_id)]
    if source_row is None:
        raise ValueError("cannot grant node %s without a source row" % node_id)
    row = dict(source_row)
    row["Node ID"] = node_id
    row["Use Type"] = source_row.get("Use Type", use_types[0])
    row["Node Status"] = status
    # Fields that are the DONOR's presentation, not the node's identity.  They are
    # inherited because inventing values would be worse, but they are reported:
    # a copied Name String ID shows the donor's wording, and a copied Building ID
    # means "trained at the donor's building".
    for f in ("Name", "Name String ID", "Picture Index", "Help String ID",
              "Building ID", "Age ID", "Link ID", "Trigger Tech ID",
              "Prerequisite IDs", "Prerequisite Types"):
        if f in row:
            # Numbers are quoted because they are what the player would have to
            # look up.  A STRING value here is the donor's own identifier written
            # in the data file's English ("Missionary"), and printing that on a
            # Chinese screen adds an English word to a Chinese sentence without
            # telling the player anything they can act on -- the real news is
            # that the field was copied at all.
            _val = row[f]
            _zh = _FIELD_ZH.get(f, f)
            if isinstance(_val, str):
                warnings.append("「%s」是从捐赠方那一行照抄下来的，不是为这个文明写的"
                                % _zh)
            else:
                warnings.append("「%s」是从捐赠方那一行照抄下来的（%r），"
                                "不是为这个文明写的" % (_zh, _val))
    # The receiver-aware one.  Kept separate from the loop above because it is
    # the only inherited field whose problem is about the civ RECEIVING it.
    _b = row.get("Building ID")
    if _b is not None and not reaches_building(tree, _b):
        warnings.append(
            "捐赠方那一行的「建筑编号」是 %r，而这个文明的科技树里根本没有这座建筑，"
            "所以照抄过来的条目可能没有地方出现" % (_b,))
    tree.setdefault(UNITS_KEY, []).append(row)
    return row, warnings


def _link_of(row):
    """The predecessor this row upgrades from, or -1 when it is a chain head."""
    if not isinstance(row, dict):
        return -1
    v = row.get("Link ID")
    if v is None:
        return -1
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


def clear_links_to(tree, gone_ids, use_types=None):
    """Drop ``Link ID`` from any kept row that points at a removed node.

    A removed node can be referenced two ways, and they need different repairs:

    * a row of the SAME use type linking to it is an UPGRADE SUCCESSOR -- the
      row is meaningless without its predecessor, so :func:`revoke` deletes it.
    * a row of ANOTHER use type linking to it is a DISPLAY attachment.  Measured on
      the 62 shipped files: of the 2,367 Tech rows carrying a Link ID, 2,320 point
      at Techs/Buildings and only 7 point at a Unit; those 7 are unrelated research
      entries (tech 602 "Arson" -> unit 1699 "Flemish Militia") whose
      ``Draw Node Type`` is ``UnitTech``.  And 2,877 Tech rows ship with NO Link ID
      at all, in the very same shapes -- so clearing the field is an ordinary,
      shipped form, while deleting the research would remove something the user
      never asked to touch.

    Returns the number of rows whose Link ID was cleared.
    """
    cleared = 0
    for key in (UNITS_KEY, BUILDINGS_KEY):
        rows = tree.get(key)
        if not isinstance(rows, list):
            continue
        for e in rows:
            if not isinstance(e, dict):
                continue
            if use_types is not None and e.get("Use Type") in use_types:
                continue
            if _link_of(e) in gone_ids:
                e.pop("Link ID", None)
                cleared += 1
    return cleared


def dangling_links(tree):
    """Every (use type, node id, missing link target) a file still carries.

    Empty is the invariant: all 62 shipped files have zero, and anything this
    module writes must too, because a missing chain target gives the game licence
    to reject the whole tree.
    """
    for key in (UNITS_KEY, BUILDINGS_KEY):
        rows = tree.get(key)
        if not isinstance(rows, list):
            continue
        have = set()
        for e in rows:
            if isinstance(e, dict):
                nid = e.get("Node ID")
                if isinstance(nid, int):
                    have.add(nid)
        out = []
        for e in rows:
            if not isinstance(e, dict):
                continue
            link = _link_of(e)
            if link >= 0 and link not in have:
                out.append((e.get("Use Type"), e.get("Node ID"), link))
        if out:
            return out
    return []


def chain_closure(tree, node_id, use_types=UNIT_USE_TYPES):
    """Every node id ``revoke(tree, node_id)`` would remove, including itself.

    ``revoke`` deletes a node and then any row that upgraded from it, walking up
    the chain until nothing links to a removed id.  A caller that is verifying an
    already-performed edit needs the same set to know which vanished rows were
    supposed to vanish -- otherwise a legitimate cascade looks like collateral
    damage.  Computed from the tree BEFORE the edit.
    """
    out = {node_id}
    changed = True
    while changed:
        changed = False
        for key in (UNITS_KEY, BUILDINGS_KEY):
            rows = tree.get(key)
            if not isinstance(rows, list):
                continue
            for e in rows:
                if not isinstance(e, dict):
                    continue
                if e.get("Use Type") not in use_types:
                    continue
                if _link_of(e) in out and e.get("Node ID") not in out:
                    out.add(e.get("Node ID"))
                    changed = True
    return out


def revoke(tree, node_id, use_types=UNIT_USE_TYPES, revoked_ids=None):
    """Remove ``node_id`` from ``tree`` and re-close every chain it was part of.

    Returns the number of rows removed.  Removing is what makes a civ UNABLE to
    obtain something, and 0 is a legitimate answer (the civ never had it), not an
    error.

    The removal CASCADES up the upgrade chain.  Deleting a node while leaving a
    row that still says ``Link ID = node_id`` produces a dangling reference that no
    shipped file contains (measured: 62 files, 3,686 unit rows, 0 dangling links),
    and the game is entitled to reject the whole tree over it.  The cascade is
    also what the caller MEANS: "this civilization may not have this unit" implies
    its upgrades are gone too, since nothing can be upgraded from a unit the civ
    cannot field.

    Rows of other use types that merely DISPLAY-attach to a removed node keep their
    row and lose the link (:func:`clear_links_to`), because those are unrelated
    research entries and deleting them would remove more than was asked.

    ``revoked_ids`` may be a set/list; the ids removed are added to it so callers
    can report what went.
    """
    total = 0
    gone = set()
    for key in (UNITS_KEY, BUILDINGS_KEY):
        rows = tree.get(key)
        if not isinstance(rows, list):
            continue
        # Every pass deletes the rows carrying a doomed id, then the rows whose
        # Link ID pointed at anything deleted become doomed themselves; the chain
        # is walked until nothing more matches.
        doomed = {node_id}
        while doomed:
            kept = []
            deleted = set()
            for e in rows:
                if isinstance(e, dict) and e.get("Use Type") in use_types:
                    eid = e.get("Node ID")
                    if eid in doomed:
                        deleted.add(eid)
                        if revoked_ids is not None:
                            revoked_ids.add(eid)
                        continue
                kept.append(e)
            step = len(rows) - len(kept)
            if not step:
                break
            rows = kept
            tree[key] = rows
            total += step
            gone |= deleted
            doomed = {e.get("Node ID") for e in rows
                      if isinstance(e, dict) and _link_of(e) in gone}
    if gone:
        clear_links_to(tree, gone)
    return total

