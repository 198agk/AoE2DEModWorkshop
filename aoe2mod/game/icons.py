# -*- coding: utf-8 -*-
"""Map a unit, technology or civilization to the icon file the game draws.

There are TWO icon tables in `widgetui/icons.json` for the same numeric id, and
they are different pictures:

    "Units"      the unit portrait / training-button art
    "Buildings"  the build-menu button art

Rendered and looked at (see `_probe/probe_icon_sheet.py`): id 2 is crossed
swords in Buildings and a knight's crest in Units; id 28 is two villagers in
Buildings and a trebuchet in Units.  So "which section" is not cosmetic -- the
wrong pick shows a player a picture of something else.

What decides it, measured over all 1,344 icon-bearing unit records
(`_probe/probe_icon_rule_composite.py`, `probe_icon_families.py`):

    114  the Builder (unit 118) makes it          -> "Buildings"  (build menu)
    459  a building (type 80) trains it           -> "Units"      (training list)
    183  no producer, and a Buildings material
         name matches the unit's English name     -> "Buildings"
    588  none of the above                        -> "Units"      (default)

The default is not a coin flip dressed up as a rule: of those 588, 327 have no
Buildings entry at all, so the Units table is the only picture that exists; the
remaining 261 are legacy duplicates.  1,344 of 1,344 resolve to a file on disk.

Technologies always use the "Techs" section: 419 of 422 resolve, and the 3 that
do not are named in `resolve`'s return value rather than silently dropped.

Civilizations use "CivEmblem", whose value is a bare file stem under
`resources/_common/wpfg/resources/civ_emblems/<stem>.png`.  Two stems are spelled
differently on disk than in icons.json (inca/incas, berber/berbers) and are
hard-coded because no rule derives that pair; slots 000 and 066 are empty
placeholders, which is why 65 pictures serve 63 civilizations.
"""
import json
import os
import re

# Section names as they appear in icons.json.
UNITS = "Units"
BUILDINGS = "Buildings"
TECHS = "Techs"
CIV_EMBLEM = "CivEmblem"

BUILDER_UNIT_ID = 118

# See the module docstring: two emblems are spelled differently on disk.
# Direction matters and both directions are needed -- the table says
# `civ_emblems_inca` while the disk says `incas.png`, so a caller arriving with
# the tree stem ("INCAS" -> "incas") must be mapped BACK to find the table row,
# and then FORWARD again to find the file.  Getting this one-way lost the two
# civilizations entirely.
_EMBLEM_ALIASES = {"inca": "incas", "berber": "berbers"}
_EMBLEM_BACK = {v: k for k, v in _EMBLEM_ALIASES.items()}

_STOPWORDS = frozenset((
    "icon", "icons", "building", "buildings", "unit", "units", "the", "of",
    "and", "a", "b", "full", "empty", "no", "new", "old",
))


def name_tokens(text):
    """Words of a material or unit name, for the build-menu witness test.

    Both digit-stripping steps are load-bearing, and both were found by
    measurement, not by reading:

    * split camelCase BEFORE removing digits, or `Icons002Barracks1` collapses
      into the single token "iconsbarracks" and every Barracks icon looks
      unrelated to "Barracks";
    * strip digits AFTER, because every material name ends in a variant number
      (`BuildingIcons002Barracks1`) and "barracks1" never equals "barracks".

    Spelling that out because this function reported a 81-icon "discovery" that
    was purely its own bug.
    """
    if not text:
        return frozenset()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    s = re.sub(r"\d+", " ", s)
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return frozenset(w.lower() for w in s.split()
                     if len(w) >= 3 and w.lower() not in _STOPWORDS)


class IconBook(object):
    """`icons.json` plus `materials.json`, read once.

    Both files are big (73 KB and 2.4 MB) and neither changes while the game is
    installed, so they are read lazily and kept.

    materials.json is UTF-8 **with a BOM** and its two tables are LISTS of
    `{"MaterialDef": ...}` / `{"AtlasDef": ...}` wrappers, not dictionaries --
    calling `.get` on the list is the first mistake this file invites.
    """

    def __init__(self, game_root):
        self.game_root = game_root
        self._icons = None
        self._materials = None
        self._atlases = None

    # ---- loading ---------------------------------------------------------
    @property
    def widgetui(self):
        return os.path.join(self.game_root, "widgetui")

    def _load_icons(self):
        if self._icons is None:
            path = os.path.join(self.widgetui, "icons.json")
            with open(path, encoding="utf-8-sig") as fh:
                self._icons = json.load(fh)
        return self._icons

    def _load_materials(self):
        if self._materials is not None:
            return self._materials
        path = os.path.join(self.widgetui, "materials.json")
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
        materials = {}
        for entry in doc.get("Materials") or ():
            md = entry.get("MaterialDef", entry)
            if md.get("Name"):
                materials.setdefault(md["Name"], md)
        atlases = {}
        for entry in doc.get("AtlasTextures") or ():
            ad = entry.get("AtlasDef", entry)
            if ad.get("Name"):
                atlases[ad["Name"]] = ad
        self._materials = materials
        self._atlases = atlases
        return materials

    # ---- raw tables ------------------------------------------------------
    def material_name(self, section, icon_id):
        """The material name for `icon_id` in `section`, or None."""
        table = self._load_icons().get(section) or {}
        return table.get("%03d" % int(icon_id))

    def sections(self):
        return sorted(self._load_icons())

    def counts(self):
        icons = self._load_icons()
        return {name: len(icons[name]) for name in sorted(icons)}

    # ---- material -> picture --------------------------------------------
    def resolve(self, material_name):
        """Material name -> the texture that draws it.

        Returns a dict; `ok` says whether a picture was found, and `why` explains
        the failure rather than leaving a caller to print "None".
        """
        materials = self._load_materials()
        md = materials.get(material_name)
        if md is None:
            return {"ok": False, "material": material_name,
                    "why": "materials.json has no material named %r" % (material_name,)}
        atlas_name = md.get("AtlasRef")
        atlas = (self._atlases or {}).get(atlas_name)
        if atlas is None:
            return {"ok": False, "material": material_name,
                    "why": "material %r points at atlas %r, which is not in "
                           "materials.json" % (material_name, atlas_name)}
        texture = None
        for entry in atlas.get("Textures") or ():
            if entry.get("RefName") in (material_name, md.get("Name")):
                texture = entry
                break
        if texture is None:
            return {"ok": False, "material": material_name, "atlas": atlas_name,
                    "why": "atlas %r has no texture whose RefName is %r"
                           % (atlas_name, material_name)}
        rel = texture.get("FileName")
        path = os.path.join(self.widgetui, rel.replace("/", os.sep)) if rel else None
        return {"ok": bool(path and os.path.isfile(path)),
                "material": material_name,
                "atlas": atlas_name,
                "file": rel,
                "path": path,
                "uv": [float(texture.get("imageTLX") or 0.0),
                       float(texture.get("imageTLY") or 0.0),
                       float(texture.get("imageBRX") or 0.0),
                       float(texture.get("imageBRY") or 0.0)],
                "atlas_size": [atlas.get("MaxWidth"), atlas.get("MaxHeight")],
                "why": "" if path and os.path.isfile(path) else
                       "the texture file %r is not on disk" % (rel,)}

    def picture(self, section, icon_id):
        """Full chain for one id: section -> material -> file.

        The UV rect is reported but must NOT be used to crop the file: for all
        1,211 icon-atlas entries the loose file is already exactly the icon
        (uv * atlas size == file pixel size), so cropping it again would take a
        corner out of the middle of the picture.
        """
        if icon_id is None or int(icon_id) <= 0:
            return {"ok": False, "why": "this record has no icon id (icon_id is 0)"}
        name = self.material_name(section, icon_id)
        if not name:
            return {"ok": False, "section": section, "icon_id": int(icon_id),
                    "why": "icons.json section %r has no entry %03d"
                           % (section, int(icon_id))}
        got = self.resolve(name)
        got["section"] = section
        got["icon_id"] = int(icon_id)
        return got

    # ---- the section rule ------------------------------------------------
    def build_menu_names_it(self, icon_id, english_name):
        """Does a Buildings material name this unit?"""
        tokens = name_tokens(english_name)
        if not tokens:
            return False
        material = self.material_name(BUILDINGS, icon_id)
        return bool(material) and bool(name_tokens(material) & tokens)

    def unit_section(self, icon_id, made_by_builder=False, made_by_building=False,
                     english_name=None):
        """Pick "Units" or "Buildings" for a unit record.

        Returns `(section, witness)` where `witness` says WHY -- so a UI (and a
        test) can tell a measured choice from the documented default instead of
        treating all four cases as equally informed.
        """
        if made_by_builder:
            return BUILDINGS, "the Builder makes it, so it is a build-menu button"
        if made_by_building:
            return UNITS, "a building trains it, so it is a training-list portrait"
        if self.build_menu_names_it(icon_id, english_name):
            return BUILDINGS, "no producer, but a build-menu material carries its name"
        return UNITS, ("no producer and no matching build-menu material; the Units "
                       "table is the default")

    # ---- civilizations ---------------------------------------------------
    def emblem_path(self, civ_name):
        """Civilization -> the PNG file of its emblem, or None.

        `civ_name` may be the .dat spelling ("British"), the tech-tree stem
        ("BRITONS") or the icons.json stem ("britons"); the caller is expected to
        have normalised it, and `aoe2mod.game.civnames.chinese` knows how.

        The alias applies to BOTH directions, and both are needed: the table
        says `civ_emblems_inca` and the disk says `incas.png`, so a caller
        holding the tree stem ("INCAS" -> "incas") has to be mapped back to find
        the table row and then forward again to find the file.  Mapping only one
        way returned None for both aliased civilizations (measured).
        """
        stem = str(civ_name or "").strip().lower()
        if not stem:
            return None
        table = self._load_icons().get(CIV_EMBLEM) or {}
        values = set(table.values())
        # The caller may hold the DISK spelling ("incas", from the tree stem) or
        # the TABLE spelling ("inca").  Try the name as given, then its alias in
        # each direction, and keep whichever the table actually has.
        key_stem = None
        for cand in (stem, _EMBLEM_BACK.get(stem), _EMBLEM_ALIASES.get(stem)):
            if cand and ("civ_emblems_" + cand) in values:
                key_stem = cand
                break
        if key_stem is None:
            return None
        file_stem = _EMBLEM_ALIASES.get(key_stem, key_stem)
        path = os.path.join(self.game_root, "resources", "_common", "wpfg",
                            "resources", "civ_emblems", "%s.png" % file_stem)
        return path if os.path.isfile(path) else None
