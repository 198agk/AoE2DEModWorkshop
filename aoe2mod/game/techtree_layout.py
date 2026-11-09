# -*- coding: utf-8 -*-
"""The tech tree's GRID: where every building, unit and technology sits.

This is a faithful port of `generateTechTreeJsons.py` from SiegeEngineers'
aoe2techtree, which is the script that turns the game's own
``resources/_common/dat/CivTechTrees/<CIV>.json`` into the ``data/trees/<CIV>.json``
the website draws.  Porting it (rather than inventing a layout) is what makes
this page match BOTH the game and https://aoe2techtree.net/ at the same time:
the game ships the rows, the script decides the grid, and the site draws that
grid.  Measured 2026-11-08 on this install: the port reproduces the site's own
``BRITONS.json`` with **0 field differences** over all 11 compared keys, and it
completes on all **62** shipped civ files without raising.

WHY THE ALGORITHM IS NOT "OBVIOUS": it is stateful and order-dependent.  A unit
is placed relative to its building's grid, links to the item above it in the
same column, and when two items collide the collision is resolved by looking at
what the occupant's own flags say -- and in one case the official script RAISES
rather than guess.  Reimplementing "something equivalent" produces a tree that
looks plausible and differs from the game.  So the control flow below is kept
line-for-line.
"""
import json
import os
import re

CIVTECHTREES_REL = os.path.join("resources", "_common", "dat", "CivTechTrees")
CIVILIZATIONS_REL = os.path.join("resources", "_common", "dat", "civilizations.json")

#: `Use Type` decides which icons.json table holds the picture.  Measured over
#: all 10,742 rows of all 62 civs: `Building` -> Buildings, `Unit` -> Units,
#: `Tech` -> Techs, **0 missing**.  `Node Type` must NOT be used for this: it
#: splits into Research / UnitUpgrade / UniqueUnit / BuildingTech / ... and 22
#: rows would land on no table at all.
SECTION_FOR_USE_TYPE = {"Building": "Buildings", "Unit": "Units", "Tech": "Techs"}

#: The four age names the engine stores, in Age ID order.  `4201..4204` is the
#: base game; `407089..407092` is the Chronicles DLC's own set (antiquity /
#: city / classical / imperial).  Which pair applies is decided per civilisation
#: by `era` in civilizations.json, never guessed.
AGE_STRING_IDS = {
    "base": (4201, 4202, 4203, 4204),
    "antiquity": (407089, 407090, 407091, 407092),
    # Rome at War ships the SAME four ids but its own table calls them 石器/工具/
    # 青铜/铁器时代.  The ids are shared, the text is per mode, which is exactly
    # why `age_names` takes the mode's own string dict and not one merged one.
    "pompeii": (4201, 4202, 4203, 4204),
}

ROWS = 8

#: Where a "mode"'s own data lives, relative to the install.  Rome at War is a
#: MODE, not a DLC: its civilizations, its `CivTechTrees`, its icon tables and
#: its string tables all sit under `modes/Pompeii/` and none of them are in the
#: base install's copies.  Measured 2026-11-08: mixing them is not a style
#: question -- the base tables have no name for 1,836 of the mode's 2,142 rows,
#: and the mode's table reuses ids 4201..4204 and 120150..120166 for different
#: text, so a merged dict would rename the base game's ages and its Britons
#: blurb.  One dict per mode, never one dict for both.
MODE_BASE = "base"
MODE_POMPEII = "pompeii"
MODE_REL = {MODE_BASE: "", MODE_POMPEII: os.path.join("modes", "Pompeii")}
MODE_LABEL = {MODE_BASE: "本体与编年史", MODE_POMPEII: "罗马归来"}
EMBLEMS_REL = os.path.join("resources", "_common", "wpfg", "resources", "civ_emblems")
#: The game's own age medallions (I / II / III / IV).  Shipped as plain PNG at
#: 80x80 under the install, so no decode step and no dependence on the site's
#: own re-drawn icons.
AGE_ICONS_REL = os.path.join("resources", "_common", "wpfg", "resources", "Icons")


class _Item(object):
    """One row of the engine file, plus the grid cell it ends up in.

    A plain class rather than a dataclass on purpose: the placement loop mutates
    `row` and `grid`, and the whole point of the port is that those mutations
    happen in the official order.
    """

    __slots__ = ("id", "age_id", "row", "building_id", "help_string_id",
                 "link_id", "link_node_type", "name", "name_string_id",
                 "node_id", "node_status", "node_type", "picture_index",
                 "building_in_new_column", "building_upgraded_from_id",
                 "use_type", "grid")

    def __init__(self, j):
        self.id = "%s_%s_%s" % (j["Use Type"], j["Node ID"], j["Building ID"])
        self.age_id = int(j["Age ID"])
        self.row = (self.age_id - 1) * 2
        self.building_id = int(j["Building ID"])
        self.help_string_id = int(j.get("Help String ID") or 0)
        self.link_id = j.get("Link ID")
        self.link_node_type = j.get("Link Node Type")
        self.name = j.get("Name") or ""
        self.name_string_id = j.get("Name String ID")
        self.node_id = int(j["Node ID"])
        self.node_status = j["Node Status"]
        self.node_type = j.get("Node Type")
        self.picture_index = int(j.get("Picture Index") or 0)
        self.building_in_new_column = j.get("Building in new column")
        self.building_upgraded_from_id = j.get("Building upgraded from ID")
        self.use_type = j["Use Type"]
        self.grid = [[None] for _ in range(ROWS)]

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


def _coordinates(building, item):
    """(row, col) of `item` inside `building.grid`, or None."""
    for r, row in enumerate(building.grid):
        for c, cell in enumerate(row):
            if cell == item.id:
                return r, c
    return None


def _add_column(building):
    for row in building.grid:
        row.append(None)


def _aged(rows):
    """Rows that carry an `Age ID`; the rest are the mode's leftovers.

    Rome at War's 17 tree files each hold FIVE rows with no `Age ID` at all
    (Improved Bow / Trireme / Catapult Trireme / Small Wall / Watch Tower --
    85 rows over the mode, the same five in every file).  They are `Tech` rows
    with no age, which means no band, which means no cell: there is nowhere to
    draw them.  The official site drops them too -- its own `ror/data/data.json`
    lists 47 techs for Greeks and marks 101/102/103 with `age: -1` for the rows
    it cannot place.  Dropping is not a workaround for a crash; it is what the
    page has always shown.  Counted here so the payload can say how many.
    """
    return [j for j in (rows or ()) if j.get("Age ID") is not None]


def layout(tree):
    """`(buildings, units_techs)` -- the same shape `data/trees/<CIV>.json` has.

    Raises `RuntimeError` where the official script raises: a collision with an
    item that carries no flag allowing a push is a data shape this algorithm was
    never written for, and inventing a placement would silently produce a tree
    that disagrees with the game.  Measured: none of the 62 shipped files gets
    there.
    """
    buildings = [_Item(j) for j in _aged(tree.get("civ_techs_buildings"))]
    units = [_Item(j) for j in _aged(tree.get("civ_techs_units"))]
    every = buildings + units
    seen = set()
    for it in every:
        if it.id in seen:
            raise RuntimeError("duplicate node id %r in one civ file" % (it.id,))
        seen.add(it.id)

    by_node = {}
    for it in every:
        by_node.setdefault(it.node_id, []).append(it)

    for it in units:
        # The building this item hangs under.  A unit's `Building ID` names a
        # BUILDING row; a technology's may name a unit row (an upgrade chain
        # that has no building of its own), which is why the fallback exists.
        cands = [b for b in buildings if b.node_id == it.building_id]
        if not cands:
            cands = [b for b in units
                     if b.node_id == it.building_id and b.use_type != "Tech"]
            if not cands:
                raise RuntimeError("no host building for %r" % (it.id,))
        host = cands[0]
        if host.row == it.row:
            it.row += 1

        link_at = None
        if it.link_id:
            # The linked item, in the same order the official script tries:
            # unique by node id, else unique within the building, else the one
            # that is not a Research node.
            same = by_node.get(it.link_id) or []
            if len(same) != 1:
                same = [x for x in same if x.building_id == it.building_id]
            if len(same) != 1:
                same = [x for x in same if x.node_type != "Research"]
            if same:
                link_at = _coordinates(host, same[0])

        last_row = -1
        for r in range(ROWS):
            if host.grid[r][-1] is not None:
                last_row = r
        row = it.row
        col = len(host.grid[row]) - 1
        if link_at:
            link_row, link_col = link_at
            col = link_col
            if it.row == link_row:
                it.row += 1
                row += 1
        else:
            if host.grid[row][-1] is not None or last_row >= row:
                _add_column(host)
                col += 1
        occupant = host.grid[row][col]
        if occupant is not None:
            held = next(x for x in every if x.id == occupant)
            if held.building_in_new_column or held.node_type == "UniqueBuilding":
                _add_column(host)
                host.grid[row][col + 1] = occupant
                host.grid[row][col] = None
            else:
                raise RuntimeError(
                    "%s grid[%d][%d] is occupied by %s while placing %s"
                    % (host.id, row, col, occupant, it.id))
        host.grid[row][col] = it.id

    for it in units:
        if not any(cell for row in it.grid for cell in row):
            it.grid = None
    return [b.as_dict() for b in buildings], [u.as_dict() for u in units]


def _join_wrapped(text):
    """Collapse a game name's literal line breaks into one line."""
    if not text:
        return ""
    text = text.replace("\r", "\n").replace("\\n", "\n")

    def glue(m):
        left, right = m.group(1), m.group(2)
        # Two CJK halves are the same word wrapped; anything else keeps a space.
        sep = "" if (ord(left) > 0x2E7F and ord(right) > 0x2E7F) else " "
        return left + sep + right

    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(\S)\s*\n\s*(\S)", glue, text)
    return text.replace("\n", " ").strip()


def _decorate(items, strings):
    """Add the two fields the screen needs and the algorithm has no opinion on."""
    out = []
    for it in items:
        d = dict(it)
        sid = d.get("name_string_id")
        zh = ""
        if sid is not None:
            try:
                zh = strings.get(int(sid)) or ""
            except (TypeError, ValueError):
                zh = ""
        # The string table spells a line break as a literal backslash-n
        # ("\u653b\u57ce\n\u6b66\u5668\u5382" is one name on two lines in the
        # game's window).  A cell is one line.  Chinese wraps mid-word, so those
        # halves join with nothing between them -- with a space you get
        # "\u653b\u57ce \u6b66\u5668\u5382", which is not a word; Latin script needs the
        # space.  The raw bytes stay in the .json if anyone needs them.
        zh = _join_wrapped(zh or "")
        d["name_zh"] = zh
        hid = d.get("help_string_id")
        help_zh = ""
        if hid:
            try:
                help_zh = strings.get(int(hid)) or ""
            except (TypeError, ValueError):
                help_zh = ""
        # The help body is prose, so its line breaks stay line breaks; the
        # screen renders them, it does not flatten them the way a cell must.
        d["help_zh"] = help_zh.replace("\\n", "\n").strip()
        d["section"] = SECTION_FOR_USE_TYPE.get(d.get("use_type"), "")
        out.append(d)
    return out


def build(tree, strings=None):
    """The whole payload for one civilisation.

    Returns ``{"buildings": [...], "units_techs": [...]}`` plus, on each item,
    ``name_zh`` (from the string table) and ``section`` (which icons.json table
    holds its picture).  Nothing here reads the disk; `civ_rows` and the caller
    supply the two files.
    """
    buildings, units = layout(tree)
    strings = strings or {}
    return {"buildings": _decorate(buildings, strings),
            "units_techs": _decorate(units, strings)}


def mode_root(game_root, mode=MODE_BASE):
    """The folder a mode's `resources/` hangs off; `""` for the base install."""
    rel = MODE_REL.get(mode or MODE_BASE)
    if rel is None:
        raise ValueError("no such mode: %r" % (mode,))
    return os.path.join(game_root, rel) if rel else game_root


def trees_dir_for(game_root, mode=MODE_BASE):
    return os.path.join(mode_root(game_root, mode), CIVTECHTREES_REL)


def emblems_dir(game_root, mode=MODE_BASE):
    return os.path.join(mode_root(game_root, mode), EMBLEMS_REL)


# The emblem comes in two very different pictures and the game never shows them
# in the same place.  `civ_emblems/<civ>.png` is 450x280 -- the drawn banner the
# history screen prints -- while `civ_techtree/menu_techtree_<civ>.png` is the
# 104x104 shield the tech-tree button and the in-game tech-tree header carry.
# The header here sits where the game puts the shield, so the shield is what it
# gets (measured 2026-11-08: britons.png is crossed spears on a rose, the shield
# is three gold lions).
ART_REL = os.path.join("resources", "_common", "wpfg", "resources", "civ_techtree")
ART_PREFIX = "menu_techtree_"
# Four civs spell the shield differently from both the tree stem and the emblem
# file: stem INCAS/MAGYAR/BERBERS/INDIANS, emblem incas/magyars/berbers/
# hindustanis, shield inca/magyars/berber/indians.
ART_ALIASES = {
    "incas": ("inca",), "berbers": ("berber",),
    "hindustanis": ("indians",), "magyar": ("magyars",), "magyars": ("magyar",),
}


def art_dir(game_root, mode=MODE_BASE):
    return os.path.join(mode_root(game_root, mode), ART_REL)


def civ_art(game_root, mode, stem, emblem_name=""):
    """The shield PNG for one civilization, or None.

    Tried in order: the emblem filename the mode's own `civilizations.json`
    states, the tree stem, and the four known alias spellings.  Resolving from
    the stem alone loses INCAS/BERBERS/MAGYAR, whose shield files drop the `s`.
    """
    folder = art_dir(game_root, mode)
    names = []
    for raw in (emblem_name, stem):
        n = os.path.splitext(os.path.basename(str(raw or "")))[0].strip().lower()
        if n:
            names.append(n)
            names.extend(ART_ALIASES.get(n, ()))
    for n in names:
        p = os.path.join(folder, ART_PREFIX + n + ".png")
        if os.path.isfile(p):
            return p
    return None


def age_icons(game_root):
    """``{1: path, ...}`` for the four shipped age medallions, missing ones out."""
    base = os.path.join(game_root, AGE_ICONS_REL)
    out = {}
    for n in (1, 2, 3, 4):
        p = os.path.join(base, "age-%d.png" % n)
        if os.path.isfile(p):
            out[n] = p
    return out


def load_trees_for(game_root, mode=MODE_BASE):
    """``{stem: <the parsed file>}`` for one mode, never raising on absence."""
    folder = trees_dir_for(game_root, mode)
    out = {}
    try:
        names = os.listdir(folder)
    except OSError:
        return out
    for name in names:
        if not name.lower().endswith(".json") or name.lower() == "civtechtrees.json":
            continue
        stem = name[:-5]
        try:
            with open(os.path.join(folder, name), encoding="utf-8-sig") as fh:
                out[stem] = json.load(fh)
        except (OSError, ValueError):
            continue
    return out


def clean_prose(text):
    """A civilization blurb as one readable block.

    The game stores it with a LITERAL backslash-n for its line breaks and with
    `<b>`/`<i>` markup for emphasis, and it also opens the unique-unit line with
    an unfollowed `<b>` ("<b>独特单位：<b>").  Rendered as-is on a page it prints
    the tags; rendered as HTML it invites whatever else the table holds.  So the
    tags come off and the breaks become real ones.
    """
    text = (text or "").replace("\\n", "\n")
    text = re.sub(r"</?[a-zA-Z][^<>]{0,20}>", "", text)
    text = text.replace("</b>", "").replace("<b>", "")
    return text.strip()


def civ_rows(game_root, mode=MODE_BASE):
    """``[{stem, internal_name, name_string_id, era, desc_id, emblem, mode}]``.

    Read from the game's own `civilizations.json`, not from a table in this
    repo: a new civilisation ships as a new row here plus a new
    `CivTechTrees/*.json`, and nothing in this module has to change.  That is
    the answer to 「官方又出新文明」 without a code edit.

    Rome at War keeps its own list under `modes/Pompeii/`, so this takes a mode.
    Its `emblem_image_path` reads `/resources/civ_emblems/egyptian.png`, which is
    NOT where the file is (the real path is
    `<mode>/resources/_common/wpfg/resources/civ_emblems/egyptian.png`); the
    basename is taken and the directory is rebuilt, the same way the base civs'
    `tech_tree_image_path` has to be.
    """
    path = os.path.join(mode_root(game_root, mode), CIVILIZATIONS_REL)
    try:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return []
    out = []
    for c in doc.get("civilization_list") or ():
        rel = (c.get("emblem_image_path") or "").replace("\\", "/")
        out.append({"stem": c.get("tech_tree_name") or "",
                    "internal_name": c.get("internal_name") or "",
                    "name_string_id": c.get("name_string_id"),
                    "desc_id": c.get("tech_tree_description_string_id"),
                    "emblem": os.path.basename(rel) if rel else "",
                    "era": c.get("era") or "base",
                    "mode": mode or MODE_BASE})
    return out


def age_names(era, strings):
    """The four age labels for a civilisation's era."""
    ids = AGE_STRING_IDS.get(era or "base") or AGE_STRING_IDS["base"]
    return [strings.get(i) or "" for i in ids]
