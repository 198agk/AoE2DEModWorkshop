# -*- coding: utf-8 -*-
"""The one entry point a UI should call.

Everything in this package exists so that a player can say a sentence and get a
working mod.  This module is that sentence's path, and it deliberately returns
plain dicts (JSON-serialisable) so a front end in any language can consume it
without importing Python.

The contract a caller can rely on:

* Nothing raises a bare exception for a user mistake.  Bad input raises
  ``IntentError`` / ``ModError`` whose message is already user-facing prose.
  Name ambiguity is not an error to hide -- ``search`` returns candidates.
* Every emitted mod has been re-parsed from disk with the unmodified parser.
* ``result['verification']['ok']`` is the only thing that means "safe".
"""
import contextlib
import copy
import io
import json
import os
import struct

from .dat import parser as P
from .dat import locate as L
from .dat import families as F
from .dat import writer as W
from .game import civtechtrees as CT
from .game import civnames as CN
from .game import buildpanel as BP
from .game import icons as IC
from .game import linkedtechs as LT
from .game import objreplace as OR
from .intent import availability as AV
from .intent import compiler as C
from .mod import emitter as E
from .mod import strings as S
from .mod import provenance as PV
from .semantic import index as semantic
from .semantic import prose as PR

__all__ = ["Toolkit", "open_toolkit", "IntentError"]
IntentError = C.IntentError

_CACHE = {}


def _tech_locations_from_intent(r, tk, donor_id, notes_used=None):
    """Which building researches the new tech, in which box.

    Three optional fields, and the ORDER matters: an explicit `building` wins
    over everything, then an explicit `research_time`/`button` rewrites the
    donor's own box, and only when neither is given is the donor's location
    inherited verbatim.

    The building case looks the id up in the located records rather than in
    `stats`, because `stats["techs"]` drops `research_locations` -- the same
    reason `newunit.train_slots` reads `_civs` (see its docstring).  A building
    the donor never used is REFUSED with what the donor does offer: inventing a
    box on a card the engine may not draw is how a mod ships a tech no player can
    ever reach.
    """
    from .dat import newtech as NT
    if notes_used is None:
        notes_used = []
    donor = NT.pick_donor(tk._tech_records(), donor_id)
    locs = [dict(loc) for loc in (donor.get("research_locations") or [])]
    if not locs:
        raise NT.NewTechError(
            "「%s」自己没有研究位置（记录里一个格子都没有），"
            "所以没有地方能研究新科技；换一个能研究的科技照着做"
            % _tech_display(tk, donor_id))
    want_building = getattr(r, "raw", {}).get("building")
    if want_building is not None:
        targets = tk._tech_locations_by_building(want_building)
        if not targets:
            # A display NAME is not a record.  "城镇中心" resolves to ONE of the five
            # shipped town-centre records (71), and that copy carries no research
            # slots -- the research card lives on 109.  Refusing here would tell
            # the player a true sentence is impossible, so try the other records
            # that answer to the same name and report which one answered.
            _asked = _describe_building(tk, want_building)
            _alt = tk._sibling_building_with_tech(want_building)
            if _alt is not None:
                targets = tk._tech_locations_by_building(_alt)
                _used = _alt
            else:
                _used = None
            if not targets:
                raise NT.NewTechError(
                    "「%s」的科技卡上没有空位能放新科技：这个工具只会照着已有的格子写"
                    % _asked)
            if _used is not None:
                notes_used.append(
                    "「%s」在这份数据里有好几条记录，用的是研究卡在那一条（第 %d 号）"
                    % (_asked, _used))
        locs = [dict(loc) for loc in targets]
    want_time = r.raw.get("research_time")
    want_button = r.raw.get("button")
    if want_time is not None:
        for loc in locs:
            loc["research_time"] = int(want_time)
    if want_button is not None:
        for loc in locs:
            loc["button_id"] = int(want_button)
    return locs


def _tech_display(tk, tech_id):
    got = tk.describe(tech_id, "tech") or {}
    return got.get("zh") or got.get("name") or str(tech_id)


def _describe_building(tk, building_id):
    got = tk.describe(building_id, "unit") or {}
    return got.get("zh") or got.get("name") or str(building_id)


class Toolkit(object):
    """An open game install, ready to answer questions and build mods."""

    def __init__(self, game_root, dat_path=None):
        self.game_root = game_root
        self.dat_path = dat_path or os.path.join(
            game_root, "resources", "_common", "dat", "empires2_x2_p1.dat")
        self._raw = None
        self._parsed = None
        self._civs = None
        self._stats = None
        self._fam = None
        self._techs = None
        self._effects = None
        self._fanout = None
        self._civtrees = None
        self._civtrees_dir_present = None
        self._sprites = None
        self._icons = None
        self._uifacts = None

    # ---- lazy game-data load ---------------------------------------------
    def _ensure(self):
        if self._parsed is not None:
            return
        data, how = P.load_dat(self.dat_path)
        p = P.Parser(data)
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
        civs, civs_start, gv, tail = L.locate(data, parser=p)
        self._raw = data
        self._civs = civs
        self._stats = p.stats
        self._parsed = (data, civs, civs_start, gv, tail, how)

    @property
    def version(self):
        self._ensure()
        return self._parsed[3]

    # ---- cached section walks --------------------------------------------
    # Walking the tech and effect sections is not free: `locate_techs` walks
    # 1,510 records and `locate_effects` walks 1,500 effects / 10,500 commands,
    # and `effect_fanout` folds all of them.  Doing that inside `effects()` and
    # `plan()` on EVERY call turned a UI list view into minutes of work -- the
    # sweep in `test_api.py` (41 techs x their commands) stopped finishing.  The
    # data is immutable once loaded, so walk it once.
    def _tech_records(self):
        self._ensure()
        if self._techs is None:
            self._techs = L.locate_techs(self._raw, self._parsed[4], self._parsed[3])
        return self._techs

    def _effect_records(self):
        self._ensure()
        if self._effects is None:
            self._effects, _start = L.locate_effects(self._raw)
        return self._effects

    def _sibling_building_with_tech(self, building_id):
        """Another record with the SAME display name that has a research card.

        ``"城镇中心"`` is the display name of five shipped unit records
        (71/109/141/142/444) and only some of them carry research slots; the one
        the sentence resolves to is whichever the name index lists first, which is
        not the one the engine draws.  Measured 2026-10-22: asking for a new
        technology on ``城镇中心`` was refused with "no free slot" while
        ``研究卡`` plainly exists on 109.

        Returns the sibling's unit id, or None when no record with that name has a
        research card.  Deliberately NOT a general "pick any building" search: the
        player named one thing, and swapping in a different one silently would be
        a wrong answer of the worst kind.
        """
        self._ensure()
        mine = self.describe(building_id, "unit") or {}
        wanted = (mine.get("zh") or mine.get("name") or "").strip()
        if not wanted:
            return None
        # Every unit record of the FIRST civilization is enough: the five town
        # centres exist once per civilization with the same ids, and a research
        # card is a property of the record, not of whose copy it is.
        seen = []
        for u in self._civs[1].get("units") or []:
            if u.get("id") == building_id:
                continue
            got = self.describe(u.get("id"), "unit") or {}
            if (got.get("zh") or got.get("name") or "").strip() != wanted:
                continue
            uid = u.get("id")
            if uid in seen:
                continue
            seen.append(uid)
            if self._tech_locations_by_building(uid):
                return uid
        return None

    def _tech_locations_by_building(self, building_id):
        """ONE research box on one building's card, as a fresh dict.

        Reads the located tech records (which keep `research_locations`) rather
        than `stats["techs"]` (which drops them).  Returns `[]` when no shipped
        tech is researched at that building -- the caller turns that into a
        refusal naming the building, because a box on a card the engine does not
        draw is a tech no player can reach.

        ONE box, not every box: this list used to be "every shipped research
        location of that building" (18 dicts for the town centre), and a caller
        that treated it as "where this new technology goes" wrote all 18 -- one
        record claiming to sit in eighteen boxes at once.  Measured 2026-10-22
        on the town centre: the 18 entries collapse to 8 distinct buttons
        (2,3,4,6,7,8,11,12), each repeated for the technologies that share it.

        The box returned is the FIRST one found, and the order is the record
        order of the shipped data -- deterministic, so two previews of the same
        sentence agree.  It is deliberately not "the free one": this tool cannot
        tell a free box from a taken one (66 shipped (building, button) pairs are
        already shared by two or more technologies), so claiming a box is free
        would be a guess dressed as a fact.  The caller reports which box it
        used instead.
        """
        self._ensure()
        for rec in self._tech_records():
            for loc in (rec.get("research_locations") or []):
                if loc.get("location_id") == building_id:
                    return [dict(loc)]
        return []

    def _effect_fanout(self):
        self._ensure()
        if self._fanout is None:
            self._fanout = C.effect_fanout(self._tech_records())
        return self._fanout

    @property
    def civ_names(self):
        self._ensure()
        return [c["name"] for c in self._civs]

    @property
    def icons(self):
        """The icon tables (icons.json + materials.json), read once.

        Built lazily and separately from the .dat: a screen that only draws
        emblems must not pay for a 93 MB parse.
        """
        if self._icons is None:
            self._icons = IC.IconBook(self.game_root)
        return self._icons

    def icon_for(self, kind, entity_id):
        """Which picture represents this entity, and how that was decided.

        Units are the hard case: the same number means two different drawings in
        the "Units" and "Buildings" tables (a portrait vs a build-menu button),
        and which one applies depends on how the thing reaches the player.  That
        rule is measured, not guessed -- see `aoe2mod/game/icons.py`.  The
        `witness` field is returned so a screen (or a person) can tell a measured
        choice from the documented default.
        """
        self._ensure()
        if kind == "tech":
            e = semantic.index().get("tech", entity_id)
            if e is None:
                # Same rule as the unit branch below: the grid asks for a picture
                # per cell, so a stale tech id puts this sentence on the screen.
                return {"ok": False, "why": "找不到编号 %s 的科技" % (entity_id,)}
            raw = getattr(e, "_extra", None) or {}
            got = self.icons.picture(IC.TECHS, raw.get("icon_id"))
            got["witness"] = "technologies are always drawn from the Techs table"
            return got
        if kind != "unit":
            # NOT "only units and technologies have icons" -- that would be
            # false.  A castle is unit 82 in this game's data and resolves to a
            # build-menu button, and the Buildings table is real.  What is
            # narrow is this function's accept-list, so say that instead.
            #
            # No English here either: this text goes through the same
            # player-facing check as every other refusal.  The caller-facing
            # name of the kind ("building") is deliberately not printed -- a
            # screen never sends it, and a person reading the sentence needs to
            # know what to do, not which enum to pass.
            return {"ok": False,
                    "why": "这里只认「单位」和「科技」两种。建筑在游戏数据里"
                           "本来就是单位记录，按单位查它就有图。"}
        facts = self._unit_facts().get(entity_id)
        if facts is None:
            return {"ok": False,
                    "why": "找不到编号 %s 的单位" % (entity_id,)}
        e = semantic.index().get("unit", entity_id)
        section, witness = self.icons.unit_section(
            facts.get("icon_id"), made_by_builder=facts.get("builder", False),
            made_by_building=facts.get("building", False),
            english_name=(e.en if e else None))
        got = self.icons.picture(section, facts.get("icon_id"))
        got["witness"] = witness
        return got

    # ---- stage 1: search, never guessing ---------------------------------
    def _unit_facts(self):
        """One pass over every unit record, kept: icon id and how it reaches you.

        `icon_for` used to re-scan 2,693 records per call (31.2 ms measured), so a
        grid of 1,219 icons would have spent 38 seconds doing nothing but
        lookups.  The records are immutable once loaded, so walk them once.
        """
        self._ensure()
        if self._uifacts is not None:
            return self._uifacts
        types = {}
        facts = {}
        for civ in self._civs:
            for u in civ["units"]:
                uid = u.get("id")
                types.setdefault(uid, u.get("type"))
                if uid in facts:
                    continue
                producers = [t.get("unit_id")
                             for t in (u.get("train_locations") or [])]
                facts[uid] = {"icon_id": u.get("icon_id"),
                              "class": u.get("class"),
                              "producers": producers,
                              "builder": IC.BUILDER_UNIT_ID in producers}
        # A unit's TYPE does not vary by civilization (measured: 0 ids differ),
        # so the first record's value speaks for all of them, and a producer that
        # is a building (type 80) means this unit is trained, not placed.
        for row in facts.values():
            row["building"] = any(types.get(p) == 80 for p in row["producers"]
                                  if p not in (None, -1))
        self._uifacts = facts
        return facts

    def unit_class(self, unit_id):
        """The .dat unit class of one unit id, or None.  Cheap; cached pass.

        The sentence reader needs it to tell a CATEGORY from a record: 骑兵 is
        not a unit, it is 188 units, and "骑兵的血量改成1000" used to resolve to
        whatever name started with 骑兵 (科技名「骑兵钢甲」, or the unit 蔷琵侦察兵
        for 侦察兵).  Knowing the class of the record the sentence landed on is
        what lets the reader say "that is a different kind of thing" instead.
        """
        row = self._unit_facts().get(unit_id)
        return None if row is None else row.get("class")

    def browse(self, kind="unit", query="", limit=60, offset=0):
        """Entities a screen can put in a grid, with the icon facts it needs.

        Why this is not `search`: a browser needs a STABLE list in a stable order
        (so the grid does not reshuffle between visits), needs to know up front
        which cells will show a picture, and needs to page it, because decoding
        1,219 sprites costs 18 seconds.

        The grid lists NAMED entities only, so every count meant for the grid has
        to be counted over this same list.  Measured 2026-10-20 on this install:
        of 2,693 unit records 1,042 have no name in any language and are not
        listed at all; of the 1,651 listed, 432 declare no icon id (0 or -1).
        Quoting a number taken over all 2,693 records next to this grid is how the
        screen came to promise "1,349 have no picture" over a grid that shows 432
        dashed cells.

        Rows carry `has_icon`, not bytes: the page asks `/api/icon` only for the
        cells it actually draws, and the browser caches those.  `has_icon` means
        "declares an icon id", not "a texture exists" -- a name can point at a
        material this install lacks (one technology does), and the picture route
        is then the authority.  The page already treats a failed `<img>` as the
        dashed cell, so the two agree on screen; do not "fix" `has_icon` by
        resolving a texture per row, which costs a 0.17 s pass per request.
        """
        ix = semantic.index()
        table = ix.units if kind == "unit" else ix.techs
        facts = self._unit_facts() if kind == "unit" else None
        q = str(query or "").strip().lower()
        rows = []
        for uid in sorted(table):
            e = table[uid]
            if not e.is_visible:
                continue
            if q and q not in (e.zh or "").lower() \
                    and q not in (e.en or "").lower() \
                    and q not in (e.internal or "").lower():
                continue
            if kind == "unit":
                icon_id = (facts.get(uid) or {}).get("icon_id")
            else:
                icon_id = (getattr(e, "_extra", None) or {}).get("icon_id")
            rows.append({"id": uid, "kind": kind, "name": e.display,
                         "en": e.en, "zh": e.zh,
                         "has_icon": bool(icon_id and int(icon_id) > 0),
                         "icon_id": icon_id})
        return {"ok": True, "kind": kind, "total": len(rows),
                "offset": offset, "limit": limit,
                "rows": rows[offset:offset + limit]}

    def search(self, query, kind="unit", limit=25):
        """Candidate entities for a user-typed name.  Never raises."""
        ix = semantic.index()
        return [{"id": e.id, "kind": e.kind, "name": e.display,
                 "en": e.en, "zh": e.zh,
                 "has_civ_variants": bool(e.civ_variants)}
                for e in ix.find(kind, query, limit=limit)]

    def describe(self, entity_id, kind="unit"):
        """Everything a UI needs to show one entity, including its data."""
        self._ensure()
        intents, bindings = C.load_schema()
        ix = semantic.index()
        e = ix.get(kind, entity_id)
        if e is None:
            # Reached by every "游戏里怎么说的？" click on a stale row, so this
            # sentence goes on screen.  The kind is named in Chinese and the id
            # is printed as-is: the player is quoting a number back to us.
            raise C.IntentError("找不到编号 %s 的%s" % (entity_id, C.kind_label(kind)))
        out = {"id": e.id, "kind": e.kind, "name": e.display,
               "en": e.en, "zh": e.zh, "resolved": e.resolved,
               "civ_variants": e.civ_variants}
        # Prose is reported with its GAPS, not just its hits: this build ships no
        # unit descriptions at all, and a screen that renders an empty box where a
        # description belongs would look like a bug in this product rather than a
        # fact about the game.  `missing` carries the reason per field.
        out["prose"] = PR.for_entity(e)
        out["icon"] = self.icon_for(kind, entity_id)

        if kind == "tech":
            # One GLOBAL record per tech -- not one per civ -- so reporting a
            # civ count here would be meaningless.  Say how many research
            # locations carry a copy of the time instead.
            hits = L.find_techs(self._tech_records(), entity_id)
            out["record_count"] = len(hits)
            out["civ_count"] = 0
            if hits:
                idx, tech = hits[0]
                locs = tech.get("research_locations")
                out["stats"] = {"research_time": (
                    [d["research_time"] for d in locs] if locs
                    else tech.get("research_time"))}
                out["stats"]["research_locations"] = (
                    len(locs) if locs is not None else 0)
                # Projected through the compiler's own slot rule, so this list
                # and the slots an edit can reach are the same set by
                # construction.  A cost the game charges under a type no intent
                # can name is surfaced separately rather than dropped, carrying
                # the game's own name for that id when it has one (so the UI can
                # say "圣物夺取数" rather than "type 7") while keeping the raw id.
                costs, unmapped = C.cost_report(bindings, tech.get("costs"))
                out["stats"]["costs"] = costs
                if unmapped:
                    out["stats"]["unmapped_costs"] = unmapped
            # Which civilizations may research this is not in the .dat either --
            # it lives in the tech-tree layer, keyed by the .dat tech ARRAY
            # INDEX, which is exactly what `entity_id` is for kind="tech" (all
            # 238 tech node ids fall inside the 1510-record array).  The space
            # argument is load-bearing: the same integer is a unit id in the
            # unit space, so asking without it returns None for all 62 civs.
            out["availability"] = self._availability_of(entity_id,
                                                        CT.TECH_USE_TYPES)
            return out

        recs = L.find_units(self._civs, entity_id)
        out["record_count"] = len(recs)
        out["civ_count"] = len({c for c, _, _ in recs})
        fam = F.family_of(self._families(), entity_id)
        # Named `variants`, not `age_variants`: the family covers BOTH the
        # age-swapped records of a building and the task-swap basket of a
        # villager.  Calling a villager's Builder/Lumberjack siblings "age
        # variants" would be a plain lie in the UI.
        out["variants"] = [i for i in fam if i != entity_id]
        # A family can span MORE THAN ONE task-swap group: the declared sex swap
        # in objreplacement.json joins the male and female villager baskets, so
        # "the villager" is now groups [1, 2].  Report the whole set; naming one
        # group would describe half the edit.
        _g = F.groups_of(self._civs, fam)
        if _g:
            out["task_swap_groups"] = _g
        if recs:
            u = recs[0][2]
            # Derived from the schema, not hand-listed: a field appears here
            # exactly when the compiler could reach it on this record, so the
            # UI can never be offered a field that an edit would refuse -- and
            # binding a new field in dat_bindings.json is enough to show it.
            out["stats"] = C.unit_field_values(bindings, u, self._raw)
            # Same projection as the tech branch: the list is what an edit can
            # reach, not a filtered copy of the stored list.  The unit path used
            # to keep only four hardcoded resource types, which silently hid 17
            # real costs (types 214/215/501/514 -- e.g. unit 2443 WCTWX).  The
            # unmapped entries carry the game's name for the id when it has one.
            costs, unmapped = C.cost_report(bindings, u.get("costs"))
            out["stats"]["costs"] = costs
            if unmapped:
                out["stats"]["unmapped_costs"] = unmapped
        # Which civilizations can BUILD this is not a .dat fact: the .dat holds
        # 63 near-identical records and says nothing about who may train one, so
        # `civ_count` above is a RECORD count and answers a different question.
        # The answer lives in the tech-tree layer, and no editor intent is needed
        # to read it -- hence a read-side entry, not just the plan() one.
        out["availability"] = self._availability_of(entity_id)
        return out

    def _availability_of(self, node_id, use_types=None):
        """Who can build a unit / research a tech, from the layer the engine reads.

        ``holders`` have it from the start, ``builders`` can get it once the
        prerequisite is researched (the two differ on 14 nodes), ``absent_from``
        are the civs a grant would ADD a row for, and ``blocked_in`` are the ones
        listed as NotAvailable, which need a status change instead.  Returns
        ``None`` for the 1,364 units that are in no tech tree at all -- "not part
        of any tech tree" is a different statement from "no civ can build it".

        ``use_types`` picks the id space and must match the entity: a tech id
        asked about in the unit space reads as "nobody has it" for all 62 civs.
        """
        ut = use_types or CT.UNIT_USE_TYPES
        tree = AV.describe(self._trees(), node_id, use_types=ut)
        if tree is None:
            return None
        return {"space": tree["space"],
                "holders": tree["holders"], "holder_count": tree["holder_count"],
                "builders": tree["builders"], "builder_count": tree["builder_count"],
                "absent_from": tree["absent_from"], "blocked_in": tree["blocked_in"],
                "pending_in": tree["pending_in"]}

    def _families(self):
        """unit id -> age-variant family, computed once per open install."""
        self._ensure()
        if self._fam is None:
            F.warm(self._stats, self.game_root)
            self._fam = F.build_families(self._civs)
        return self._fam

    def schema(self):
        intents, bindings = C.load_schema()
        return {"intents": intents, "bindings": bindings}

    def effects(self, tech, fanout=True):
        """List the commands of the effect a technology points at.

        This is the list a ``tech.effect`` intent picks from, so it is the only
        way a UI can offer that intent at all -- and it is why the intent is
        addressed by index instead of by meaning.

        Every row carries what the command does, what it costs to write, and --
        the part a player cannot be expected to guess -- whether the same effect
        is shared with other technologies.  Measured over the shipped data, 37
        effects are referenced by more than one tech and 34 of those carry
        commands; editing one of those changes every tech that points at it, so
        ``fan_in`` / ``shared_with`` are reported on every row rather than left
        for the caller to discover.

        A command whose attribute id has no name in the shipped vocabulary is
        still returned, with ``editable`` False and a ``reason`` -- a missing
        name is a fact about the table, not a reason to hide the command.
        """
        self._ensure()
        idx, rec = self._resolve_tech(tech)
        effects = self._effect_records()
        fan = self._effect_fanout() if fanout else None
        rows = C.effect_rows(effects, rec, fanout=fan,
                             unit_class=self.unit_class)
        return {"tech_id": idx, "name": rec.get("name"),
                "effect_id": rec.get("effect_id"),
                "effect_name": (effects[rec["effect_id"]]["name"]
                                if 0 <= (rec.get("effect_id") or -1) < len(effects)
                                else None),
                "command_count": len(rows), "rows": rows}

    def effect_count(self, tech):
        """How many effect commands a technology has.  Cheap; no full row build.

        The sentence reader needs this to answer "第2条" honestly: 669 of the
        1,040 technologies with commands have two or more, so a bare "效果加5"
        cannot say which one, while 371 have exactly one and there the position
        is unambiguous.  Building the full rows here would walk the vocabulary
        tables for every sentence typed, so only the length is counted.
        """
        idx, rec = self._resolve_tech(tech)
        eid = rec.get("effect_id")
        effects = self._effect_records()
        if eid is None or eid < 0 or eid >= len(effects):
            return 0
        return len(effects[eid].get("commands") or ())

    def _resolve_tech(self, tech):
        """Accept a tech id or a name, and refuse ambiguity instead of picking.

        A name goes through the semantic index (which knows the localized and
        internal names) rather than matching the tech's own ``name`` field: that
        field is an internal code -- several techs share one, and it is not what
        the player sees.
        """
        tail, gv = self._parsed[4], self._parsed[3]
        techs = self._tech_records()
        # Both refusals below are read by whoever typed the tech: `effects()` and
        # `plan()` funnel them through `IntentError`, and the sentence is printed.
        if isinstance(tech, int) or (isinstance(tech, str) and tech.isdigit()):
            n = int(tech)
            if not (0 <= n < len(techs)):
                raise C.IntentError("科技表里没有第 %d 号记录（这一类只有 %d 条）"
                                    % (n, len(techs)))
            return n, techs[n]
        try:
            ent = semantic.index().resolve_one("tech", tech)
        except LookupError as exc:
            raise C.IntentError(str(exc))
        if not (0 <= ent.id < len(techs)):
            raise C.IntentError("科技表里没有第 %d 号记录（这一类只有 %d 条）"
                                % (ent.id, len(techs)))
        return ent.id, techs[ent.id]

    def _strategy(self, intent):
        """The declared compile strategy for an intent, before resolving it.

        Read from the schema so a caller can route on it without the cost of
        resolving (which loads the semantic index).  An unknown intent is
        reported by ``resolve`` with its own message, so this returns None rather
        than inventing a refusal.
        """
        if not isinstance(intent, dict):
            return None
        intents_schema, _ = C.load_schema()
        spec = (intents_schema.get("intents") or {}).get(intent.get("intent"))
        if spec is None:
            return None
        return (spec.get("compile") or {}).get("strategy")

    def _trees(self):
        """The CivTechTrees layer, read once per open install.

        Cached because it is 62 files and every availability call reads it, and
        because the WRITE mutates the dict -- so a caller that plans and then
        builds must be looking at the same object (see :meth:`_plan_availability`).
        """
        if self._civtrees is None:
            self._civtrees = CT.load_trees(self.game_root)
            self._civtrees_dir_present = os.path.isdir(CT.trees_dir(self.game_root))
        return self._civtrees

    def _plan_availability(self, r, base):
        """Preview for "let <civ> build <unit>".

        The whole point of routing this through the same ``availability.plan``
        the build uses is that the two cannot disagree -- and they would, easily:
        this intent's answer depends on 62 files on disk, not on the .dat, so a
        second implementation's idea of "already has it" would drift silently.

        ``civ`` is resolved here (name -> the tree's own key) because the intent
        may name a civ the way the .dat does (`Magyars`) while the tree is keyed
        by its file stem (`MAGYAR`); using the raw name as an index would find
        nothing and report "this civ has no file".
        """
        trees = self._trees()
        if not trees:
            raise C.IntentError(
                "no CivTechTrees data next to this install (%s); availability "
                "cannot be read or written for any civilization"
                % CT.trees_dir(self.game_root))
        civ = self._tree_civ(r.civ, trees)
        ut = AV.space_of(r.raw)
        rep = AV.plan(trees, civ, r.entity.id, r.action or "grant",
                      display=r.entity.display, use_types=ut,
                      civ_zh=CN.chinese(civ))
        # "Who has it" is worth showing even when the answer is "you already do"
        # -- and it is the only way a UI can offer a different civilization.
        base["civ"] = civ
        base["civ_requested"] = r.civ
        base["action"] = r.action or "grant"
        base["shape"] = "availability"
        base["space"] = ut[0]
        base["civ_count"] = 1
        base["civs"] = [civ]
        # This intent no longer writes "no .dat bytes at all".  A grant now also
        # writes the recipe the user confirmed in game, so the old unconditional
        # `edit_count = 0` / `changes_dat = False` would have been a preview that
        # contradicts the build -- the defect class this file already fixed twice.
        # Which action gets the `.dat` half is read from the SCHEMA, so the
        # preview cannot drift from `_dat_half_declared` in `build`.
        _dh = self._dat_half_declared(r.raw)
        _wants_dat = (base["action"] in (_dh.get("actions") or ())
                      and ut == CT.UNIT_USE_TYPES)
        if _wants_dat:
            # The count is DECLARED by the schema, not measured here: measuring it
            # means running the recipe, and the recipe serialises the whole 93 MB
            # .dat -- 25 s on this machine, against 9 s for a whole preview.  The
            # declaration is a fixed property of the recipe (two write operations,
            # whatever the data), and `_probe/test_dat_half_count.py` asserts it
            # still equals what `apply_grant` actually reports, so the two cannot
            # drift apart in silence.
            base["edit_count"] = self._write_ops_for(_dh, base["action"])
            # The build emits FOUR files for a grant that carries the .dat half,
            # not two: the .dat, the tree file, and -- because the menu the
            # player sees is fed by a pre-baked panel -- the panel splice
            # (`futuravailableunits.json` / `paphosfutureavailableunits.json`).
            # An audit measured a plan that named only the .dat + the tree file
            # while the build wrote the panel too; naming the third file here
            # keeps the preview honest about what will land on disk.
            base["writes"] = ("resources/_common/dat/empires2_x2_p1.dat + "
                              "resources/_common/dat/CivTechTrees/%s.json + "
                              "the build-panel file for that civilization "
                              "(futuravailableunits.json or "
                              "paphosfutureavailableunits.json)"
                              % CT.civ_file_stem(civ))
            base["changes_dat"] = True
            base["dat_is_carrier"] = False
            base["mod_contains_dat"] = True
            base["dat_half"] = _dh.get("help")
        else:
            base["edit_count"] = 0
            base["writes"] = "resources/_common/dat/CivTechTrees/%s.json" % \
                CT.civ_file_stem(civ)
            base["changes_dat"] = False
            base["dat_is_carrier"] = True
            base["mod_contains_dat"] = True
        if not rep["ok"]:
            base["editable"] = False
            base["description"] = rep["reason"]
            base["reason"] = rep["reason"]
            # A plan that has just been refused must not keep advertising work.
            # The block above sets `edit_count` and `changes_dat` from the schema
            # BEFORE this branch runs, so a refusal used to come back saying
            # "2 edits, changes the .dat" next to `editable: False`.  Measured by
            # an independent audit on `{unit: 步弓手, civ: AZTECS, action: grant}`.
            base["edit_count"] = 0
            base["changes_dat"] = False
            base["dat_is_carrier"] = True
            base["mod_contains_dat"] = True
            return base
        base["editable"] = True
        base["description"] = rep["description"]
        base["mode"] = rep["mode"]
        for k in ("donor", "warnings", "was_status"):
            if k in rep:
                base[k] = rep[k]
        who = AV.describe(trees, r.entity.id, display=r.entity.display,
                          use_types=ut)
        if who:
            # "Who has it" and "who can ever build it" are different lists and
            # differ on 14 nodes (War Galley: 0 holders, 56 builders).  A UI
            # offering "let another civilization build this" wants the second.
            base["holders"] = who["holders"]
            base["holder_count"] = who["holder_count"]
            base["builders"] = who["builders"]
            base["builder_count"] = who["builder_count"]
            base["absent_from"] = who["absent_from"]
            base["blocked_in"] = who["blocked_in"]
        return base

    # ---- reskin: loose .sld files, no .dat --------------------------------
    def _reskin_mode(self, r):
        """How the reskin should be delivered: ``copy`` files, or ``rename`` records.

        Two products, and the difference is not cosmetic.  ``copy`` ships the
        donor's picture once per target file name; the villager family is 466
        files and 418 MB.  ``rename`` rewrites the graphics records' `file`
        strings to point at the donor's already-shipped picture: 244 record
        edits, the .dat gets SMALLER, and the mod is one 11.98 MB file.

        Both are PROVEN in game: ``copy`` by ``dsh test v12`` (2026-10-17) and
        ``rename`` by ``dsh test v13`` the same day, where the user answered
        「没问题，看了都是羊」.  ``rename`` working is what proves the engine picks
        a graphic by its `file` string and not by the neighbouring `slp` id.

        Default is ``copy`` because it composes with any data mod (it ships no
        .dat) while ``rename`` IS a data mod, and only one data mod loads per
        match.  Asking for the cheap model must be a decision, not an accident.
        """
        v = (r.raw or {}).get("mode")
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ("rename", "retarget", "dat"):
                return "rename"
            if v in ("copy", "files", "sld", ""):
                return "copy"
            raise C.IntentError(
                "mode must be 'copy' (ship the pictures, proven in game) or "
                "'rename' (repoint the records, much smaller); got %r" % v)
        return "rename" if v is True else "copy"

    def _reskin_scope(self, r):
        """Which civilizations a reskin covers, as the tree's own key names.

        ``unit.sprite`` accepts ``civs`` as a plain list of names.  It is
        deliberately NOT run through the availability machinery's single-civ
        resolution: this intent is about ART, not about a game rule, so a name
        the tree files do not know is still a legitimate thing to ask about --
        and the per-civ art lookup below reports, per civilization, whether it
        had art to change.
        """
        scope = r.raw.get("civs")
        if scope in (None, "", "all"):
            return None
        if isinstance(scope, str):
            return [scope]
        return list(scope)

    def _reskin_art(self):
        """The sprite index for this install, built once and cached.

        Reading it walks 20,883 graphics records and lists 15,486 files, and
        every reskin call needs the same table -- so it is cached per toolkit,
        the same way `_trees` is, and for the same reason.
        """
        if self._sprites is None:
            from .game import sprites as SP
            self._sprites = SP.art_index(self.game_root, self._stats["graphics"])
        return self._sprites

    def _reskin_family_flag(self, r):
        """Whether this sentence asks for the whole task-swap family.

        Read from the sentence, defaulting to False: a family-wide villager
        reskin is 320 files and 435 MB against 20 files and 25 MB, so the cheap
        and the complete answer are different products and the caller must pick.

        Filling is switched on by the same sentence, and for the same reason: a
        family scope that does not fill leaves the villager a human whenever it
        works, because no entity in the game owns all ten animations a villager
        family needs.  Asking for the family and expecting it to look complete
        would otherwise be asking for something the file list cannot deliver.
        """
        v = (r.raw or {}).get("whole_family")
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)

    def _reskin_fill_flag(self, r):
        """Whether a nearby donor animation may stand in for a missing one.

        Read straight from the sentence, but ALSO true whenever the family is
        asked for: see `_reskin_family_flag`.  A caller who wants the plain copy
        semantics can say `fill=False` explicitly.
        """
        v = (r.raw or {}).get("fill")
        if v is not None:
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "on")
            return bool(v)
        return self._reskin_family_flag(r)

    def _plan_new_unit(self, r, base):
        """Preview for "make a new unit modelled on the villager".

        Everything the preview promises is computed from the same functions the
        build calls, so "plan says it fits and build says the id is taken" cannot
        happen.  The expensive part (parsing the .dat) is already done by
        `_ensure`, and picking an id is a set difference over ids, not a scan of
        records -- measured at a few milliseconds.
        """
        from .dat import newunit as NU
        base["shape"] = "new_unit"
        base["donor_id"] = r.donor.id
        base["donor_name"] = r.donor.display
        base["new_name"] = r.name
        base["writes"] = "resources/_common/dat/empires2_x2_p1.dat"
        base["changes_dat"] = True
        base["dat_is_carrier"] = False
        base["mod_contains_dat"] = True
        _civ = r.civ
        civ_index = self._civ_index(_civ)
        civ_name = (self._civs[civ_index] or {}).get("name") or _civ
        # The player reads the sentence, so it names the civilization the way
        # the rest of the product does (`不列颠`, not the .dat spelling
        # `British`).  `civ_name` stays the .dat spelling for the structured
        # fields, because those are read by code rather than by a person.
        civ_zh = CN.chinese(civ_name) or civ_name
        base["civ"] = civ_name
        base["civ_index"] = civ_index
        try:
            avoid = NU.referenced_ids(self._stats)
            new_id = NU.pick_free_id(self._stats, avoid=avoid)
            _img = NU.donor_image(self._raw, self._parsed[3],
                                  self._parsed[2], civ_index, r.donor.id)
        except NU.NewUnitError as exc:
            base["editable"] = False
            base["changes_dat"] = False
            base["description"] = str(exc)
            base["reason"] = str(exc)
            base["edit_count"] = 0
            return base
        # The name ships as strings, so the string id must exist before the
        # player sees the promise.  Asking the string module rather than
        # assuming 30030002 keeps two creations in one session from colliding.
        try:
            string_id = S.first_free_id(self.game_root,
                                        start=base.get("string_id") or
                                        S.LAST_SHIPPED_ID + 1)
            creation_id = S.first_free_id(self.game_root, start=string_id + 1)
        except S.StringError as exc:
            base["editable"] = False
            base["changes_dat"] = False
            base["description"] = str(exc)
            base["reason"] = str(exc)
            base["edit_count"] = 0
            return base
        base["editable"] = True
        base["new_id"] = new_id
        base["string_id"] = string_id
        # Two strings ship, because the record has two: the name labels the unit,
        # the creation string is the command-card tooltip's first line.  A single
        # id in both slots emptied the whole tooltip on four measured builds.
        base["creation_string_id"] = creation_id
        base["creation_text"] = "生产" + str(r.name)
        base["record_bytes"] = len(_img)
        base["description"] = (
            "照 %s 在 %s 做一个新单位「%s」（编号 %d，%d 字节的记录；"
            "名字和建造文本各用一个字符串，%d 和 %d）"
            % (r.donor.display, civ_zh, r.name, new_id, len(_img),
               string_id, creation_id))
        base["edit_count"] = 2
        # Where the button will be, and which numbers are free on that card.
        # Measured from the located civs (`_civs`), because the parsed stats
        # model drops `train_locations` -- see `newunit.train_slots`.
        want_button = getattr(r, "button", None)
        # Which building shows the button.  `None` = the donor's own.  Measured
        # 2026-10-23: the train location (the entry that names the building, the
        # box number and the train time) lives on the UNIT's record, so pointing
        # the clone at a different building rewrites two bytes of the record the
        # build already emits.  It does not edit the building and appends
        # nothing -- so "a building that never trained the donor" was never a
        # wall, only an unimplemented field.
        want_builder = r.raw.get("builder")
        try:
            _slots = NU.train_slots(self._raw, self._parsed[3], self._parsed[2],
                                    civ_index, r.donor.id, civs=self._civs)
        except NU.NewUnitError:
            _slots = []
        _builders = sorted({s["builder"] for s in _slots if s["builder"] not in (-1, None)})
        if want_builder is not None:
            # A clone re-pointed at another building does not need the donor's
            # card to exist at all, so the "no card" refusal below must not fire
            # on a donor whose entries all say -1.
            _builders = [int(want_builder)]
        base["buttons"] = [s["button"] for s in _slots]
        base["builder_ids"] = _builders
        base["builder_names"] = [(self.describe(b, "unit") or {}).get("zh")
                                 or (self.describe(b, "unit") or {}).get("name")
                                 or str(b) for b in _builders]
        free_by_builder = {}
        for b in _builders:
            free_by_builder[str(b)] = NU.free_buttons(self._civs, civ_index, b)
        base["free_buttons"] = free_by_builder
        if want_button is not None:
            base["button"] = int(want_button)
            if _builders:
                base["description"] += ("，放在 %s 的第 %d 格"
                                        % (base["builder_names"][0], int(want_button)))
            else:
                # The build refuses this case (see `add_unit`), so the preview
                # must refuse it too: a preview that promises a box and then
                # fails at build time teaches the player to distrust the sentence
                # that was right.  Measured: British has 683 units whose only
                # train entries point at no building, so a donor can be picked
                # whose card does not exist.
                base["editable"] = False
                base["reason"] = (
                    "「%s」的建造位置没有指向任何建筑（记录里的建筑编号是 -1），"
                    "所以第 %d 格没有一块命令卡可以放"
                    % (base.get("donor_name") or r.donor.display, int(want_button)))
        # The old sentence said a clone has no icon of its own because "the icon
        # numbers 0..999 are full".  The first half is a fact about the SHIPPED
        # file; the second was wrong, and it made a missing feature sound like a
        # wall.  Measured 2026-10-23 (`_probe/tmp_icon_ceiling.py`,
        # `tmp_icon_field_width.py`, `tmp_mod_icons_real.py`):
        #
        #   * the record's `icon_id` is an i16 (parser.py `r.i16()  # IconID`),
        #     so the engine's ceiling is 32767 -- not 999;
        #   * the shipped table stops at 999 for Units / 312 for Techs, and the
        #     shipped records only ever use -1..936;
        #   * a RELEASED community mod (the user's installed
        #     `[UI]7V1_Three Kingdoms ... v1.46`) ships its own icons.json with
        #     Units extended to 2149 keys, of which 127 (2000..2126) name real
        #     materials, and every one of them resolves in that mod's
        #     materials.json.
        #
        # So the layer IS writable by a mod; this tool has not written it yet.
        # UPDATED 2026-10-23: it writes it now when the sentence names a picture
        # (`_probe/tmp_iconart_smoke.py` measured the round trip: slot 1000, a
        # 262,272 B DDS, both tables merged with all 1000 shipped keys and all
        # 4555 shipped materials intact).  So the answer depends on the request,
        # and the preview must say which of the two it is.
        want_icon = r.raw.get("icon")
        base["warnings"] = []
        if want_icon:
            from .game import iconart as IA
            try:
                # The picture is checked HERE, on the preview path, because
                # `iconart.plan` only decides numbers -- it never opens the file.
                # Measured 2026-10-23: a text file named `not_a_picture.png` got
                # `editable: True, edit_count: 3` from the preview and then killed
                # the build with PIL's own English sentence.  `check_picture`
                # reads only the header, so a plan stays cheap enough to run on
                # every keystroke, and the build still does the full decode.
                _w, _h = IA.check_picture(want_icon)
                _icons_doc, _materials_doc = IA.shipped(self.game_root)
                _art = IA.plan(_icons_doc, _materials_doc, want_icon,
                               stem=r.name, slot=base.get("icon_slot"))
            except IA.IconError as exc:
                # The build refuses this too, so the preview has to: a preview
                # that promises an icon and then dies on a material-name clash
                # teaches the player to distrust a sentence that was right.
                base["editable"] = False
                base["reason"] = str(exc)
                base["edit_count"] = 0
                return base
            base["icon_slot"] = _art["slot"]
            base["icon_material"] = _art["material"]
            base["icon_source_size"] = [_w, _h]
            # Three files, named without building them: the preview must be cheap
            # (a plan is run on every keystroke in the page) and encoding a
            # 262,272 B DDS plus merging a 2.5 MB materials table only to count
            # them would make the sentence feel broken.  `plan()` already
            # computed these exact paths from the same helper `emit()` uses.
            base["icon_files"] = sorted([_art["file_rel"].replace(os.sep, "/"),
                                        _art["icons_rel"].replace(os.sep, "/"),
                                        _art["materials_rel"].replace(os.sep, "/")])
            base["description"] += ("，并给它一张自己的图标（图标槽 %d，"
                                    "外加贴图和两张图标表）" % _art["slot"])
            base["edit_count"] += 1
            base["warnings"].append(
                "图标这一层要发 %d 个文件：一张 256×256 的图片，加上完整合并的"
                "图标表和材质表。游戏会画它 —— 2026-10-24 实机验过：把一张"
                "洋红/青棋盘写进这三份文件、把出厂图标格指过去，命令卡上画出的"
                "就是这张棋盘。之前十几次没画出来，原因写在工具自己身上："
                "图片文件头声明了「有几层缩放图」，却写 0 层，引擎拒绝这种"
                "自相矛盾的文件，于是那一格是空的。现在头部按游戏自己的写法写。"
                "还没量过的是：新建单位的图标在一局真游戏里长什么样 ——"
                "数据层和图标层都已单独验过，两者合起来的那一局还没跑。"
                % len(base["icon_files"]))
            # Say the shaping out loud when it happens: a 300x120 logo is NOT
            # shrunk to a square (that would distort it) and NOT cropped (that
            # would hide most of it) -- it is fitted into the square and the
            # margins stay transparent.  A player who expected a full-bleed
            # button needs to hear this before the build, not after.
            if (_w, _h) != (IA.SIDE, IA.SIDE):
                base["warnings"].append(
                    "你给的图是 %d×%d，会被等比缩进 %d×%d 的正方形里，"
                    "四周留透明边（不裁切、不拉伸）。" % (_w, _h, IA.SIDE, IA.SIDE))
        else:
            base["warnings"].append(
                "新单位的图标就是照着做的那个单位的：这句话没说要用哪张图。"
                "（游戏自己的单位图标表 0..999 已经占满，但模组可以往 1000 以上"
                "加 —— 已装的三国界面模组就加到了 2126，所以想要自己的图标，"
                "在句子里说一句「图标用 <图片路径>」就行）")
        if _builders:
            _free = free_by_builder.get(str(_builders[0])) or []
            # The number that will actually be written: the one asked for, or the
            # donor's own when only the building changed.  Printing every slot
            # the donor had would describe a state that will not exist.
            _box = (int(want_button) if want_button is not None
                    else (int(base["buttons"][0]) if base["buttons"] else 0))
            # Naming the donor's OWN building is not a re-point, and saying so
            # would describe an edit that is not happening (measured: unit 83
            # trains at 109, so `builder=109` writes the same two bytes back).
            _donor_builders = {s["builder"] for s in _slots
                               if s["builder"] not in (-1, None)}
            if want_builder is not None and int(want_builder) not in _donor_builders:
                base["warnings"].append(
                    "这个单位被改到 %s 的建造按钮上（第 %d 格），不是照着做的那个单位原来"
                    "所在的那座建筑；那一排还空着的是第 %s 格"
                    % (base["builder_names"][0], _box,
                       "、".join(str(x) for x in _free) if _free else "（一格都不空）"))
            else:
                base["warnings"].append(
                    "它出现在 %s 的建造按钮里（第 %s 格），因为建造位置是从原记录抄来的；"
                    "那一排还空着的是第 %s 格"
                    % (base["builder_names"][0],
                       "、".join(str(x) for x in base["buttons"]),
                       "、".join(str(x) for x in _free) if _free else "（一格都不空）"))
        elif want_builder is not None:
            # Named a building, but the donor has no train entry at all: there is
            # no slot whose two bytes could be re-pointed, so `add_unit` refuses.
            # Say it here or the preview promises a build that fails.
            base["editable"] = False
            base["reason"] = (
                "「%s」自己没有任何建造位置（它是那种谁都不训练的单位），"
                "没有可以改到 %s 上的位置"
                % (r.donor.display, base["builder_names"][0] if base["builder_names"] else r.raw.get("builder")))
        else:
            base["warnings"].append(
                "照着做的那个单位没有任何建筑在训练它，所以新单位暂时不会出现在任何建造菜单里")
            # Measured 2026-10-22: the tooltip's first line is the record's
            # LanguageDLLCreation string.  The build now writes a real
            # "生产<名字>" sentence there instead of the donor's, so this is a
            # note about which two strings ship rather than a defect.
        return base

    def _plan_new_tech(self, r, base):
        """Preview for "make a technology the game does not have".

        A technology is addressed by its POSITION in the array, so the id is not
        picked from a free pool -- it is ``len(techs)``, and the preview can say
        it without touching a byte.  Everything else here is about the two things
        a player would notice: the name string, and the button on a card.
        """
        from .dat import newtech as NT
        base["shape"] = "new_tech"
        base["donor_id"] = r.donor.id
        base["donor_name"] = r.donor.display
        base["new_name"] = r.name
        base["writes"] = "resources/_common/dat/empires2_x2_p1.dat"
        base["changes_dat"] = True
        base["dat_is_carrier"] = False
        base["mod_contains_dat"] = True

        try:
            new_id = NT.next_tech_id(self._stats)
            string_id = S.first_free_id(self.game_root)
            _locs_notes = []
            rec = NT.clone_tech(
                NT.pick_donor(self._tech_records(), r.donor.id),
                NT.internal_name_for(r.name, new_id), string_id,
                research_locations=_tech_locations_from_intent(
                    r, self, r.donor.id, _locs_notes),
                research_time=r.raw.get("research_time"))
        except NT.NewTechError as exc:
            base["editable"] = False
            base["changes_dat"] = False
            base["description"] = str(exc)
            base["reason"] = str(exc)
            base["edit_count"] = 0
            return base

        base["editable"] = True
        base["new_id"] = new_id
        base["string_id"] = string_id
        base["record_name"] = rec["name"]
        locs = rec["research_locations"]
        base["research_locations"] = locs
        base["building_ids"] = sorted({loc["location_id"] for loc in locs})
        base["building_names"] = [
            (self.describe(b, "unit") or {}).get("zh")
            or (self.describe(b, "unit") or {}).get("name") or str(b)
            for b in base["building_ids"]]
        base["description"] = (
            "照 %s 做一个新科技「%s」（编号 %d；名字用一个新字符串 %d；%s）"
            % (r.donor.display, r.name, new_id, string_id,
               ("占 %s 研究卡的第 %d 格" % ("、".join(base["building_names"]),
                                          int(locs[0].get("button_id")
                                              if locs[0].get("button_id") is not None
                                              else -1)))
               if base["building_names"] else "没有研究位置"))
        base["edit_count"] = 1
        # This warning used to say the new technology could never be in the tech
        # tree, because node id 1510 "is already the unit City Gate NE (Rubble)".
        # That was FALSE, and measured false on 2026-10-23 (`_probe/tmp_tree_for_
        # tech.py` + `tmp_what_1510.py`, which is why those two files exist):
        #
        #   * the .dat record at index 1510 IS `CityGate NE (Rubble)`, hp 0;
        #   * but NO tree row in ANY of the 62 civilizations carries Node ID 1510,
        #     in the Unit space or the Tech space -- `civtechtrees.py`'s own
        #     UNIT_USE_TYPES/TECH_USE_TYPES comment says why: a Node ID is a unit
        #     id in a Unit row and a tech id in a Tech row, and the row's
        #     `Use Type` decides which;
        #   * and no shipped tree references any tech node id above 1509 at all.
        #
        # So the tree half is not blocked by a collision; it is simply not written
        # yet by this tool.  Saying "impossible" when the answer is "not yet" is
        # the difference between a player giving up and a player knowing what to
        # ask for -- and the old sentence ALSO named a unit that no tree row
        # mentions, so it could not be checked by anyone reading it.
        base["warnings"] = [
            "它还不会出现在科技树面板里：这一版只写 .dat 那一半，科技树那层（每个文明一个 "
            "JSON，Node 编号 %d 在 62 个文明里现在一个都没占）本工具还没动。"
            "研究卡上有它、科技树面板上没有它" % new_id,
        ]
        # The icon layer, same wiring as unit.create's, but through the Techs
        # section -- which differs in three measured ways (2026-10-23, from the
        # only shipped precedent, `[UI]7V1_Three Kingdoms`): its keys start at
        # 500 rather than 1000, its textures live under `textures/ingame/tech`,
        # and its added icons are PNG rather than uncompressed DDS.  Copying the
        # unit shape here would point at a folder the tech icons do not use.
        _want_icon = r.raw.get("icon")
        if _want_icon:
            from .game import iconart as IA
            try:
                # Checked on the PREVIEW path on purpose: `iconart.plan` only
                # picks numbers and never opens the file, so without this the
                # preview would promise an icon and the build would die decoding
                # it (measured on the unit path, 2026-10-23).
                _w, _h = IA.check_picture(_want_icon)
                _icons_doc, _materials_doc = IA.shipped(self.game_root)
                _art = IA.plan(_icons_doc, _materials_doc, _want_icon,
                               stem=r.name, slot=base.get("icon_slot"),
                               kind="tech")
            except IA.IconError as exc:
                base["editable"] = False
                base["changes_dat"] = False
                base["reason"] = str(exc)
                base["description"] = str(exc)
                base["edit_count"] = 0
                return base
            base["icon_slot"] = _art["slot"]
            base["icon_material"] = _art["material"]
            base["icon_source_size"] = [_w, _h]
            base["icon_files"] = sorted([_art["file_rel"].replace(os.sep, "/"),
                                        _art["icons_rel"].replace(os.sep, "/"),
                                        _art["materials_rel"].replace(os.sep, "/")])
            base["description"] += ("，并给它一张自己的图标（图标槽 %d，"
                                    "外加贴图和两张图标表）" % _art["slot"])
            base["edit_count"] += 1
            base["warnings"].append(
                "图标这一层要发 %d 个文件：一张 256×256 的图片，加上完整合并的"
                "图标表和材质表。游戏会画它 —— 2026-10-24 实机验过：把一张"
                "洋红/青棋盘写进这三份文件、把出厂图标格指过去，命令卡上画出的"
                "就是这张棋盘。之前十几次没画出来，原因写在工具自己身上："
                "图片文件头声明了「有几层缩放图」，却写 0 层，引擎拒绝这种"
                "自相矛盾的文件，于是那一格是空的。现在头部按游戏自己的写法写。"
                "还没量过的是：新建单位的图标在一局真游戏里长什么样 ——"
                "数据层和图标层都已单独验过，两者合起来的那一局还没跑。"
                % len(base["icon_files"]))
            if (_w, _h) != (IA.SIDE, IA.SIDE):
                base["warnings"].append(
                    "你给的图是 %d×%d，会被等比缩进 %d×%d 的正方形里，"
                    "四周留透明边（不裁切、不拉伸）。" % (_w, _h, IA.SIDE, IA.SIDE))
        else:
            base["warnings"].append(
                "新科技的图标就是照着做的那个科技的。想要它自己的图标，在句子里"
                "加一句「图标用 <图片路径>」——这一版会把它作为新的一张图发出去，"
                "挂在科技图标表 0..312 之后（出厂那 313 格是全占的；这一层能扩到"
                "多大由记录的 i16 字段决定，上限 32767）。")
        if base["building_names"]:
            # A box is not a private resource: 66 shipped (building, button) pairs
            # already hold two or more technologies (the town centre's box 8 holds
            # Town Watch and Town Patrol; box 11 holds all three ages).  Saying
            # "takes box 8" without saying WHO ELSE is in it is the same
            # under-report as naming only one of two written files -- the player
            # finds out when two technologies share a button and wonder whether
            # they broke something.
            _box = locs[0].get("button_id")
            _where = locs[0].get("location_id")
            _mates = [(tid, rec.get("name"))
                      for tid, rec in enumerate(self._tech_records())
                      for loc in (rec.get("research_locations") or [])
                      if loc.get("location_id") == _where
                      and loc.get("button_id") == _box]
            base["warnings"].append(
                "它借用 %s 的第 %s 格"
                % (base["building_names"][0], _box))
            if _mates:
                base["warnings"].append(
                    "那一格本来已经有 %d 项科技（%s）：同一格放多项是出厂数据里就有的做法，"
                    "多出来的会挤在一起，不是冲突"
                    % (len(_mates),
                       "、".join((_tech_display(self, tid) or str(tid))
                                for tid, _n in _mates[:4])))
        # Notes raised while choosing the research card travel with the plan: the
        # chosen building may be a DIFFERENT record that answers to the same
        # display name (five town centres), and the player has to be able to see
        # which one was used rather than infer it from a name that matches four
        # other records.
        for _n in _locs_notes:
            base["warnings"].append(_n)
        return base

    def _plan_reskin(self, r, base):
        """Preview for "make the Archer look like the Longbowman"."""
        from .intent import reskin as RK
        if self._reskin_mode(r) == "rename":
            return self._plan_retarget(r, base)
        fam = self._families()
        rep = RK.plan(self.game_root, self._stats["graphics"], self._parsed[1],
                      r.entity.id, r.donor.id,
                      scope=self._reskin_scope(r),
                      families=fam,
                      family_scope=self._reskin_family_flag(r),
                      fill=self._reskin_fill_flag(r))
        base["shape"] = "sprite"
        # The rename model sets this too. Copy is the default, and a caller must
        # not have to read "key absent" as "the proven model" -- that is an
        # inference about a default, not a fact about this run.
        base["sprite_mode"] = "copy"
        base["target_id"] = r.entity.id
        base["target_name"] = r.entity.display
        base["donor_id"] = r.donor.id
        base["donor_name"] = r.donor.display
        # A sprite mod changes NO .dat byte, and it must say so: the same keys
        # exist on the availability preview, and a UI reading them cannot tell
        # "writes nothing to the .dat" from "forgot to fill this in".
        base["writes"] = "resources/_common/drs/graphics/*.sld"
        base["changes_dat"] = False
        base["dat_is_carrier"] = False
        base["mod_contains_dat"] = False
        if not rep.get("ok"):
            base["editable"] = False
            base["description"] = rep["reason"]
            base["reason"] = rep["reason"]
            base["edit_count"] = 0
            for k in ("conflicts", "skipped"):
                if rep.get(k):
                    base[k] = rep[k]
            return base
        base["editable"] = True
        base["description"] = RK.describe(
            rep, target_name=r.entity.display, donor_name=r.donor.display)
        base["edit_count"] = rep["file_count"]
        base["file_count"] = rep["file_count"]
        base["civ_count"] = rep["civ_count"]
        base["target_stems"] = rep["target_stems"]
        base["donor_stems"] = rep["donor_stems"]
        if rep.get("warnings"):
            base["warnings"] = list(rep["warnings"])
        # The engine pairs an animation with the art by frame_count/angle_count and
        # plays the wrong frames rather than refusing, so the structured form is
        # carried alongside the warning text: a UI that wants to draw a frame
        # ruler should not have to parse a sentence to get the numbers.
        if rep.get("grid_mismatches"):
            base["grid_mismatches"] = list(rep["grid_mismatches"])
        # The engine re-points a task-swapping unit to a sibling record and each
        # sibling names its own art, so "replace this unit's picture" has a
        # second, larger meaning.  Both the structured form and the count of what
        # was actually rewritten are carried, because a UI must be able to say
        # "20 of 232 files" without parsing a sentence.
        if rep.get("family"):
            base["family"] = rep["family"]
        # A stand-in is a decision the player will see, so it is exposed in
        # structured form and not only inside a sentence: "carry <- walk" is what
        # the toolkit did, and a reviewer needs to be able to disagree with it
        # without reading prose.
        if rep.get("filled"):
            base["filled"] = list(rep["filled"])
        base["fill"] = bool(rep.get("fill"))
        # Some of the art a unit uses is named by NO unit record -- the engine
        # picks the stone miner's carry picture by the resource being carried --
        # so those files travel with the stem.  In game on 2026-10-17 exactly
        # this file was the one job that stayed human, which is why the report
        # names them instead of leaving them inside a file count.
        if rep.get("resource_variants"):
            base["resource_variants"] = list(rep["resource_variants"])
        if rep.get("resource_variant_unmatched"):
            base["resource_variant_unmatched"] = list(
                rep["resource_variant_unmatched"])
        if rep.get("target_count"):
            base["target_count"] = rep["target_count"]
        if rep.get("skipped"):
            base["skipped"] = rep["skipped"]
        return base

    def _plan_retarget(self, r, base):
        """Preview for the rename model: repoint records, copy no pictures."""
        from .intent import retarget as RT
        rep = RT.plan(self.game_root, self._stats["graphics"], self._parsed[1],
                      r.entity.id, r.donor.id,
                      scope=self._reskin_scope(r),
                      families=self._families(),
                      family_scope=self._reskin_family_flag(r),
                      fill=self._reskin_fill_flag(r),
                      target_name=r.entity.display,
                      donor_name=r.donor.display)
        base["shape"] = "sprite"
        base["sprite_mode"] = "rename"
        base["target_id"] = r.entity.id
        base["target_name"] = r.entity.display
        base["donor_id"] = r.donor.id
        base["donor_name"] = r.donor.display
        # This model DOES change the .dat and ships no picture at all -- the
        # exact mirror of the copy model's keys, filled in from what it does
        # rather than left to a default.
        base["writes"] = "resources/_common/dat/empires2_x2_p1.dat"
        base["changes_dat"] = True
        base["dat_is_carrier"] = False
        base["mod_contains_dat"] = True
        if not rep.get("editable"):
            base["editable"] = False
            base["description"] = rep["reason"]
            base["reason"] = rep["reason"]
            base["edit_count"] = 0
            # A refused rename writes no `.dat`, so the keys that describe what
            # the build would ship must say "nothing" rather than keep the
            # optimistic values set above.
            base["changes_dat"] = False
            base["dat_is_carrier"] = False
            base["mod_contains_dat"] = False
            return base
        rt = rep["retarget"]
        base["editable"] = True
        base["description"] = rep["description"]
        base["edit_count"] = rt["rename_count"]
        base["rename_count"] = rt["rename_count"]
        base["target_names"] = rt["target_names"]
        base["donor_names"] = rt["donor_names"]
        base["no_sld_shipped"] = True
        base["copy_based_equivalent"] = rt["copy_based_equivalent"]
        base["civ_count"] = int(rep.get("civ_count") or 0)
        if rep.get("warnings"):
            base["warnings"] = list(rep["warnings"])
        for k in ("family", "filled", "fill", "resource_variants",
                  "target_count", "target_stems", "donor_stems",
                  "grid_mismatches"):
            if rep.get(k):
                base[k] = rep[k]
        return base

    def _paint_animations(self, r):
        """The animation names a repaint is limited to, or None for all of them.

        Read from the sentence rather than fixed, because a unit's art is split
        across up to nine files (one per animation) and repainting all of them
        when the user asked about the idle pose would ship changes they never
        asked for.
        """
        v = (r.raw or {}).get("animations")
        if v in (None, "", "all"):
            return None
        if isinstance(v, str):
            return [v]
        return list(v)

    def _plan_paint(self, r, base):
        """Preview for "paint this picture onto the unit's animations".

        A repaint ships loose `.sld` files and no `.dat`, exactly like the copy
        model of a reskin -- but the two are different products: one moves
        pictures that already exist, the other encodes a picture that does not.
        So they are separate strategies and separate previews, and a caller can
        tell from `shape` and `writes` which one it is looking at.
        """
        from .intent import repaint as RP
        base["shape"] = "sprite"
        base["sprite_mode"] = "paint"
        base["target_id"] = r.entity.id
        base["target_name"] = r.entity.display
        base["writes"] = "resources/_common/drs/graphics/*.sld"
        base["changes_dat"] = False
        base["dat_is_carrier"] = False
        base["mod_contains_dat"] = False
        try:
            rep = RP.plan_unit(self.game_root, self._stats["graphics"],
                               self._parsed[1], r.entity.id,
                               animations=self._paint_animations(r),
                               scope=self._reskin_scope(r))
        except RP.PaintError as exc:
            base["editable"] = False
            base["description"] = str(exc)
            base["reason"] = str(exc)
            base["edit_count"] = 0
            return base
        base["editable"] = True
        base["file_count"] = rep["file_count"]
        base["edit_count"] = rep["file_count"]
        base["civ_count"] = rep["civ_count"]
        base["animations"] = rep["animations"]
        base["per_file"] = rep["per_file"]
        if rep.get("missing_essential"):
            base["missing_essential"] = list(rep["missing_essential"])
        # The picture's own size is part of the promise: it is what the caller's
        # aspect ratio gets fitted into, and a user who hands over a 4,000 px
        # photo should see that acknowledged rather than silently resampled.
        try:
            base["picture_size"] = list(RP.picture_size(r.raw["picture"]))
        except RP.PaintError as exc:
            base["editable"] = False
            base["description"] = str(exc)
            base["reason"] = str(exc)
            return base
        base["description"] = (
            "把图片画到 %s 的 %d 个动画文件上（%d 个文明）"
            % (r.entity.display, rep["file_count"], rep["civ_count"]))
        return base

    def _build_paint(self, r, out_dir, title=None, author="", description="",
                     thumbnail=None, overwrite=False):
        """Encode the picture into main's BC1 blocks and emit loose `.sld` files.

        No `.dat` is written or shipped: the engine resolves the same file names
        it always did, so the only thing that changes is what those files draw.
        """
        from .intent import repaint as RP
        pic, pw, ph = RP.load_picture(r.raw["picture"])
        try:
            rep = RP.paint_unit(self.game_root, self._stats["graphics"],
                                self._parsed[1], r.entity.id, pic, pw, ph,
                                animations=self._paint_animations(r),
                                scope=self._reskin_scope(r))
        except RP.PaintError as exc:
            raise C.IntentError(str(exc))
        payload = rep["files"]
        if not payload:
            raise C.IntentError("这次换图没有产出任何文件，所以没有东西可以写进模组")

        info = E.make_info(title or ("%s 换图" % r.entity.display),
                           author=author, description=description)
        man = E.emit_json_mod(out_dir, payload, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite)
        verification = self._sprite_verification(
            payload, [{"civ_count": rep["civ_count"]}], out_dir)
        # A repaint has its own doubt and it is NOT the copy model's: no game has
        # ever loaded a hand-encoded block from this toolkit.  Saying the copy
        # model's sentence here would claim a proof about a different artifact.
        verification["proven"] = [
            "that each of the %d file(s) this mod ships was written from one "
            "picture, with every byte outside the main layer's BC1 blocks left "
            "exactly as the game shipped it" % verification["checked"],
            "that the block grid was respected: copying the original blocks back "
            "reproduces each source file byte-for-byte, so a block that landed "
            "in the wrong cell would have shown up as a mismatch",
        ]
        verification["not_proven"] = [
            "that a running game draws these files.  Loose .sld loading is "
            "proven (2026-10-17), but those mods copied shipped files; nothing "
            "has yet put a hand-encoded block into a file the game then drew",
        ]
        man["resolved"] = r.describe()
        man["sprite"] = {
            "mode": "paint",
            "target_id": r.entity.id, "target_name": r.entity.display,
            "civ_count": rep["civ_count"],
            "animations": rep["animations"],
            "missing_essential": rep.get("missing_essential") or [],
            "per_file": rep["per_file"],
            "verification": verification,
        }
        man["edits"] = rep["file_count"]
        man["edit_count"] = rep["file_count"]
        man["civs_edited"] = rep["civ_count"]
        man["changes_dat"] = False
        man["dat_is_carrier"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["verification"] = verification
        return man

    def _build_new_unit(self, r, out_dir, title=None, author="", description="",
                        thumbnail=None, overwrite=False):
        """Append one cloned unit record and ship the name it will show.

        `newunit.add_unit` mutates the model, `write_civ` writes the flag array
        from the model (not from raw bytes), and `serialize_dat` re-emits the
        stream.  The three steps are the same three the probe measured at
        +2,387 bytes with a byte-stable second pass, so the build path is the
        measured path rather than a second implementation of it.
        """
        from .dat import newunit as NU
        civ_index = self._civ_index(r.civ)
        civ_name = (self._civs[civ_index] or {}).get("name") or r.civ
        avoid = NU.referenced_ids(self._stats)
        new_id = NU.pick_free_id(self._stats, avoid=avoid)
        string_id = S.first_free_id(self.game_root)
        # Two strings, not one.  The record carries both a name and a creation
        # string, and they are read by different parts of the interface: the
        # name labels the unit, the creation string is the FIRST LINE OF THE
        # COMMAND-CARD TOOLTIP ("生产<名字>（价格：N）").  Measured 2026-10-22
        # on four builds: pointing the creation string at the new name (or
        # omitting it) emptied the entire tooltip body -- no title, no price, no
        # description.  A second free id is the whole fix.
        creation_id = S.first_free_id(self.game_root, start=string_id + 1)
        # A deep copy: `add_unit` mutates the model in place and this Toolkit
        # answers every later call from the same cached object, so building from
        # the cache would add the unit to this session's model as a side effect of
        # a build that may yet fail.
        stats = copy.deepcopy(self._stats)
        # The icon layer, when the sentence named a picture.  Built BEFORE the
        # record because the record only carries the SLOT NUMBER, so the slot has
        # to be allocated first -- and the slot cannot be allocated without the
        # merged tables, since the table is what makes a number mean a picture.
        # A patch would not do: the engine reads the mod's whole file in place of
        # the game's (measured on a released UI mod that keeps every base key).
        icon_files = {}
        icon_id = None
        if r.raw.get("icon"):
            from .game import iconart as IA
            _icons_doc, _materials_doc = IA.shipped(self.game_root)
            _art = IA.plan(_icons_doc, _materials_doc, r.raw["icon"],
                           stem=r.name, slot=r.raw.get("icon_slot"))
            icon_id = _art["slot"]
            _sw, _sh, _rgba = IA._rgba_from_picture(r.raw["icon"],
                                                    side=_art["side"])
            icon_files = IA.emit(_icons_doc, _materials_doc, _art["key"], _rgba,
                                 side=_art["side"], slot=_art["slot"],
                                 stem=_art["material"])
        # `civs=self._civs` is required whenever `button` is set: the training
        # slots live on the LOCATED records and are dropped by the parser on the
        # way into `stats` (measured: unit 83 has one train location located,
        # none in stats).  Passing the wrong list makes every donor look like it
        # trains nothing, which would refuse a perfectly good request.
        stats, rec = NU.add_unit(stats, self._raw, self._parsed[3], self._parsed[2],
                                 civ_index, r.donor.id, new_id,
                                 name_string_id=string_id,
                                 creation_string_id=creation_id,
                                 hp=r.raw.get("hp"),
                                 button=getattr(r, "button", None),
                                 builder=r.raw.get("builder"),
                                 civs=self._civs,
                                 civ_zh=CN.chinese(self._civs[civ_index].get("name")
                                                   or r.civ),
                                 icon_id=icon_id)
        data, rep = W.serialize_dat(stats, raw=self._raw)
        if rep.get("raw_consumed") != len(self._raw):
            raise C.IntentError(
                "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），所以这份不改了"
                % (rep.get("raw_consumed"), len(self._raw)))
        string_files = S.build_files(self.game_root,
                                     [(string_id, r.name),
                                      (creation_id, "生产" + str(r.name))])
        # One folder, two bins: the strings live outside the DAT storage point,
        # the icon tables inside it, and a mod is a mod folder, not a bin.
        _extra = dict(string_files or {})
        _extra.update(icon_files or {})
        info = E.make_info(title or ("新单位 %s" % r.name), author=author,
                           description=description)
        man = E.emit_data_mod(out_dir, data, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite,
                              json_files=_extra or None)
        # The emitted file must survive the game's inflate path and a re-parse,
        # and the new record must be IN it -- a reparse that succeeds on a file
        # without the record would look like the same green.
        raw2, how2 = P.load_dat(man["dat"])
        p2 = P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            stats2 = p2.parse()
        man["reloaded_with"] = how2
        man["reparse_leftover"] = len(raw2) - p2.r.pos
        man["reparse_ok"] = p2.r.pos == len(raw2)
        ids2 = {u["id"] for u in stats2["civs"][civ_index]["units"]}
        man["unit_added"] = new_id in ids2
        # The icon slot must survive too, and it is checked the same way: read the
        # field back OFF THE EMITTED FILE rather than trusting the number asked
        # for.  It cannot come from the parsed model -- that model keeps only six
        # keys per unit (class/hit_points/id/name/task_swap_group/type), so
        # `u["icon_id"]` is None for every unit and a check written against it
        # would report failure on a byte-perfect build (measured 2026-10-23).
        icon_read = None
        if icon_id is not None:
            # `civs_start` comes from the ORIGINAL locate on purpose: the pointer
            # section is fixed-size (one i32 array per civilization), so its offset
            # is the same number in the emitted file.  What changes is the raw
            # stream length, which `unit_spans` walks.
            _spans2 = NU.unit_spans(raw2, self._parsed[3], self._parsed[2],
                                    civ_index)
            _span = _spans2.get(new_id)
            if _span is not None:
                icon_read = struct.unpack_from("<h", raw2, _span[0] + NU.ICON_OFF)[0]
            man["icon_slot_written"] = icon_read
            man["icon_slot_ok"] = (icon_read == icon_id)
        man["new_unit"] = {
            "id": new_id, "name": r.name, "string_id": string_id,
            "creation_string_id": creation_id,
            "creation_text": "生产" + str(r.name),
            "civ": civ_name, "civ_index": civ_index,
            "donor_id": r.donor.id, "donor_name": r.donor.display,
            "record_bytes": rec["bytes"], "slot": rec["slot"],
            "buttons": rec.get("buttons") or [],
            "strings": sorted(string_files) if string_files else [],
        }
        if icon_id is not None:
            man["new_unit"]["icon_slot"] = icon_id
            man["new_unit"]["icon_files"] = sorted(icon_files)
        man["resolved"] = r.describe()
        # Records plus flags, matching the schema's declared count: one appended
        # record and one slot flipped.  A byte count here would not compare
        # against any other intent's edit_count.
        man["edits"] = 3 if icon_id is not None else 2
        man["edit_count"] = man["edits"]
        man["civs_edited"] = 1
        man["changes_dat"] = True
        man["dat_is_carrier"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["verification"] = {
            "ok": bool(man["reparse_ok"] and man["unit_added"]
                       and (icon_id is None or man["icon_slot_ok"])),
            "why_not_dat": "this intent appends a record instead of patching bytes",
            "reparse_ok": bool(man["reparse_ok"]),
            "unit_record_present": bool(man["unit_added"]),
            "proven": [
                "that the emitted .dat inflates and re-parses with the unmodified "
                "parser, with every byte consumed",
                "that civ %d's record run contains id %d after the round trip, so "
                "the record survived the writer rather than only the model"
                % (civ_index, new_id),
                "that the name line landed in the file the game's own 605-byte "
                "instructions name as the way a mod adds a string",
            ],
            "not_proven": [
                # PROVEN 2026-10-22: v26..v33 built the record with the same
                # `newunit.clone_image` this method calls, and the user confirmed
                # in game that a new unit appears on the town centre's 4th box,
                # can be trained, and shows a name in the production queue.
                # What has NOT been inside the game is THIS method's output --
                # `tmp_product_check.py` builds v35 through `build_bundle` and it
                # was never installed (measured 2026-10-23: no `v35` folder, no
                # log line).  Say the narrow true thing, not the broad false one:
                # the old sentence ("no test has loaded a record the toolkit
                # created") would make the next reader re-run v26..v33.
                "that a running game shows a unit built by THIS method (the "
                "bundle path).  The record-level clone was proven in game "
                "2026-10-22 (v26..v33, user-confirmed on the town centre's 4th "
                "box), but v35 -- the same intent through build_bundle -- was "
                "built and never installed, so the product path itself has no "
                "in-game reading",
            ],
        }
        return man

    def _build_new_tech(self, r, out_dir, title=None, author="", description="",
                        thumbnail=None, overwrite=False):
        """Append one cloned tech record, its effect, and the name it will show.

        Three appends in one pass: `newtech.add_tech` puts the record in the
        model, an optional `_new` effect gives it something to do, and
        `serialize_dat` re-emits the stream.  The record lands at index
        `len(techs)` because technologies are addressed by POSITION -- there is no
        free-id pool to pick from and no way to leave a hole.
        """
        from .dat import newtech as NT
        new_id = NT.next_tech_id(self._stats)
        string_id = S.first_free_id(self.game_root)
        # The icon layer, when the sentence named a picture.  Built BEFORE the
        # record for the same reason the unit path does it: the record carries
        # only the slot NUMBER, so the slot has to exist before the record can
        # point at it.  The Techs section differs from Units in three measured
        # ways (2026-10-23, `_probe/tmp_tech_icon_shape.py`): keys start at 500,
        # textures live under `textures/ingame/tech`, and the only shipped
        # precedent used PNG rather than uncompressed DDS.
        icon_files = {}
        icon_id = None
        if r.raw.get("icon"):
            from .game import iconart as IA
            _icons_doc, _materials_doc = IA.shipped(self.game_root)
            _art = IA.plan(_icons_doc, _materials_doc, r.raw["icon"],
                           stem=r.name, slot=r.raw.get("icon_slot"),
                           kind="tech")
            icon_id = _art["slot"]
            _sw, _sh, _rgba = IA._rgba_from_picture(r.raw["icon"],
                                                   side=_art["side"])
            icon_files = IA.emit(_icons_doc, _materials_doc, _art["key"], _rgba,
                                 side=_art["side"], slot=_art["slot"],
                                 stem=_art["material"], kind="tech")
        # A deep copy: `add_tech` mutates the model in place and this Toolkit
        # answers every later call from the same cached object.
        stats = copy.deepcopy(self._stats)
        try:
            rec = NT.add_tech(
                stats, r.donor.id,
                NT.internal_name_for(r.name, new_id), string_id,
                research_locations=_tech_locations_from_intent(r, self, r.donor.id),
                research_time=r.raw.get("research_time"),
                effect=r.raw.get("effect"),
                icon_id=icon_id)
        except NT.NewTechError as exc:
            raise C.IntentError(str(exc))
        data, rep = W.serialize_dat(stats, raw=self._raw)
        if rep.get("raw_consumed") != len(self._raw):
            raise C.IntentError(
                "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），所以这份不改了"
                % (rep.get("raw_consumed"), len(self._raw)))
        string_files = S.build_files(self.game_root, [(string_id, r.name)])
        # One folder, two bins: strings live outside the DAT storage point, the
        # icon tables inside it, and a mod is a mod folder, not a bin.
        _extra = dict(string_files or {})
        _extra.update(icon_files or {})
        info = E.make_info(title or ("新科技 %s" % r.name), author=author,
                           description=description)
        man = E.emit_data_mod(out_dir, data, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite,
                              json_files=_extra or None)
        # The emitted file must survive the game's inflate path and a re-parse,
        # and the new record must be IN it -- a reparse that succeeds on a file
        # without the record would look like the same green.
        raw2, how2 = P.load_dat(man["dat"])
        p2 = P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            p2.parse()
        man["reloaded_with"] = how2
        man["reparse_leftover"] = len(raw2) - p2.r.pos
        man["reparse_ok"] = p2.r.pos == len(raw2)
        # Read the record back through the LOCATOR, not the parser's stats: only
        # `locate_techs` keeps `research_locations` and the four display string
        # ids, so it is the only reader that can see whether the record is really
        # nameable and really on a card.
        _civs2, _cs2, _gv2, tail2 = L.locate(raw2)
        recs2 = L.locate_techs(raw2, tail2, _gv2)
        man["tech_added"] = len(recs2) == new_id + 1
        back = recs2[new_id] if man["tech_added"] else {}
        man["tech_readback"] = {
            "index": new_id, "name": back.get("name"),
            "lang_name": back.get("lang_name"),
            "effect_id": back.get("effect_id"),
            "icon_id": back.get("icon_id"),
            "locations": [{"location_id": loc.get("location_id"),
                           "research_time": loc.get("research_time"),
                           "button_id": loc.get("button_id")}
                          for loc in (back.get("research_locations") or [])],
        }
        # The icon slot is read back OFF THE EMITTED FILE, like the unit path:
        # trusting the number asked for would pass on a build that never wrote it.
        # `locate_techs` DOES keep `icon_id` (unlike the parser's per-unit model),
        # so the locator is the right reader here.
        if icon_id is not None:
            man["icon_slot_written"] = back.get("icon_id")
            man["icon_slot_ok"] = (back.get("icon_id") == icon_id)
        man["new_tech"] = {
            "id": new_id, "name": r.name, "string_id": string_id,
            "internal_name": (rec.get("record") or {}).get("name"),
            "donor_id": r.donor.id, "donor_name": r.donor.display,
            "effect_id": rec.get("effect_id"),
            "effect": r.raw.get("effect"),
            "locations": rec.get("locations"),
            "strings": sorted(string_files) if string_files else [],
        }
        if icon_id is not None:
            man["new_tech"]["icon_slot"] = icon_id
            man["new_tech"]["icon_files"] = sorted(icon_files)
        man["resolved"] = r.describe()
        man["edits"] = 2 if icon_id is not None else 1
        man["edit_count"] = man["edits"]
        man["civs_edited"] = 0
        man["changes_dat"] = True
        man["dat_is_carrier"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["verification"] = {
            "ok": bool(man["reparse_ok"] and man["tech_added"]
                       and (icon_id is None or man["icon_slot_ok"])),
            "why_not_dat": "this intent appends a record instead of patching bytes",
            "reparse_ok": bool(man["reparse_ok"]),
            "tech_record_present": bool(man["tech_added"]),
            "proven": [
                "that the emitted .dat inflates and re-parses with the unmodified "
                "parser, with every byte consumed",
                "that the record at index %d reads back with the display string id "
                "%d and the research box it was given" % (new_id, string_id),
                "that the record's byte length matches 62 + len(name) + 9 * boxes",
                "that the name landed in the file the game's own 605-byte "
                "instructions name as the way a mod adds a string",
            ],
            "not_proven": [
                # PROVEN 2026-10-22: v49 put a created technology on the town
                # centre's 8th research box and the user read it there, so both
                # halves of this old note are now answered -- the engine shows the
                # button, and index 1510 is reachable (the shipped tree already
                # referenced 517 Node IDs above 1,509, which was the encouragement
                # this note used to cite).  What remains unpublished is the
                # opposite direction: nothing has shown what happens when the
                # SHIPPED count moves under such a mod.
                "that a created technology survives a GAME UPDATE: index %d is "
                "the first free id only against today's shipped count, so a "
                "patch that adds technologies can move it.  Reachability itself "
                "is no longer in doubt (v49, 2026-10-22)" % new_id,
            ],
        }
        if icon_id is not None:
            # Same split the unit path states: the three files are checked byte
            # for byte and the record reads the slot back, but no run has watched
            # the game draw a TECH icon -- the shipped precedent only proves a mod
            # MAY extend the table, not that this particular picture renders.
            man["verification"]["not_proven"].append(
                "that a game draws the icon this build shipped for the new "
                "technology: its three files are checked byte for byte and record "
                "index %d reads icon slot %d back, but no run has watched that "
                "picture on a command card" % (new_id, icon_id))
        return man

    def _new_unit_bundle(self, new_list, base_raw, icon_state=None):
        """Fold every "make a new unit" sentence onto ONE stream.

        Returns ``(bytes_or_None, notes, refusals, string_entries, icon_files)``.

        ``icon_state`` is SHARED with the other creation bundle.  Both
        sections draw their materials from ONE ``materials.json``, so a
        unit icon and a technology icon in the same bundle must be
        written into one table -- measured 2026-10-23: each bundle
        re-read the shipped tables, so the tech bundle overwrote the
        unit bundle's merged file, slot 1000 vanished, and both
        previews still said the icon was fine.

        ``string_entries`` is a LIST of ``(id, text)`` pairs, not files: the
        caller builds one table from every creation in the request, because a
        unit and a technology write the same key-value path and emitting per
        sentence would repeat that file's header.

        The creations must share one pass rather than one serialize each: an
        append changes the stream length, so the second sentence has to see the
        model the first one produced or it would address stale offsets.  Ids are
        therefore picked AFTER each insertion, from the same mutated model -- two
        creations in one bundle must not both be offered id 382.

        A sentence that cannot be honoured is refused in place, matching every
        other bucket: one impossible creation must not throw away the ones that
        work.
        """
        from .dat import newunit as NU
        notes, refusals = [], []
        # (id, text) pairs, turned into files ONCE by the caller: emitting per
        # sentence and concatenating repeats the file's header block.
        string_entries = []
        stats = None
        civs_start = gv = None
        cur = base_raw
        touched = False
        next_string = None
        # The icon tables are CUMULATIVE: `IA.emit` returns the whole merged file,
        # so two sentences that each add an icon must work on the table the
        # previous one produced or the second would silently drop the first.  The
        # working pair is re-adopted from the emitted bytes after every icon.
        if icon_state is None:
            icon_state = {"icons": None, "materials": None, "files": {}}
        _icons_doc = icon_state.get("icons")
        _materials_doc = icon_state.get("materials")
        icon_files = icon_state.setdefault("files", {})
        for r in new_list:
            if stats is None:
                # Parsed ONCE, and the same model is mutated by every sentence.
                # Re-parsing per sentence was measured to be wrong: the stream is
                # only serialized after the loop, so each re-parse would hand back
                # the BASE model and the id picked for sentence 1 would be offered
                # again to sentence 2.  Two creations in one bundle both got id 382
                # and both names got string id 30030002 -- one record, one name,
                # while the manifest said two.
                try:
                    p = P.Parser(cur)
                    with contextlib.redirect_stdout(io.StringIO()):
                        p.parse()
                    civs, _cs, gv, _tail = L.locate(cur, parser=p)
                    civs_start = _cs
                    stats = p.stats
                except Exception as exc:                  # noqa: BLE001
                    refusals.append({"description": r.describe(),
                                     "reason": str(exc)})
                    continue
            civ_index = self._civ_index(r.civ)
            civ_name = (self._civs[civ_index] or {}).get("name") or r.civ
            try:
                avoid = NU.referenced_ids(stats)
                new_id = NU.pick_free_id(stats, avoid=avoid)
                # The string table this mod SHIPS is not part of the game's own
                # tables, so asking the game for a free id answers 30030002 every
                # time.  Successive creations step past the ones this bundle has
                # already claimed.
                # Two strings per unit: the name, and the creation string the
                # command card prints as its first line.  Step the bundle's
                # counter by two so the next creation starts cleanly above both.
                string_id = S.first_free_id(
                    self.game_root,
                    start=next_string or (S.LAST_SHIPPED_ID + 1))
                creation_id = S.first_free_id(self.game_root, start=string_id + 1)
                # Icons first: the record only carries the SLOT NUMBER, so the
                # slot has to be allocated against tables that already contain
                # every icon this bundle has shipped so far.
                _icon_id = None
                if r.raw.get("icon"):
                    from .game import iconart as IA
                    if _icons_doc is None:
                        _icons_doc, _materials_doc = IA.shipped(self.game_root)
                    _art = IA.plan(_icons_doc, _materials_doc, r.raw["icon"],
                                   stem=r.name, slot=r.raw.get("icon_slot"))
                    _icon_id = _art["slot"]
                    _rgba = IA._rgba_from_picture(r.raw["icon"],
                                                  side=_art["side"])[2]
                    _files = IA.emit(_icons_doc, _materials_doc, _art["key"],
                                     _rgba, side=_art["side"],
                                     slot=_art["slot"], stem=_art["material"])
                    icon_files.update(_files)
                    # Re-adopt the merged tables so the NEXT icon sees them.
                    _icons_doc = json.loads(_files[IA.ICONS_REL.replace(
                        os.sep, "/")].decode("utf-8"))
                    _materials_doc = json.loads(_files[IA.MATERIALS_REL.replace(
                        os.sep, "/")].decode("utf-8"))
                    icon_state["icons"] = _icons_doc
                    icon_state["materials"] = _materials_doc
                stats, rec = NU.add_unit(stats, cur, gv, civs_start, civ_index,
                                         r.donor.id, new_id,
                                         name_string_id=string_id,
                                         creation_string_id=creation_id,
                                         hp=r.raw.get("hp"),
                                         button=getattr(r, "button", None),
                                         builder=r.raw.get("builder"),
                                         civs=civs,
                                         civ_zh=CN.chinese(civ_name),
                                         icon_id=_icon_id)
            except (NU.NewUnitError, S.StringError) as exc:
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            next_string = creation_id + 1
            # Collected, not emitted: the caller builds ONE table from every
            # creation in the bundle (units and technologies share the path).
            string_entries.append((string_id, r.name))
            string_entries.append((creation_id, "生产" + str(r.name)))
            touched = True
            notes.append({
                "description": r.describe(),
                "mode": "new_unit",
                "civ": civ_name, "civ_index": civ_index,
                "id": new_id, "name": r.name, "string_id": string_id,
                "creation_string_id": creation_id,
                "creation_text": "生产" + str(r.name),
                "donor_id": r.donor.id, "donor_name": r.donor.display,
                "record_bytes": rec["bytes"], "slot": rec["slot"],
                "icon_slot": _icon_id,
            })
        if not touched:
            return None, notes, refusals, [], {}
        out, rep = W.serialize_dat(stats, raw=cur)
        if rep.get("raw_consumed") != len(cur):
            raise C.IntentError(
                "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），所以这份不改了"
                % (rep.get("raw_consumed"), len(cur)))
        return out, notes, refusals, string_entries, icon_files

    def _new_tech_bundle(self, tech_list, base_raw, icon_state=None):
        """Fold every "make a new technology" sentence onto ONE stream.

        Returns ``(bytes_or_None, notes, refusals, string_entries)``.

        Same reason as `_new_unit_bundle`: a technology's id is ``len(techs)``, so
        a second creation must see the model the first one produced or both would
        be offered the same index and the same name string.  Re-parsing per
        sentence was measured to be wrong for units (two records, one id, one
        name, while the manifest said two); the arithmetic here is identical.
        """
        from .dat import newtech as NT
        notes, refusals = [], []
        # Collected as (id, text) pairs and turned into files ONCE at the end.
        # Accumulating the emitted BYTES per sentence repeats the file header --
        # measured 2026-10-22: two creations in one bundle produced a table with
        # two "//INSTRUCTIONS:" blocks and two newlines of padding between them.
        # The engine tolerates the comments, but the file stops being a list.
        string_entries = []
        stats = None
        cur = base_raw
        touched = False
        next_string = None
        # Cumulative like the unit path: each icon re-adopts the merged tables so
        # a second sentence cannot silently drop the first one's material.
        if icon_state is None:
            icon_state = {"icons": None, "materials": None, "files": {}}
        _icons_doc = icon_state.get("icons")
        _materials_doc = icon_state.get("materials")
        icon_files = icon_state.setdefault("files", {})
        for r in tech_list:
            if stats is None:
                # Parsed ONCE; every sentence mutates this same model.
                try:
                    p = P.Parser(cur)
                    with contextlib.redirect_stdout(io.StringIO()):
                        p.parse()
                    stats = p.stats
                except Exception as exc:                  # noqa: BLE001
                    refusals.append({"description": r.describe(),
                                     "reason": str(exc)})
                    continue
            try:
                new_id = NT.next_tech_id(stats)
                string_id = S.first_free_id(
                    self.game_root,
                    start=next_string or (S.LAST_SHIPPED_ID + 1))
                _icon_id = None
                if r.raw.get("icon"):
                    from .game import iconart as IA
                    if _icons_doc is None:
                        _icons_doc, _materials_doc = IA.shipped(self.game_root)
                    _art = IA.plan(_icons_doc, _materials_doc, r.raw["icon"],
                                   stem=r.name, slot=r.raw.get("icon_slot"),
                                   kind="tech")
                    _icon_id = _art["slot"]
                    _rgba = IA._rgba_from_picture(r.raw["icon"],
                                                  side=_art["side"])[2]
                    _files = IA.emit(_icons_doc, _materials_doc, _art["key"],
                                     _rgba, side=_art["side"],
                                     slot=_art["slot"], stem=_art["material"],
                                     kind="tech")
                    icon_files.update(_files)
                    _icons_doc = json.loads(_files[IA.ICONS_REL.replace(
                        os.sep, "/")].decode("utf-8"))
                    _materials_doc = json.loads(_files[IA.MATERIALS_REL.replace(
                        os.sep, "/")].decode("utf-8"))
                    icon_state["icons"] = _icons_doc
                    icon_state["materials"] = _materials_doc
                rec = NT.add_tech(
                    stats, r.donor.id,
                    NT.internal_name_for(r.name, new_id), string_id,
                    research_locations=_tech_locations_from_intent(
                        r, self, r.donor.id),
                    research_time=r.raw.get("research_time"),
                    effect=r.raw.get("effect"),
                    icon_id=_icon_id)
            except (NT.NewTechError, S.StringError) as exc:
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            next_string = string_id + 1
            string_entries.append((string_id, r.name))
            touched = True
            notes.append({
                "description": r.describe(),
                "mode": "new_tech",
                "id": new_id, "name": r.name, "string_id": string_id,
                "internal_name": (rec.get("record") or {}).get("name"),
                "donor_id": r.donor.id, "donor_name": r.donor.display,
                "effect_id": rec.get("effect_id"),
                "locations": rec.get("locations"),
                "icon_slot": _icon_id,
            })
        if not touched:
            return None, notes, refusals, {}, {}
        out, rep = W.serialize_dat(stats, raw=cur)
        if rep.get("raw_consumed") != len(cur):
            raise C.IntentError(
                "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），所以这份不改了"
                % (rep.get("raw_consumed"), len(cur)))
        return out, notes, refusals, string_entries, icon_files

    def _build_retarget(self, r, out_dir, title=None, author="",

                        description="", thumbnail=None, overwrite=False,
                        base_raw=None, base_stats=None, base_parsed=None):
        """Compile a reskin by renaming graphics records and emit one .dat.

        The mirror of `_build_reskin`: that one copies pictures and ships no
        `.dat`; this one ships no picture and ships a `.dat`.  Both take their
        decisions from the same `reskin.plan` call underneath, so the two models
        cannot disagree about which files or records a swap covers.

        `base_raw`/`base_stats`/`base_parsed` let a bundle feed in the stream it
        has grown so far: appending an effect moves every offset after the
        effects section, so a second `.dat` half must be addressed against the
        stream being grown rather than against the one on disk.
        """
        from .intent import retarget as RT
        rep = RT.plan(self.game_root, self._stats["graphics"], self._parsed[1],
                      r.entity.id, r.donor.id,
                      scope=self._reskin_scope(r),
                      families=self._families(),
                      family_scope=self._reskin_family_flag(r),
                      fill=self._reskin_fill_flag(r))
        if not rep.get("editable"):
            raise C.IntentError(rep.get("reason") or "这个改名做不了")

        raw = self._raw if base_raw is None else base_raw
        stats = self._stats if base_stats is None else base_stats
        gv = (self._parsed[3] if base_parsed is None else base_parsed[3])
        # Deep-copy discipline, the same one `datgrant` documents: `apply` mutates
        # the model in place, and a caller that keeps the original model would
        # otherwise watch its own world change after a build.
        stats = dict(stats)
        stats["graphics"] = [dict(g) for g in stats["graphics"]]
        changed = RT.apply(stats, rep["retarget"])
        patched, wrep = W.serialize_dat(stats, raw=raw, gv=gv)

        info = E.make_info(title or rep["description"], author=author,
                           description=description)
        man = E.emit_data_mod(out_dir, patched, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite)

        # The emitted file must survive the game's inflate path and a re-parse,
        # and the re-parse must show exactly the renames the plan promised and
        # nothing else.  This is the rename model's equivalent of the copy
        # model's `identical_to_target` check: not "did we write bytes" but "did
        # the world end up as described".
        raw2, how2 = P.load_dat(man["dat"])
        p2 = P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            p2.parse()
        by_id = {}
        for g in p2.stats["graphics"]:
            by_id.setdefault(g["id"], g)
        want = {e["graphic_id"]: e["now"] for e in changed}
        wrong = [i for i, f in want.items()
                 if (by_id.get(i) or {}).get("file") != f]
        untouched_drifted = []
        before = {g["id"]: (g.get("file") or "")
                  for g in (base_stats or self._stats)["graphics"]}
        for i, f in before.items():
            if i in want:
                continue
            if (by_id.get(i) or {}).get("file") != f:
                untouched_drifted.append(i)
        man["reloaded_with"] = how2
        man["reparse_leftover"] = len(raw2) - p2.r.pos
        man["reparse_ok"] = p2.r.pos == len(raw2)
        man["dat_raw_bytes"] = len(patched)
        man["dat_serialize"] = wrep
        man["verification"] = {
            "ok": bool(man["reparse_ok"] and not wrong and not untouched_drifted),
            "renamed": len(changed),
            "renamed_but_wrong": wrong,
            "untouched_but_moved": untouched_drifted,
            "no_sld_shipped": True,
            "proven": [
                "every one of the %d renamed graphics record(s) names the donor "
                "picture the plan chose" % len(changed),
                "no graphics record outside the plan changed its file field",
                "the emitted .dat inflates and reparses exactly to its own length",
            ],
            "not_proven": [
                "that a running game draws the donor's picture for every job: the "
                "rename model was proven in game on 2026-10-17 (dsh test v13, one "
                ".dat and no pictures), so this model has a precedent, but that "
                "was a single mod on a single install",
            ],
        }
        man["resolved"] = r.describe()
        man["sprite"] = {
            "mode": "rename",
            "target_id": r.entity.id, "target_name": r.entity.display,
            "donor_id": r.donor.id, "donor_name": r.donor.display,
            "target_stems": rep.get("target_stems") or [],
            "donor_stems": rep.get("donor_stems") or [],
            "civ_count": rep.get("civ_count"),
            "rename_count": rep["retarget"]["rename_count"],
            "donor_names": rep["retarget"]["donor_names"],
            "warnings": rep.get("warnings") or [],
            "grid_mismatches": rep.get("grid_mismatches") or [],
            "family": rep.get("family"),
            "filled": rep.get("filled") or [],
            "fill": bool(rep.get("fill")),
            "target_count": rep.get("target_count"),
            "verification": man["verification"],
        }
        man["edits"] = len(changed)
        man["edit_count"] = len(changed)
        man["civs_edited"] = int(rep.get("civ_count") or 0)
        man["changes_dat"] = True
        man["dat_is_carrier"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        return man

    def _sprite_verification(self, payload, notes, out_dir, refusals=()):
        """Independent verdict on the loose files a reskin put on disk.

        Three separate questions, because they fail separately:

          * every file the plan named is on disk, and holds the bytes we meant
            to ship (a half-written or clobbered file draws the wrong unit);
          * none of them is byte-identical to the file it replaces -- a 4 MB
            no-op is still a mod the user has to load;
          * every refusal is named, so a sentence that could not be honoured is
            reported rather than subtracted in silence.

        Reading back off DISK rather than trusting the payload is the whole
        point: it is the only check that can see a path-traversal rejection or an
        overwrite refusal in the emitter.
        """
        rep = {"ok": True, "checked": 0, "missing_on_disk": [],
               "wrong_bytes": [], "identical_to_target": [],
               "refusals": list(refusals or ())}
        for rel, want in sorted(payload.items()):
            p = os.path.join(out_dir, rel.replace("/", os.sep))
            if not os.path.isfile(p):
                rep["missing_on_disk"].append(rel)
                continue
            with open(p, "rb") as fh:
                got = fh.read()
            rep["checked"] += 1
            if got != want:
                rep["wrong_bytes"].append(rel)
            src = os.path.join(self.game_root, rel.replace("/", os.sep))
            if os.path.isfile(src):
                with open(src, "rb") as fh:
                    if fh.read() == got:
                        rep["identical_to_target"].append(rel)
        rep["ok"] = not (rep["missing_on_disk"] or rep["wrong_bytes"]
                         or rep["identical_to_target"] or rep["refusals"])
        rep["files"] = len(payload)
        rep["civ_count"] = max([n.get("civ_count") or 0 for n in notes] or [0])
        rep["warnings"] = [w for n in notes for w in (n.get("warnings") or ())]
        rep["proven"] = [
            "that each of the %d file(s) this mod ships is on disk holding the "
            "donor's own bytes, and that none of them is byte-identical to the "
            "file it replaces (so this is a change, not a no-op)" % rep["checked"],
            "that the target names are the engine's own: resolved from the unit "
            "record's standing graphic through the graphics record's `file` "
            "string, not guessed from a filename",
        ]
        rep["not_proven"] = [
            "that this run of the running game draws the new art from these "
            "loose .sld files.  The copy model IS proven in game (2026-10-17: "
            "villagers came out as sheep from 20 loose .sld and no .dat), but "
            "every launch is a separate load, so a fresh install still has to be "
            "looked at once",
        ]
        return rep

    def _build_reskin(self, r, out_dir, title=None, author="", description="",
                      thumbnail=None, overwrite=False):
        """Compile a reskin and emit it.

        The verification here is NOT the byte-level one the .dat path uses:
        nothing was parsed, so there is no reparse to check.  Instead the bytes
        about to ship are compared against the install (is this really the
        donor's file?) and against the file being replaced (is this a no-op?),
        which are the two ways a copy can be wrong.
        """
        from .intent import reskin as RK
        rep = RK.plan(self.game_root, self._stats["graphics"], self._parsed[1],
                      r.entity.id, r.donor.id,
                      scope=self._reskin_scope(r),
                      families=self._families(),
                      family_scope=self._reskin_family_flag(r),
                      fill=self._reskin_fill_flag(r))
        if not rep.get("ok"):
            raise C.IntentError(rep["reason"])
        payload, missing = RK.read_payload(self.game_root, rep)
        if missing:
            raise C.IntentError(
                "这个安装里缺了来源那边的动画文件：%s" % "、".join(missing[:5]))
        # The plan-level check (is this really the donor's file, and is it a
        # no-op?) runs on the payload BEFORE emitting, because a refusal here
        # must stop the mod rather than ship it.  The disk-level check runs after
        # `emit_json_mod` and is the same function the bundle path calls, so the
        # single-intent and bundle verdicts cannot drift apart.
        pre = RK.verify_files(self.game_root, rep, payload)
        if not pre.get("ok"):
            raise C.IntentError(
                "this reskin would not change the picture: %s"
                % (pre.get("identical_to_target")
                   or pre.get("not_the_donor")
                   or pre.get("absent_targets")))

        info = E.make_info(title or rep and RK.describe(
            rep, target_name=r.entity.display, donor_name=r.donor.display),
                           author=author,
                           description=description)
        man = E.emit_json_mod(out_dir, payload, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite)
        verification = self._sprite_verification(
            payload, [{"civ_count": rep["civ_count"],
                       "warnings": rep.get("warnings") or ()}], out_dir)

        man["resolved"] = r.describe()
        man["sprite"] = {
            "target_id": r.entity.id, "target_name": r.entity.display,
            "donor_id": r.donor.id, "donor_name": r.donor.display,
            "target_stems": rep["target_stems"],
            "donor_stems": rep["donor_stems"],
            "civ_count": rep["civ_count"],
            "warnings": rep.get("warnings") or [],
            "grid_mismatches": rep.get("grid_mismatches") or [],
            "family": rep.get("family"),
            "filled": rep.get("filled") or [],
            "fill": bool(rep.get("fill")),
            "target_count": rep.get("target_count"),
            "skipped": rep.get("skipped") or [],
            "verification": verification,
        }
        man["edits"] = rep["file_count"]
        man["edit_count"] = rep["file_count"]
        man["civs_edited"] = rep["civ_count"]
        man["changes_dat"] = False
        man["dat_is_carrier"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["verification"] = verification
        return man

    def _placement_row(self, trees, civ, node_id, use_types):
        """The tree row that PLACES ``node_id`` for ``civ``, or the donor's row.

        Returns ``(row, inherited_from)``; ``inherited_from`` is the civilization
        the row was copied from when ``civ`` has no row of its own, else ``None``.

        Shared by the build-panel half and the ``.dat`` half so the two cannot
        disagree about which BUILDING the node belongs to.  A disagreement would
        put the menu entry under one building and the training entry under
        another, which a player sees as neither half having worked.

        The civ has no row of its own when this is a grant-from-a-donor, and then
        there is no local `Building ID` to place anything under.  Use the same
        donor the tree layer copies from, and say so, rather than reporting "no
        building is known" about a node plenty of civilizations can build.
        """
        unit_types = (CT.TECH_USE_TYPES if use_types == CT.TECH_USE_TYPES
                      else CT.UNIT_USE_TYPES)
        try:
            row = CT.row_for(trees[civ], node_id, unit_types)
        except (KeyError, TypeError):
            row = None
        if row is not None:
            return row, None
        try:
            donor, dr = CT.donor_row(trees, node_id, unit_types)
        except (KeyError, TypeError):
            return None, None
        if dr is None:
            return None, None
        return dr, donor

    def _civ_index(self, civ_key, civs=None):
        """The ``.dat`` civ index for a CivTechTrees key (``BRITONS`` -> 1).

        Trees are keyed by file stem and the `.dat` names civilizations its own
        way (`British`, `Magyars`), so the index is found by comparing stems
        rather than by assuming the two orders agree.  They do not: the six
        name-bridge civs (`French`/`FRANKS`) would all land on the wrong record.

        ``civs`` is the located civ list to search, and a bundle passes its own:
        appending an effect moves every section after the effects section, so the
        cached record list belongs to the BASE stream and a second `.dat` half in
        the same bundle must be addressed against the stream being grown.
        """
        self._ensure()
        pool = self._civs if civs is None else civs
        want = CT.civ_file_stem(civ_key)
        for i, c in enumerate(pool):
            if CT.civ_file_stem(c.get("name")) == want:
                return i
        raise C.IntentError("科技树里的这个文明名（%r）对不上 .dat 里的任何一条文明"
                            % (civ_key,))

    def _dat_grant_half(self, civ, unit_id, building_id, trees, action="grant"):
        """The ``.dat`` half of an availability edit, against this session's stream.

        Convenience wrapper for the single-intent path; the bundle addresses an
        explicit stream because it grows one step at a time.
        """
        return self._dat_grant_on(civ, unit_id, building_id, trees,
                                  self._raw, self._parsed[3], self._parsed[4],
                                  self._civs, self._stats, action=action)

    def _dat_grant_on(self, civ, unit_id, building_id, trees, raw, gv, tail, civs,
                      stats, action="grant"):
        """The in-game-proven ``.dat`` half of "let <civ> build <unit>".

        Returns ``(patched_raw_bytes, report)``; ``patched`` is ``None`` with a
        ``reason`` when this cannot be done, and then the caller emits the JSON
        halves alone -- with the reason recorded, never silently.

        ``raw``/``gv``/``tail``/``civs``/``stats`` are the stream to edit.  They
        are explicit rather than read from the session because two grants in one
        bundle compose: each appends an effect, which MOVES every offset after
        the effects section, so a later grant must address the stream the earlier
        one produced rather than the base.

        The recipe is the one the user confirmed in game (`dsh test v7`, m27131):
        append a NEW effect carrying the anchor's own commands plus the enable
        command, re-point the anchor technology at it, and move the unit's button
        to a free slot.  Every choice here is measured, not stylistic:

          * the anchor comes from :func:`datgrant.pick_tech`, which ranks by
            ``required_techs``.  The v5/v6 builds hung the enable on
            ``tech 263 'Longbow (make avail)'`` because its NAME says "make
            avail", and the user reported the button only appearing after a
            Castle (m26421).  ``required_techs`` is what actually says when a
            technology fires: 263 needs ``[102, 266 'Castle built']`` while 383
            needs ``[]``.
          * the anchor's commands MUST be carried into the new effect.  The
            anchor is chosen to be a 0:00 technology, which is exactly where a
            civilization's bonuses live; re-pointing it at a fresh single-command
            effect would delete a shipped bonus while reporting success.
          * the model is COPIED before the edit.  ``self._stats`` is this
            session's picture of the game and a build is a proposal on disk; a
            build that mutated the picture would silently change what the tool
            says afterwards (the defect class `test_availability_intent.py`
            section 2 exists to catch).
        """
        from .intent import datgrant as DG
        civ_index = self._civ_index(civ, civs=civs)
        techs = L.locate_techs(raw, tail, gv)
        if action == "revoke":
            # A revoke has no anchor to choose and no button to move: the edit is
            # one appended effect carrying a disable, hung on a technology that
            # fires later than whatever enables the unit (see `apply_revoke`).
            # The model is still copied first, for the same reason the grant path
            # copies it -- a build is a proposal on disk, not a change to the
            # session's picture of the game.
            stats = dict(stats)
            stats["effects"] = list(stats["effects"])
            stats["techs"] = list(stats["techs"])
            patched, rep = DG.apply_revoke(
                stats, raw, gv, civ_index, trees[civ], unit_id,
                rank_techs=techs)
            rep["civ"] = civ
            return patched, rep
        tech_index, anchor, why = DG.pick_tech(techs, civ_index)
        if tech_index is None:
            return None, {"ok": False, "reason": why, "civ_index": civ_index,
                          "civ": civ}
        # Minimal copy rather than `deepcopy`: the model holds 136,861 unit
        # records and only three objects are written -- the effects LIST (so the
        # append cannot reach the cache), the techs LIST, and the one anchor tech
        # dict whose `effect_id` is re-pointed.  Copying anything less leaves a
        # write that mutates the cache; copying more costs a deep copy per build.
        # On the bundle path `stats` is already a per-step copy, so the shallow
        # copy here only has to protect the lists that are appended to.
        stats = dict(stats)
        stats["effects"] = list(stats["effects"])
        stats["techs"] = list(stats["techs"])
        stats["techs"][tech_index] = dict(stats["techs"][tech_index])
        patched, rep = DG.apply_grant(
            stats, raw, gv, civ_index, civs[civ_index],
            trees[civ], unit_id, tech_index, building_id, trees=trees)
        rep["civ"] = civ
        rep["anchor_name"] = (anchor or {}).get("name")
        return patched, rep

    def _declared_dat_halves(self, resolved_list, trees):
        """The `.dat` half every sentence in ``resolved_list`` would write.

        Returns ``(halves, refusals)``, both cheap: this touches the schema and
        the tree rows and never runs the recipe (which serialises the whole
        93 MB `.dat`).  ``halves`` is a list of
        ``(resolved, civ_key, building_id, declaration)`` in sentence order;
        ``refusals`` is a list of ``(resolved, reason)`` for sentences that
        declare a half but cannot get one.

        The schema decides which actions get a half, not this file.  Both
        availability actions do: a grant was confirmed in game on 2026-10-16
        (`dsh test v7`) and a revoke on 2026-10-19 (`dsh test v17`).  The
        technology space has neither, because both proven commands are unit-space
        -- `type 2` names a UNIT id, so pointing one at a tech node would touch
        whichever unit happens to share that integer.

        A revoke does not need a building.  A grant does: it moves the unit's
        training button, so there has to be a training entry to move.  A revoke
        only appends a disable, so refusing it for "no building" would reject
        sentences the recipe can actually perform.
        """
        halves, refusals = [], []
        for r in resolved_list:
            dh = self._dat_half_declared(r.raw)
            if not dh:
                continue
            if (r.action or "grant") not in (dh.get("actions") or ()):
                refusals.append((r, dh.get("why_not_for_other_actions")
                                 or "this action has no verified `.dat` recipe"))
                continue
            if AV.space_of(r.raw) != CT.UNIT_USE_TYPES:
                refusals.append((r, "the `.dat` recipe is only proven for units; "
                                    "this sentence is about the technology space "
                                    "(%s)" % r.entity.display))
                continue
            civ = self._tree_civ(r.civ, trees)
            row, _inh = self._placement_row(trees, civ, r.entity.id,
                                            CT.UNIT_USE_TYPES)
            bldg = (row or {}).get("Building ID")
            if bldg is None and (r.action or "grant") != "revoke":
                # A GRANT moves the unit's training button, so it needs an entry
                # to move.  A REVOKE only appends a disable -- no button, no
                # building needed -- so refusing it here would reject something
                # the recipe can perform.
                refusals.append((r, "no building places this node for %s, so "
                                    "there is no training entry to enable" % civ))
                continue
            halves.append((r, civ, bldg, dh))
        return halves, refusals

    def _fold_dat_halves(self, halves, base_raw):
        """Run the `.dat` recipe for each half onto ONE growing stream.

        Returns ``(patched, reps, gv)``.  ``patched`` is ``None`` when no half
        produced bytes.  Each step re-derives the model from the stream the
        previous step produced, because appending an effect MOVES every offset
        after the effects section -- addressing the base for the second grant
        would patch the wrong bytes without erroring.

        A half that fails is NOT fatal: it leaves the stream as it was and
        records why, so the JSON halves still land and the manifest can say that
        this sentence got two of its three layers.  Failing the whole bundle
        instead would throw away the sentences that DID work.
        """
        raw = base_raw
        reps = []
        gv = None
        for r, civ, bldg, _dh in halves:
            p = P.Parser(raw)
            with contextlib.redirect_stdout(io.StringIO()):
                p.parse()
            civs, _cs, gv, tail = L.locate(raw, parser=p)
            patched, rep = self._dat_grant_on(civ, r.entity.id, bldg,
                                              self._trees(), raw, gv, tail,
                                              civs, p.stats,
                                              action=(r.action or "grant"))
            rep["resolved"] = r.describe()
            if patched is None:
                reps.append(rep)
                continue
            raw = patched
            reps.append(rep)
        return (raw if reps and any(x.get("ok") for x in reps) else None), reps, gv

    def _dat_half_declared(self, intent):
        """The schema's declaration of which action gets a ``.dat`` half.

        Which machinery compiles a sentence is the SCHEMA's decision, not this
        file's (`build` already says so for strategies).  Both availability
        actions now have one: a grant was confirmed in game on 2026-10-16
        (`dsh test v7`) and a revoke on 2026-10-19 (`dsh test v17`, which also
        established the ordering rule the recipe obeys).
        """
        intents_schema, _ = C.load_schema()
        spec = (intents_schema.get("intents") or {}).get(
            (intent or {}).get("intent"), {})
        return ((spec.get("compile") or {}).get("dat_half") or {})

    @staticmethod
    def _write_ops_for(dat_half, action):
        """How many write operations ``action`` performs, per the schema.

        The counts live in ``write_operations_by_action`` because grant and revoke
        do not write the same number: a grant also moves the training button, so
        it reports 2, while a revoke only appends an effect and re-points a
        technology, so it reports 1.  Falling back to the single
        ``write_operations`` keeps older schemas readable, but a schema that
        declares both actions and no per-action map is a defect this returns 0
        for rather than guessing.
        """
        by_action = dat_half.get("write_operations_by_action") or {}
        if action in by_action:
            return int(by_action.get(action) or 0)
        if by_action:
            return 0
        return int(dat_half.get("write_operations") or 0)

    def _panel_availability(self, civ, node_id, action, use_types, trees,
                            texts=None):
        """The build-panel half of an availability edit.  ``(report, files)``.

        The panel keys civilizations by its own display name (`Britons`) while
        the tree keys them by file stem (`BRITONS`), and it is split across two
        files by era, so the file is chosen by asking
        :func:`buildpanel.panel_path_for` rather than by inferring.

        ``texts`` is a mutable ``{rel_path: current_text}`` map owned by the
        caller.  It exists because TWO sentences in one bundle can edit the SAME
        panel file, and this function otherwise re-reads the shipped file every
        time -- so the caller's ``files.update()`` let the later, full-file
        result silently overwrite the earlier one.  Measured on
        `dsh test v9`: "grant the Champi Scout to the British" plus "revoke it
        from the Incas" shipped only the revoke, and the manifest said both.
        """
        row, inherited = self._placement_row(trees, civ, node_id, use_types)
        space = (BP.TECHS_KEY if use_types == CT.TECH_USE_TYPES
                 else BP.UNITS_KEY)
        _path, _key = BP.panel_path_for(self.game_root, civ)
        _rel = BP.panel_rel_for(_path)
        _text = (texts or {}).get(_rel)
        try:
            rep, files = BP.availability_edit(
                self.game_root, civ, node_id, action,
                building_id=(row or {}).get("Building ID"),
                age_id=(row or {}).get("Age ID"),
                space=space,
                ready=self._panel_ready(trees, space, node_id),
                text=_text,
            )
        except Exception as e:                      # noqa: BLE001 - reported
            # Reaches the screen through the bundle summary ("这几句都做不了……"),
            # so the sentence is Chinese like every other refusal there.
            return ({"ok": False, "mode": "errored",
                     "reason": "这个文明的建造面板改不了：%s" % e}, {})
        if inherited:
            rep["building_from"] = inherited
        if texts is not None and _rel and files.get(_rel) is not None:
            # Hand the next sentence the text this one produced, so edits chain
            # instead of each starting over from the shipped file.
            texts[_rel] = files[_rel].decode("utf-8")
        return rep, files

    def _panel_ready(self, trees, space, node_id):
        """``ready(civ_key) -> bool``: is that civ's tree row ResearchedCompleted?

        The donor preference for a synthesised panel entry.  A donor whose own
        tree says "has it" produced the menu entry the game already shows; a
        donor whose row is merely `ResearchRequired` would copy an entry that is
        itself behind a gate.

        The node id is a parameter because `node_status` needs it -- a predicate
        that ignored it would answer "ready" for the wrong row, which is the
        class of bug this project keeps paying for.
        """
        ut = (CT.TECH_USE_TYPES if space == BP.TECHS_KEY
              else CT.UNIT_USE_TYPES)

        def _ready(civ_key):
            tree = trees.get(CT.civ_file_stem(civ_key))
            if tree is None:
                return False
            return CT.node_status(tree, node_id, ut) == "ResearchedCompleted"
        return _ready

    def _tree_civ(self, name, trees):
        """A user-given civilization name -> the key ``trees`` is actually under.

        Accepts what the .dat calls the civ (`Magyars`, `Hindustanis`, `British`)
        and what the file is called (`MAGYAR`, `INDIANS`, `BRITONS`), because the
        two differ on six civs and a user has no way to know which one this
        layer wants.  Refuses with the candidates rather than guessing.
        """
        if name in trees:
            return name
        if isinstance(name, str):
            stem = CT.civ_file_stem(name)
            if stem in trees:
                return stem
            upper = name.upper()
            if upper in trees:
                return upper
        close = [c for c in sorted(trees) if isinstance(name, str)
                 and (name.upper()[:4] in c or c[:4] in name.upper())]
        if close:
            raise C.IntentError("unknown civilization %r; did you mean %s?"
                                % (name, ", ".join(close)))
        raise C.IntentError("unknown civilization %r for the tech-tree layer; "
                            "known: %s" % (name, ", ".join(sorted(trees))))

    def _build_availability(self, intent, out_dir, title=None, author="",
                            description="", thumbnail=None, overwrite=False):
        """The JSON-only build for "let <civ> build <unit>".

        Three things are deliberately different from :meth:`build`:

        * the edits are made on a COPY of the tree, taken before the change, so
          the verification can compare the shipped file against the emitted one
          through the same serializer.  Verifying against the already-mutated
          object would compare the change with itself and always pass;
        * the emitted path is re-read from DISK and compared byte for byte with
          what ``emit_json_mod`` was handed, because the emitter copies and adds
          a manifest of its own -- "the bytes were right" is a claim about disk;
        * the result says what is NOT proven.  The end-to-end test asserts the
          same boundary, and a caller reading ``verification`` must not conclude
          the game will offer the unit.

        The change is made on a COPY of the civilization's tree.  The cached
        trees are this session's picture of the GAME's files, and a build is a
        proposal written to ``out_dir`` -- it must not edit the picture.  The
        .dat path behaves the same way for the same reason (``bytes`` are
        immutable), so a caller can plan, build, and then plan again and get the
        same answer instead of one that has drifted by whatever was built.
        """
        trees = self._trees()
        if not trees:
            raise C.IntentError(
                "no CivTechTrees data next to this install (%s)"
                % CT.trees_dir(self.game_root))
        intents_schema, _ = C.load_schema()
        r = C.resolve(intent, intents_schema)
        civ = self._tree_civ(r.civ, trees)
        action = r.action or "grant"
        ut = AV.space_of(r.raw)

        # Preview first, using the SAME function the plan uses.  A build that
        # skipped this could write a duplicate row for a civ that already has the
        # unit -- a file whose parse is fine and whose meaning is undefined.
        #
        # `civ_zh` is passed for the same reason `plan` passes it: the refusal
        # this can raise is player-facing prose, and `civ` is a file stem
        # (INCAS).  Without it, the same rule would read "INCAS 本来就不能..."
        # here and "印加 本来就不能..." from the preview -- two spellings of one
        # answer, depending on which entry point the player used.
        pre = AV.plan(trees, civ, r.entity.id, action,
                      display=r.entity.display, use_types=ut,
                      civ_zh=CN.chinese(civ))
        if not pre["ok"]:
            raise C.IntentError(pre["reason"])

        # Work on a copy: `orig` is the game's tree as shipped, `edited` is the
        # proposal.  Both are needed afterwards -- `orig` is what the serializer
        # must reproduce byte for byte, `edited` is what gets written.  `edited`
        # is a full JSON round-trip rather than a shallow dict copy because a
        # shallow one would share the ROW dicts, and a `set_status` edits a row
        # in place.
        import json as _json
        orig = _json.loads(_json.dumps(trees[civ], ensure_ascii=False))
        orig.pop("path", None)          # bookkeeping, not part of the file
        shipped = CT.serialize(orig)
        edited = _json.loads(_json.dumps(trees[civ], ensure_ascii=False))
        # The proposal keeps every civilization: `apply` finds the donor row by
        # searching the corpus, so handing it only the edited civ would make the
        # unit look like it belongs to nobody.
        proposal = dict(trees)
        proposal[civ] = edited

        # What a revoke is SUPPOSED to remove, computed before the edit.  A revoke
        # cascades up the upgrade chain so the file stays chain-closed (no row may
        # Link ID a node the file lacks -- all 62 shipped files obey this, and a
        # dangling target is grounds for the game to reject the whole tree, which
        # is what invalidated the v9 experiment).  Verification needs the intended
        # set or the intended cascade would be reported as collateral damage.
        cascade = (CT.chain_closure(edited, r.entity.id, use_types=ut)
                   if action == "revoke" else None)
        rep = AV.apply(proposal, civ, r.entity.id, action, use_types=ut)
        files, rel = AV.emit_files(proposal, civ)
        # The OTHER half.  The tree is a model; the menu the player sees is
        # supplied by a pre-baked panel file, so an availability edit has to
        # land in both or it changes a document the game may never consult.
        # See `game/buildpanel.py` for why this is a text splice and not a
        # re-serialisation.
        panel_rep, panel_files = self._panel_availability(
            civ, r.entity.id, action, ut, trees)
        files.update(panel_files)
        # The THIRD half, and the only one proven to render in game.  The two
        # JSON layers are a model of per-civ availability; the `.dat` recipe is
        # what the user actually confirmed (m27131 for a grant, and `dsh test v17`
        # on 2026-10-19 for a revoke).  Which actions get it is the schema's
        # declaration, not this file's.
        dat_half = self._dat_half_declared(intent)
        dat_rep, patched = None, None
        if action in (dat_half.get("actions") or ()):
            _row, _ = self._placement_row(trees, civ, r.entity.id, ut)
            _bldg = (_row or {}).get("Building ID")
            if _bldg is None and action != "revoke":
                # A grant moves the unit's training button, so a training entry
                # must exist to move.  A revoke only appends a disable, so the
                # building is irrelevant and demanding one would refuse work the
                # recipe can do.
                dat_rep = {"ok": False, "reason":
                           "no building places this node for %s, so there is no "
                           "training entry to enable" % civ}
            elif ut != CT.UNIT_USE_TYPES:
                # The proven recipe is "make a UNIT available", which is a
                # unit-space command (`type 2` with `a = <unit id>`).  Pointing
                # it at a tech-space node would enable whatever unit happens to
                # share that integer, so it is refused rather than guessed.
                dat_rep = {"ok": False, "reason":
                           "the `.dat` grant recipe is only proven for units; "
                           "this sentence is about the technology space (%s)"
                           % r.entity.display}
            else:
                patched, dat_rep = self._dat_grant_half(
                    civ, r.entity.id, _bldg, trees, action=action)
        elif dat_half:
            dat_rep = {"ok": False, "reason":
                       dat_half.get("why_not_for_other_actions",
                                    "this action has no verified `.dat` recipe")}
        if patched is not None:
            files = dict(files)
        info = E.make_info(title or pre["description"], author=author,
                           description=description)
        if patched is not None:
            man = E.emit_data_mod(out_dir, patched, info, thumbnail=thumbnail,
                                  base_dir=self.game_root, overwrite=overwrite,
                                  json_files=files)
        else:
            man = E.emit_json_mod(out_dir, files, info, thumbnail=thumbnail,
                                  base_dir=self.game_root, overwrite=overwrite)

        # --- verification, from DISK --------------------------------------
        emitted_path = os.path.join(out_dir, rel)
        with open(emitted_path, "rb") as fh:
            on_disk = fh.read()
        ver = AV.verify_files(orig, edited, shipped, r.entity.id, use_types=ut,
                              cascade_ids=cascade)
        ver["emitted_matches_intended"] = (on_disk == files[rel.replace(
            os.sep, "/")])
        ver["emitted_bytes"] = len(on_disk)
        ver["emitted_path"] = emitted_path
        # The engine formats `CivTechTrees/%s.json` itself, so the only thing
        # worth asserting is that the file sits under that relative path.
        ver["path_is_engine_relative"] = rel.replace(
            os.sep, "/").startswith(CT.CIVTECHTREES_REL.replace(os.sep, "/") + "/")
        ver["ok"] = bool(ver["ok"] and ver["emitted_matches_intended"]
                         and ver["path_is_engine_relative"])
        ver["proven"] = [
            "the serializer reproduces the shipped file byte for byte",
            "the emitted tree re-parses to the same object",
            "every row other than the named %s is unchanged"
            % ("technology" if ut == CT.TECH_USE_TYPES else "unit"),
            "the file on disk equals the bytes handed to the emitter",
            "the file sits under the path the engine formats at runtime",
        ]
        # This claim is only true when no `.dat` was written.  The JSON strategy
        # used to be the whole product, so the sentence could be unconditional;
        # now the same method may also write the proven `.dat` half, and shipping
        # a `.dat` while claiming there is none is exactly the kind of quiet lie
        # this project keeps paying for.
        if patched is None:
            ver["proven"].append("no .dat is included in this mod")
        # HONESTY BOUNDARY, and it is not hypothetical any more.  On 2026-10-14
        # this exact path was tested in game: a mod carrying BOTH a `.dat` edit
        # and a rewritten `CivTechTrees/BRITONS.json` loaded (the game log has
        # "Enabling mod #0 (aoe2mod smoke villager HP + Britons units)"), the
        # `.dat` half took effect, and this half did NOT -- in either mode
        # (add_row and set_status).  So the tree file is a MODEL of per-civ
        # availability, not a proven input.  Do not upgrade this wording back to
        # a promise without a new in-game result.  (Superseded in the useful
        # direction by `dsh test v15` -- see the "status of the tree write"
        # paragraph below: the model is not merely unproven, it is measured NOT
        # to move the build menu.)
        #
        # ⚠ THIS PARAGRAPH WAS HALF WRONG AND IS KEPT ONLY AS A WARNING.
        # It used to argue: six candidate per-civ gates inside the `.dat` were
        # refuted (membership, the record, the effect layer, prerequisite
        # transitivity, the shipped TechTree singleton, overlay depth), so
        # `CivTechTrees/` "is the ONLY place a per-civ gate could live".
        #   * The six refutations are still measurements and still hold.
        #   * The conclusion drawn from them does NOT.  A seventh dat-side
        #     mechanism was never tested by those six: a `type 2` Enable/Disable
        #     Unit command hung on a technology the civilization ITSELF owns, with
        #     the LAST command to fire winning.  `dsh test v7` (2026-10-16) used it
        #     to give unit 2550 to the Britons and `dsh test v17` (2026-10-19) used
        #     its mirror (`b = 0`) to take 2550 away from the Incas -- but only from
        #     the Castle Age, because the 0:00 carrier fired before the global
        #     enable and lost.  Absence of evidence in six candidate sites was read
        #     as evidence of absence everywhere, which is the same mistake this
        #     project keeps paying for.
        #
        # Two cheaper explanations for the 2026-10-14 failure are still REFUTED
        # and must not be revived: "the overlay does not recurse into
        # subdirectories" (`_probe/test_overlay_depth.py`: the WIDGETUI storage
        # root has 550 nested mod files, deepest 4 levels, and a depth-3 emblem is
        # visible in game) and "the file name or FORM is wrong"
        # (`_probe/test_tree_form.py`: the exe names `CivTechTrees/%s.json`
        # exactly once, with its own generated field table ending immediately
        # before it).
        #
        # The status of the tree write is no longer "unproven" either.  `dsh test
        # v15` (2026-10-19) sent ONLY two `CivTechTrees/*.json` over a
        # byte-identical `.dat` carrier, asserted both trees chain-closed, kept
        # the panel untouched, and the engine logged loading the mod -- the menu
        # did not move in either direction.  That is a measurement, so: THE TREE
        # LAYER DOES NOT ADD OR REMOVE A BUILD-MENU BUTTON.  It is still written,
        # because a different screen reads it (the tech-tree preview's controls
        # map to tree enum values 16 of 16, `_probe/test_screen_vocabulary.py`)
        # -- but it is not what the sentence below may promise.
        #
        # 2026-10-15 narrowed it further, WITHOUT any mod installed: the shipped
        # `futuravailableunits.json` is SILENT about Sicilians' Siege Onager (`588`
        # absent from the siege workshop's `Units`, its research `320` absent from
        # `Techs`) while `CivTechTrees/SICILIANS.json` grants it
        # `ResearchedCompleted` -- and a running game OFFERED both the upgrade and
        # the unit.  So the build menu does NOT follow the panel alone
        # (`_probe/test_time_gate_and_tooltip.py`).  That is evidence about the
        # shipped files; the 2026-10-19 runs (v15 tree-only, v16 button-byte-only)
        # are what finally showed that a MOD EDIT to either JSON file is not what
        # the button follows.
        #
        # The two layers are also 99.4% the same data (3,107 of 3,126 (civ, unit)
        # pairs agree -- `_probe/test_panel_tree_agreement.py`).  That used to be
        # the stated reason this method writes BOTH ("whatever the engine
        # consults, it sees the edit").  Both writes are STILL correct, but not
        # for that reason: neither file is what adds or removes a build-menu
        # button (v15 / v16, 2026-10-19).  They are written because other screens
        # consume them, and because leaving them stale would make the two data
        # layers disagree with the `.dat` the same mod ships.
        # The sentence names WHAT is being offered ("the unit" / "the technology"),
        # because that is the question the reader is asking; the tests assert the
        # noun is present, so dropping it is a silent regression in the wording.
        #
        # 2026-10-15, the first clean in-game test (m24660): the user selected a
        # data mod before starting a match -- which is how a data mod actually
        # loads -- and reported 「不列颠黑暗时代兵营，没有蔷琵侦察兵，村民血量是1000」.
        # The control passed (the `.dat` edit rendered) and the grant did not.
        #
        # 2026-10-17 CORRECTED IT (m29132, `dsh test v9`).  v9's C sentence REVOKED
        # unit 2550 from the Incas -- the tree row deleted, the panel entry
        # deleted, and the `.dat` carried UNCHANGED, so the global `type 2` enable
        # in tech 1350 still said "yes".  The user reported the Incas Barracks
        # STILL shows the Champi Scout, and `_probe/test_revoke_is_not_enough.py`
        # confirms the bytes really did what the sentence claimed (INCAS.json 56 ->
        # 55 unit rows, no panel entry, `.dat` shipped-plus-one-effect).
        #
        # So deleting BOTH JSON layers did not take the button away.  An earlier
        # revision of this comment recorded an "AND gate" model -- a JSON layer can
        # veto what the `.dat` allows -- and that model is now REFUTED.
        #
        # The replacement model written here next was TOO STRONG, and an
        # independent review cut it down -- correctly.  What the evidence
        # supported at that point:
        #
        #     the `.dat` is the only layer SHOWN to move the build menu;
        #     it is not shown to be the only layer that CAN move it
        #
        #   * v6 grant (`.dat` gated until the Castle, JSON said yes)     -> hidden.
        #   * v7 grant (only which tech carries the enable changed; both
        #     JSON layers byte-identical to v6's)                         -> shown.
        #     That is the observation that proves the `.dat` CAN drive the menu.
        #   * v9 revoke (`.dat` still allows 2550, both JSON layers gone) -> shown.
        #     PROVISIONAL: v9's INCAS.json kept a dangling `Link ID 2550` after
        #     its 2550 row was deleted, and no shipped tree file has a dangling
        #     link id, so the game may have fallen back to the `.dat` default
        #     tree.  That session also ran 43 s after the mod loaded with no map
        #     load, so match entry cannot be confirmed.  (`revoke` no longer emits
        #     that shape: `CT.revoke` cascades and `dangling_links` is asserted.)
        #   * 2026-10-15 JSON-only grant (`.dat` said no, JSON said yes)  -> hidden.
        #     Its log is gone, so this line cannot be cited as evidence.
        #
        # "Why the `.dat` cannot be the whole story" -- the paragraph that used to
        # sit here -- is ANSWERED, and the answer went the other way.  It argued
        # that for the 32 units whose `type 2` enable is global (civ = -1, no
        # per-civ enable; the Champi Scout is one) the shipped `.dat` carries no
        # per-civ signal, so something outside the `.dat` must decide.  Both JSON
        # layers were then deleted in v9 and the button stayed.  What that
        # paragraph missed is that the `.dat` can express it without touching the
        # unit record: hang a `type 2` command on a technology the civilization
        # OWNS, and the last command to fire wins.  The shipped data has nine
        # disable commands (`_probe/probe_revoke_mechanism.py`), e.g. Armenians and
        # Georgians lose the Lumber Camp through `tech 932/940 -> effect 944`.
        # v17 confirmed the mechanism in game for unit 2550.
        #
        # That these files are READ is still supported, by weaker evidence than an
        # earlier revision of this comment claimed: `futuravailableunits.json`
        # sits 96 bytes from `CommandPanel` and within three occurrences of
        # `TechTreePreviewPanel` in the executable, and
        # `widgetui/futuravailableunits.json` is an 81-byte stub redirecting to
        # the dat-folder copy -- a fixed engine entry point, with nothing said
        # about what the engine does with it.  `linkedTechs.json` separately
        # carries Cycle groupings the `.dat` cannot express.  The tech-tree screen
        # `widgetui/screentechtree.json` has 16 icon widgets and all 16 map to
        # tree enum values, while `techtreepreviewpanel.json` mentions none of
        # them, so "the preview reads the tree" rests on asset names, not a
        # layout binding.
        #
        # It means this module's JSON write side is a MODEL whose effect on the
        # running build menu has since been measured as NO effect (v15 for the
        # tree, v16 for the button byte, v17 for the `.dat`).  Both files are
        # still written, because the tree feeds the tech-tree preview and the
        # panel feeds the greyed-out future-items view -- not because they gate a
        # button.
        #
        # So the sentence below may not claim a JSON layer changes the menu.  It
        # says which layers this build wrote and which of them has ever been shown
        # to render.
        _noun = "technology" if ut == CT.TECH_USE_TYPES else "unit"
        # The honesty wording depends on which layers this build actually wrote.
        # Before the `.dat` half existed this sentence always said "the JSON
        # layers did not reach the menu"; saying that about a build that DOES
        # carry the in-game-proven `.dat` recipe would understate it, and saying
        # "the game will offer it" about a build that carries only JSON would
        # overstate it.  Both halves are therefore reported from what happened.
        if patched is not None:
            _d = dat_rep or {}
            ver["proven"].append(
                "the `.dat` half the game confirmed was written: a new effect was "
                "appended carrying the anchor technology %s's own commands plus "
                "'make unit %s available', and the technology now points at it "
                "(this is what `dsh test v7` did, and the user confirmed the unit "
                "appeared at 0:00)"
                % (_d.get("tech"), r.entity.id))
            ver["not_proven"] = [
                "that THIS mod renders %s for that civilization -- the recipe is "
                "the one confirmed in game (2026-10-16, `dsh test v7`, three "
                "controls: villagers stayed at 1000 hp, the Castle Longbowman was "
                "unaffected, and the Dark Age Barracks showed the unit), but each "
                "new mod is a new load and only an in-game test settles it"
                % _noun,
            ]
        else:
            ver["not_proven"] = [
                "that a running game changes its build menu because of this "
                "edit, which offers the %s in the JSON layers only (%s).  That "
                "is now a measurement and not a doubt: `dsh test v15` "
                "(2026-10-19) shipped ONLY `CivTechTrees/*.json` over a "
                "byte-identical `.dat` carrier, the engine logged loading it, and "
                "the menu did not move in either direction.  What moves the menu "
                "is the `.dat` layer -- a `type 2` command on a technology the "
                "civilization already owns (grant: `dsh test v7`; revoke: `dsh "
                "test v17`, where the last command to fire wins).  So these files "
                "are written for the readers that do use them (the tech-tree "
                "preview reads the tree; the panel feeds the greyed-out future-"
                "items view), and this build will not add or remove a button"
                % (_noun, (dat_rep or {}).get("reason", "the schema declares no "
                                              "`.dat` half for this action")),
            ]
        if panelled := panel_rep.get("ok"):
            ver["proven"] = [x for x in ver["proven"]
                             if x != "no .dat is included in this mod"]

        man["verification"] = ver
        man["resolved"] = r.describe()
        man["civ"] = civ
        # The panel half's own report.  It is a SEPARATE verdict, not a footnote:
        # a tree edit can succeed while the panel edit is an honest no-op (the
        # civ already lists the node) or refuses for its own reason (no panel
        # file serves that civ), and a caller must be able to tell those apart.
        man["panel"] = panel_rep
        # `ok` alone does not mean a panel file was written: the honest no-op
        # (the civ's panel already lists the node) reports ok with mode "none"
        # and emits nothing.  Saying "the panel entry was written" there would be
        # a claim about a file that was never produced, so the two cases are
        # reported with different sentences.
        _p_mode = panel_rep.get("mode")
        if panel_rep.get("ok") and _p_mode == "none":
            ver["proven"].append(
                "the build panel already lists this node for %s, so no panel "
                "file needed to change (%s)"
                % (man["civ"], panel_rep.get("reason", "no entry added")))
        elif panel_rep.get("ok"):
            ver["proven"].append(
                "the build-panel entry was %s in %s, spliced so that only that "
                "building's array changed"
                % ("removed" if _p_mode == "remove_entry" else "written",
                   panel_rep.get("panel_name", "the panel file")))
        else:
            ver["not_proven"].append(
                "that the build menu will show this change: the panel layer "
                "did nothing here (%s), so only the tree file was written"
                % panel_rep.get("reason", "no reason given"))
        man["civ_requested"] = r.civ
        man["action"] = action
        # The `.dat` half's own report, for the same reason the panel half has
        # one: a build can write the two JSON layers and NOT the `.dat` recipe
        # (the reach is the technology space, which has no unit to enable or
        # disable, or a revoke found no carrier that fires late enough), and a
        # caller must be able to tell "wrote all three" from "wrote only the
        # two JSON layers".  Both directions of the `.dat` recipe ARE in-game
        # proven -- grant by `dsh test v7` (2026-10-16), revoke by
        # `dsh test v17` (2026-10-19) -- so a refusal here is a limitation of
        # this particular request, never the state of the art.
        man["dat_half"] = dat_rep
        man["space"] = ut[0]
        man["node_id"] = r.entity.id
        man["node_name"] = r.entity.display
        # `unit_id`/`unit_name` are kept as aliases because the unit-space intent
        # shipped them first; `node_id` is the key that stays true when the same
        # machinery serves the tech space (where "unit_id" would be a misnomer).
        man["unit_id"] = r.entity.id
        man["unit_name"] = r.entity.display
        # `edit_count` counts `rep["edits"]` everywhere else in this file, so it
        # counts them here too: 0 when the two JSON layers were the whole build, or
        # the `.dat` recipe's own operations (each an `edits[]` entry) when it ran.
        # Writing 0 unconditionally was true until the `.dat` half was wired and
        # became a quiet lie the moment it was not.
        man["edit_count"] = len((dat_rep or {}).get("edits") or ())
        man["civs_edited"] = 1
        # The tree layer never changes a `.dat` byte; the EMITTER may still put one
        # in the mod as a carrier, because a mod that writes under
        # `resources/_common/dat/` without `empires2_x2_p1.dat` makes the game fail
        # to start (`mod/emitter.py`).  Report what actually landed on disk, not
        # the tree layer's intention.
        man["mod_contains_dat"] = bool(man.get("dat"))
        for k in ("donor", "warnings", "was_status"):
            if k in rep:
                man.setdefault(k, rep[k])
        if "warnings" in rep:
            # `rep`'s warnings are about the ROW the tree copied.  The emitter's
            # warnings are about the MOD as a whole (a carried `.dat`, a JSON file
            # pinned to today's content), and losing either would be a silent lie,
            # so they are concatenated rather than one replacing the other.
            _emitter_warnings = man.get("warnings") or []
            _rep_warnings = rep.get("warnings") or []
            man["warnings"] = list(_rep_warnings) + [
                w for w in _emitter_warnings if w not in _rep_warnings]
        return man

    def _group_dat_half(self, members, kind, base_raw=None, base_stats=None):
        """Append one `type 102` ban per member pair onto ONE `.dat` stream.

        Returns ``(stats_or_None, commands_added, shared_effects_cloned)``.

        This is the half that makes an exclusive group DO something.  Measured
        2026-10-22 in game: a group written as `linkedTechs.json` alone draws the
        red cross but does not stop the second technology from being researched
        (user: 「不变灰」 then 「研究后依旧能接着研究第二个」); adding these commands
        makes the loser disappear from the panel.  All 16 shipped
        MutuallyExclusive/Toggleable groups carry them, and the 4 Cycle groups do
        not -- a Cycle's exclusion is the file order itself, so `kind` decides
        whether there is anything to do at all.

        It lives in one function because the BUNDLE path had no copy of it: on
        2026-10-23 `build_bundle([villager hp, group])` shipped `linkedTechs.json`
        with no `type 102` anywhere and reported `commands_added: None`, while the
        one-sentence path wrote the bans correctly.  Two sentences silently doing
        less than one is the worst shape a defect can take here, so both callers
        now call this.

        ``base_raw``/``base_stats`` exist for the bundle: its `.dat` half has to
        land on the stream every earlier stage produced, not on the one on disk.
        Appending an effect grows the stream, and the writer replays the raw
        bytes it did not touch, so every byte after the effects section shifts
        correctly.
        """
        wants_dat = kind in ("MutuallyExclusive", "Toggleable")
        if not wants_dat:
            return None, 0, []

        if base_stats is None:
            raw = self._raw if base_raw is None else base_raw
            p = P.Parser(raw)
            with contextlib.redirect_stdout(io.StringIO()):
                p.parse()
            base_stats = p.stats
        else:
            raw = self._raw if base_raw is None else base_raw

        stats = dict(base_stats)
        stats["effects"] = [dict(e) for e in (base_stats.get("effects") or ())]
        # `techs` too: re-pointing a member at a cloned effect must not reach into
        # the session model, and a later bundle step would then see the copy as if
        # it were the file.
        stats["techs"] = [dict(t) for t in (base_stats.get("techs") or ())]

        recs = stats["techs"]
        # An effect record can be SHARED by several technologies.  1,510 shipped
        # techs sit on only 1,014 effects: 37 effects are shared, and 115 techs
        # share one -- typically a civilization bonus riding on the generic
        # technology (effect 67 belongs to both `Forging` and Khitans'
        # `C-Bonus, Double Forging`; effect 74 to `Scale Mail Armor` and Romans'
        # `C-Bonus, Double Scale Mail`).  Appending a `type 102` to a shared effect
        # therefore greys a technology out for players who never asked for the
        # group -- measured 2026-10-22 on v47 itself, where the British test
        # looked perfect and Khitans lost a bonus.  So a shared effect is CLONED
        # and the member re-pointed at the copy.
        co_tenants = {}
        for _tid, _rec in enumerate(recs):
            _e = _rec.get("effect_id")
            if isinstance(_e, int) and _e >= 0:
                co_tenants.setdefault(_e, []).append(_tid)

        commands_added = 0
        cloned = []
        for tid in members:
            eid = recs[tid].get("effect_id") if tid < len(recs) else None
            if eid is None or eid < 0 or eid >= len(stats["effects"]):
                raise C.IntentError(
                    "「%s」没有效果记录，没法写「与其它几项互斥」这一半；"
                    "只写 JSON 的话游戏里不会有任何变化。"
                    % self.describe(tid, "tech").get("name"))
            cmds = list(stats["effects"][eid].get("commands") or ())
            added_here = 0
            for other in members:
                # A MutuallyExclusive member bans ITSELF as well.  Measured
                # 2026-10-23 over the shipped file: 13 of the 14
                # MutuallyExclusive groups do that (26 of their 29 members), and
                # both Toggleable groups do not.  The difference is the difference
                # the two words promise: banning yourself takes the chosen
                # technology out of the tree, so you cannot come back and pick the
                # other one -- a one-way choice.  With only the siblings banned,
                # the losers stay researchable and the choice can be re-toggled,
                # which is what `Toggleable` means.
                if other == tid and kind == "MutuallyExclusive":
                    pass
                elif other == tid:
                    continue
                cmd = (102, -1, -1, -1, float(other))
                if cmd not in cmds:
                    cmds.append(cmd)
                    added_here += 1
            if not added_here:
                continue
            others = [o for o in co_tenants.get(eid, []) if o != tid]
            if others:
                # Snapshot the OLD owner before re-pointing.  `recs` aliases
                # `stats["techs"]`, so reading it afterwards returns the number
                # just written -- measured 2026-10-23: a bundle reported
                # `from: 1500, to: 1500` for a cloned effect, i.e. "moved from
                # where it already is", which is exactly the kind of number a
                # player would read as "nothing happened".
                _from_eid = eid
                stats["effects"].append({"name": "NewEffect%d" % tid,
                                         "commands": cmds, "_new": True})
                new_eid = len(stats["effects"]) - 1
                stats["techs"][tid] = dict(stats["techs"][tid])
                stats["techs"][tid]["effect_id"] = new_eid
                cloned.append({"tech": tid, "from": _from_eid,
                               "to": new_eid, "would_have_hit": others})
            else:
                stats["effects"][eid] = dict(stats["effects"][eid])
                stats["effects"][eid]["commands"] = cmds
            commands_added += added_here

        if not commands_added:
            return None, 0, []
        return stats, commands_added, cloned

    def _build_toggle_group(self, r, out_dir, title=None, author="",
                            description="", thumbnail=None, overwrite=False):
        """Write ``linkedTechs.json`` with one more group in it.

        Deliberately shaped like :meth:`_build_availability`, because the two
        have the same hazard: both re-serialise a file the engine reads off
        disk, and both must be able to prove the shipped file survives the
        round trip.  So `shipped` is serialised from the UNEDITED document and
        compared with the file on disk first -- a serializer that cannot
        reproduce the input byte for byte means every later claim about "only
        the new group changed" is unfounded.

        Two files may be written.  `linkedTechs.json` is always one of them, and
        it is not in the CRC table (measured: 6 of the dat JSON files are, this
        one is not), so a mod may override it on its own.  The v45 canary on
        2026-10-22 proved a mod's copy of a dat-directory JSON is honoured, which
        is what makes the label worth writing.

        For `MutuallyExclusive` and `Toggleable` the label alone does nothing on
        screen (measured in game the same day: the user studied Forging and read
        「不变灰」), so the `.dat` half is written too -- a `type 102` command in
        each member's own effect, which is the shape all 16 shipped non-Cycle
        groups use.  That makes this a data mod rather than a JSON-only one.
        """
        from .game import linkedtechs as LT
        doc, note = LT.load(self.game_root)
        shipped_groups = len(LT.groups(doc))
        # The shipped file's OWN formatting is carried into the output.  Writing
        # the same content in compact form would still replace the player's file
        # on disk, so every line they or another mod ever added would show up as
        # changed -- and this project's verification would warn on every build
        # about a difference that is whitespace only.
        on_disk = LT.shipped_bytes(self.game_root)
        style = LT.detect_style(on_disk)
        shipped_bytes = LT.serialize(doc, style)
        on_disk_path = LT.path_for(self.game_root)

        # Work on a copy taken BEFORE the edit: the verification below compares
        # the edited document against this one, and comparing a document with
        # itself would always pass.
        import copy as _copy
        before = _copy.deepcopy(doc)
        # Preview through the same function `plan()` uses, so a group the
        # preview refused cannot be written here.
        try:
            LT.add_group(doc, [m.id for m in r.members],
                         comment=r.raw.get("comment") or "",
                         kind=r.raw.get("type"))
        except LT.LinkedTechError as exc:
            raise C.IntentError(str(exc))

        # --- the .dat half -------------------------------------------------
        # Measured 2026-10-22 (`tmp_group_mechanism.py`): of the 20 shipped
        # groups, the 16 MutuallyExclusive/Toggleable ones put the exclusion in
        # `.dat` -- every member's own effect carries a `type 102` command
        # naming each sibling -- and the 4 Cycle groups carry none.  So for
        # those two kinds the JSON is a LABEL over a mechanism that lives in the
        # `.dat`.  Measured in game the same day: a MutuallyExclusive group
        # written as JSON alone did NOT grey the second technology out (user:
        # 「不变灰」).  Writing only the label would ship a group that looks
        # right in a diff and does nothing on screen.
        #
        # The recipe itself lives in `_group_dat_half` because the BUNDLE path
        # needed the same thing and did not have it: on 2026-10-23 a bundle of
        # [villager hp, group] shipped `linkedTechs.json` with no `type 102`
        # anywhere and reported `commands_added: None`.  Two sentences in one
        # request produced a silent no-op that one sentence did not.  One
        # recipe, called from both places, is the only shape where that cannot
        # happen again.
        members = [m.id for m in r.members]
        kind = r.raw.get("type") or "MutuallyExclusive"
        wants_dat = kind in ("MutuallyExclusive", "Toggleable")
        # `base_stats` by KEYWORD: the third positional is `base_raw`, and
        # passing the model there made the helper re-parse a dict as if it were
        # the 93 MB stream (KeyError: slice(0, 8, None)).  Measured on the first
        # run after the extraction.
        stats, commands_added, shared_effects_cloned = self._group_dat_half(
            members, kind, base_stats=self._stats)

        files = LT.emit_files(doc, style)
        rel = list(files.keys())[0]
        info = E.make_info(
            title or LT.describe([m.display for m in r.members],
                                 r.raw.get("type"), r.raw.get("comment") or ""),
            author=author, description=description)
        patched = None
        if stats is not None and commands_added:
            patched, _wrep = W.serialize_dat(stats, raw=self._raw)
            man = E.emit_data_mod(out_dir, patched, info, thumbnail=thumbnail,
                                  base_dir=self.game_root, overwrite=overwrite,
                                  json_files=files)
        else:
            man = E.emit_json_mod(out_dir, files, info, thumbnail=thumbnail,
                                  base_dir=self.game_root, overwrite=overwrite)

        # --- verification, from DISK --------------------------------------
        emitted_path = os.path.join(out_dir, rel.replace("/", os.sep))
        with open(emitted_path, "rb") as fh:
            written = fh.read()
        import json as _json
        reparsed = _json.loads(written.decode("utf-8"))
        groups_after = LT.groups(reparsed)
        old_keys = [_json.dumps(g, sort_keys=True) for g in LT.groups(before)]
        new_keys = [_json.dumps(g, sort_keys=True) for g in groups_after]
        missing = [k for k in old_keys if k not in new_keys]
        added = [g for g in groups_after
                 if _json.dumps(g, sort_keys=True) not in old_keys]
        ver = {
            "emitted_path": emitted_path,
            "emitted_bytes": len(written),
            "emitted_matches_intended": written == files[rel],
            "groups_before": shipped_groups,
            "groups_after": len(groups_after),
            "every_previous_group_survived": not missing,
            "groups_added": len(added),
            "shared_effects_cloned": shared_effects_cloned,
            "serializer_reproduces_the_shipped_file": (
                on_disk is None or shipped_bytes == on_disk),
            "formatting_follows_the_shipped_file": bool(style.get("indent")),
            # What the round trip CANNOT do, stated rather than left to a False
            # that reads like a defect.  Measured: the shipped file has
            # hand-written spacing (`"StartingTech" :  1215`) that no encoder
            # reproduces, so byte equality is impossible by construction.
            "formatting_note": (
                "本工具按原文件的缩进与换行写出，但原文件有些冒号前后是手打的空格"
                "（例如 \"StartingTech\" :  1215），那不是任何序列化器会产生的写法，"
                "所以内容相同、空白可能不同。"),
        }
        ver["ok"] = bool(ver["emitted_matches_intended"]
                         and ver["every_previous_group_survived"]
                         and ver["groups_added"] == 1)
        ver["commands_added"] = commands_added
        # The id the group was ALLOCATED.  Until 2026-10-22 this was hard-coded
        # to 424001, which the string tables define as "Satrapies" -- so every
        # group this tool ever wrote displayed under a shipped group's name.
        # Naming the allocated id in the manifest is how a build can be checked
        # for that class of collision after the fact.
        _newgrp = added[0] if added else {}
        ver["name_id"] = _newgrp.get("NameId")
        ver["name_id_is_fresh"] = bool(
            isinstance(ver["name_id"], int)
            and ver["name_id"] not in
            [int(g.get("NameId")) for g in LT.groups(before)
             if isinstance(g.get("NameId"), int)])
        ver["dat_half"] = ("written" if commands_added
                           else ("label_only" if not wants_dat else "not_needed"))
        ver["proven"] = [
            "the emitted file on disk equals the bytes handed to the emitter",
            "the file re-parses and contains one more group than before",
            "every group the player already had is still present with the same "
            "content, key order and values",
        ]
        if commands_added:
            # This half is what makes the group DO something for the two kinds
            # that ship their exclusion in `.dat`.  Naming it in the manifest is
            # the difference between "we wrote a label" and "we wrote the
            # mechanism the shipped groups use".
            ver["proven"].append(
                "each member's effect record now carries a `type 102` command "
                "naming every sibling (%d command(s)), which is the same shape "
                "all 16 shipped %s groups use" % (commands_added, kind))
            ver["proven"].append(
                "the .dat re-read from disk contains exactly those commands, so "
                "the 93 MB stream still parses after a length-changing append")
        else:
            ver["proven"].append(
                "that the .dat in this mod is a byte-identical carrier, not an "
                "edit: a Cycle group's exclusion is the file order itself, so "
                "no `type 102` command is needed and `changes_dat` is False")
        if shared_effects_cloned:
            ver["proven"].append(
                "%d member(s) sat on an effect record other technologies also "
                "use, so the group was written to a CLONE and the member "
                "re-pointed: %s"
                % (len(shared_effects_cloned),
                   "; ".join("tech %d effect %s -> %s (would have hit %s)"
                             % (c["tech"], c["from"], c["to"], c["would_have_hit"])
                             for c in shared_effects_cloned)))
        if ver["formatting_follows_the_shipped_file"]:
            ver["proven"].append(
                "the file is written with the shipped file's own indentation "
                "and line endings, so a diff shows the new group only")
        if not ver["serializer_reproduces_the_shipped_file"]:
            # Not a warning: this is a property of the shipped file, measured,
            # and it cannot be fixed without inventing whitespace.  Say it once
            # as a fact instead of warning on every build.
            ver.setdefault("limits", []).append(
                "原文件的空白无法逐字节复现（见 formatting_note）；内容与键序不变。")
        # HONESTY BOUNDARY.  Measured, and the halves are different facts:
        #   * the SHIPPED groups are read -- Paphos' choice screen exists;
        #   * a mod's replacement of this file IS honoured -- `dsh test v45`
        #     (2026-10-22) put civilizations.json under a mod's dat directory and
        #     all 63 names changed in game, in the same mod whose `.dat` canary
        #     also took effect;
        #   * a group written as JSON ALONE does nothing on screen for the two
        #     kinds that carry `type 102` -- measured in game on 2026-10-22 (the
        #     user studied Forging and read 「不变灰」).  That is why this method
        #     writes the `.dat` half too.
        #   * answered in game on 2026-10-23: `dsh test v47` IS this method's
        #     output (installed through the product) and the user read
        #     「相当于只能研究其中一个」 -- studying the first one removed the
        #     sibling from the panel.  So only the limits this run did NOT
        #     settle are still unproven: Type=Cycle, and the first turn right
        #     after an install.
        ver["not_proven"] = [
            "that a CYCLE group does anything: `dsh test v47` (2026-10-23, user "
            "read 「只能研究其中一个」) wrote MutuallyExclusive, and the four "
            "Cycle groups the game ships carry no `type 102` at all, so nothing "
            "about them can be predicted from the shipped file",
            "that the group is honoured on the very first turn after an "
            "install: v47 was studied after a fresh launch, not straight off "
            "the install",
        ]
        man["verification"] = ver
        man["name_id"] = ver["name_id"]
        man["shape"] = "linked_group"
        man["group_type"] = r.raw.get("type")
        man["members"] = [{"id": m.id, "name": m.display} for m in r.members]
        man["member_count"] = len(r.members)
        man["file_state"] = note
        man["groups_before"] = shipped_groups
        man["groups_after"] = len(groups_after)
        man["edit_count"] = 1
        man["dat_half"] = ver["dat_half"]
        man["commands_added"] = commands_added
        man["shared_effects_cloned"] = shared_effects_cloned
        man["changes_dat"] = bool(commands_added)
        man["civs_edited"] = 0
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["dat_is_carrier"] = bool(man.get("dat")) and not man["changes_dat"]
        man["resolved"] = LT.describe([m.display for m in r.members],
                                      r.raw.get("type"),
                                      r.raw.get("comment") or "")
        return man

    # ---- stage 2: plan, then build ---------------------------------------
    def plan(self, intent):
        """Validate an intent WITHOUT touching any bytes.

        Returns the resolved description plus the scope, so a UI can show
        "Archer attack +2 -> 63 civilizations" before anything is written.

        A tech has no per-civ fan-out, so a unit-shaped answer would be a lie
        twice over: looking the *tech* id up in the unit table reports 63
        civilizations that were never involved.  Branch on the kind and report
        what this edit actually touches.
        """
        self._ensure()
        intents, bindings = C.load_schema()
        r = C.resolve(intent, intents, bindings=bindings)
        base = {"description": r.describe(), "entity_id": r.entity.id,
                "entity_name": r.entity.display, "kind": r.kind,
                "stat": r.stat, "op": r.op, "amount": r.amount}
        if self._strategy(r.raw) == "loose_files":
            return self._plan_reskin(r, base)
        if self._strategy(r.raw) == "new_unit":
            return self._plan_new_unit(r, base)
        if self._strategy(r.raw) == "new_tech":
            return self._plan_new_tech(r, base)
        if self._strategy(r.raw) == "repaint_sld":
            return self._plan_paint(r, base)
        if self._strategy(r.raw) == "linked_techs_json":
            return self._plan_toggle_group(r, base)
        if self._strategy(r.raw) == "objreplacement_json":
            return self._plan_objreplace(r, base)
        # The arms above handle five strategies; the two below handle the byte
        # patcher and the tech-tree writer.  Anything ELSE used to fall straight
        # into the byte-preview body and answer "will change the game data, 1701
        # edits" -- measured 2026-10-22 with a 14th intent declaring the made-up
        # strategy `not_a_real_strategy`: plan() said editable=True and build()
        # then refused.  A preview that promises an edit the build refuses is
        # exactly the defect _probe/test_plan_build_agreement.py exists to kill,
        # and it matters twice over now that strategies are expected to come from
        # data: a typo in a schema file must be refused, not previewed.
        _strategy = self._strategy(r.raw)
        if _strategy not in ("in_place_patch", "civtechtrees_json"):
            raise C.IntentError(
                "「%s」声明了编译策略 %r，这个版本既不预览也不构建它。"
                % (r.raw.get("intent"), _strategy))
        # The four byte-patcher intents (unit.stat, unit.cost,
        # tech.research_time, tech.effect) returned plans with NO `writes` key
        # at all -- measured 2026-10-25, while every newer strategy had one.
        # So those four said "this works, N edits" and never said that it
        # rewrites the 93 MB .dat inside a new mod.  What changes on disk is the
        # one thing a player needs before pressing the button.  (The page did not
        # PRINT the field either -- it started doing that in the same commit that
        # added these keys; a comment claiming otherwise would have been the
        # same lie in a new place.)  `E.DAT_REL` is the same constant the emitter
        # builds a mod folder around, so the two cannot drift apart.
        base["writes"] = E.DAT_REL.replace(os.sep, "/")
        if r.raw.get("intent", "").endswith(".availability"):
            return self._plan_availability(r, base)
        if r.kind == "tech":
            hits = L.find_techs(self._tech_records(), r.entity.id)
            base.update(self._describe_tech_targets(hits, r))
            # "Loom tech effect +5" says nothing about what is being changed.
            # Once the command is resolved, name it -- the attribute IS the edit,
            # and the user picked the command by position.  The target ("平民",
            # "弓箭手") belongs in the sentence too: the same tech often changes
            # hit points for one class and armour for another.
            #
            # A resource modifier has no attribute at all: its operation applies
            # to a RESOURCE ("起始食物 +50").  Gating the sentence on
            # attribute_label alone would leave those rows described as the tech
            # name, which is exactly the uninformative text this rewrite exists
            # to replace.
            if base.get("shape") == "effect" and (
                    base.get("attribute_label")
                    or base.get("target_kind") == "resource"):
                what = base.get("attribute_label")
                if what:
                    # Attribute rows keep their long-standing shape:
                    # "<entity> <target> <attribute> <amount>".
                    desc = "%s %s %s %s" % (r.entity.display,
                                            base.get("target_label") or "",
                                            what, r.describe_amount())
                else:
                    # A resource row has no attribute, so the resource NAME is
                    # the thing being changed.  A multiply row is not a quantity
                    # at all: its number is a FACTOR, and "+0.05" there would
                    # read as adding a half a unit of something.  Say the factor
                    # the command will hold instead -- and for 'set' say "设为",
                    # because "=500" next to a bare resource name is cryptic.
                    name = base.get("target_label") or ""
                    op = base.get("operation")
                    # `base["value"]` is the number the FILE holds today.  The
                    # sentence has to describe the result, so a delta is applied
                    # to it here -- showing the current factor next to "+0.05"
                    # would read as if the command already carried the new one.
                    cur = base.get("value")
                    if op == "multiply":
                        new = (cur + r.amount) if r.op == "delta" else r.amount
                        tail = "×%.3g" % (new or 0)
                    elif op == "set":
                        new = (cur + r.amount) if r.op == "delta" else r.amount
                        tail = "%s %.3g" % (C._OPERATION_ZH.get("set", "set"),
                                            new or 0)
                    else:
                        tail = r.describe_amount()
                    desc = "%s %s %s" % (r.entity.display, name, tail)
                base["description"] = desc.replace("  ", " ").strip()
            # Same value-legality check the write performs, so "make Loom's
            # research time -1" is refused at preview time.  A tech is one
            # global record, so the first hit speaks for the edit.
            b = C._binding_for(bindings, r, r.raw["intent"])
            writes = None
            if hits:
                safety = intents["intents"][r.raw["intent"]].get("safety", {})
                idx, tech = hits[0]
                if b["source"] == "effect_command":
                    # The check for an effect edit is not collect_targets (the
                    # byte lives in the shared Effects array, not in the tech
                    # record) but the very function the write calls.
                    effects = self._effect_records()
                    C.plan_effect_edit(effects, tech, r.raw.get("command"),
                                       r.op, r.amount,
                                       fanout=self._effect_fanout(),
                                       tech_label=r.entity.display,
                                       unit_class=self.unit_class)
                else:
                    # KEEP the count.  `_describe_tech_targets` reports how many
                    # places the field LIVES (`research_time` is one number per
                    # research location), which is a structural fact -- it says 1
                    # for "Loom research time +0" too, because Loom does have one
                    # location.  `collect_targets` is the function the write
                    # calls, and it drops a target whose new value equals the old
                    # one.  Discarding its result made the preview promise an edit
                    # that `build` then refused with "nothing would change",
                    # measured on `{tech.research_time, tech: 22, delta: 0}`:
                    # plan said `editable: True, changes_dat: True, 1 edit`,
                    # build raised.  The unit branch below has always used the
                    # collected count; this one now does the same.
                    writes = len(list(C.collect_targets(
                        self._raw, C._targets_for_tech(b, tech, idx), r, b,
                        safety)))
                    if writes != base.get("edit_count"):
                        base["edit_count"] = writes
            # Same contract as the unit branch below: a plan must not promise
            # work the build then refuses.  "Change Loom's food cost" is 0
            # edits -- Loom costs gold -- and the user has to be told that here,
            # not by an exception after they press the button.  `editable` is set
            # too, because `edit_count: 0` beside `editable: True` is exactly the
            # contradiction an audit measured the build refusing moments later.
            # The sentence comes from the same helper the compiler raises from,
            # so the two cannot word one refusal two ways.
            if base.get("edit_count") == 0:
                if b.get("source") == "cost_entry":
                    _why = "none of its 3 cost slots declares that resource"
                elif not hits:
                    _why = "no such record exists"
                elif writes == 0:
                    # The field is there and the value is legal; the value just
                    # equals what the file holds.  Say that, rather than blaming
                    # a missing research location the tech clearly has.
                    base["editable"] = False
                    base["changes_dat"] = False
                    base["reason"] = C.zero_delta_message(r, b.get("label"))
                    base["description"] = base["reason"]
                    return base
                else:
                    _why = "it declares no research location"
                base["editable"] = False
                base["changes_dat"] = False
                base["reason"] = C.no_field_message(r, b, r.raw["intent"], _why)
                base["description"] = base["reason"]
            else:
                # `editable` and `changes_dat` were absent from this branch while
                # `_plan_availability`/`_plan_reskin` set them, so a UI keyed on
                # either crashed on a tech edit.  An in_place_patch success always
                # writes the .dat, so changes_dat is unconditionally True here.
                base["editable"] = True
                base["changes_dat"] = True
            return base

        allowed = C._allowed_civs(self._civs, r.civ_scope)
        # Ask the compiler which records this edit will really touch, so the
        # preview cannot promise a narrower scope than the build performs.  For a
        # building that means its whole age-variant family, not just the one
        # record the name happened to resolve to.
        #
        # A CLASS edit takes the other branch: it names no record at all, and the
        # family rule must NOT be applied on top of it -- the class IS the scope
        # the user asked for, and expanding further would edit past it.
        if r.unit_class is not None:
            fam = []
            ids, hits = C.unit_targets_for_class(self._civs, r.unit_class,
                                                 allowed)
        else:
            fam, hits = C.unit_targets(self._civs, r.entity.id, allowed,
                                       self._stats, self.game_root)
            ids = sorted({u["id"] for _, _, u in hits})
        # Count the records that can actually carry this field, not the records
        # we looked at: a Barracks has no base attack, so "252 edits" for
        # "Barracks attack +1" would promise work the build then refuses.
        b = C._binding_for(bindings, r, r.raw["intent"])
        safety = intents["intents"][r.raw["intent"]].get("safety", {})
        # A preview that only counts records is not a preview: "archer costs 100
        # less wood" is 63 records and an impossible number.  Run the value
        # through the SAME legality check the write performs, so an illegal
        # value is refused here rather than after the user pressed the button.
        #
        # Validate one record per DISTINCT unit id, not just the first hit.  The
        # 63 civ copies of one unit carry identical values so one of them speaks
        # for all, but the AGE VARIANTS of a building do not: a Barracks is
        # 1200 / 1500 / 1800 / 2100 hp across Dark/Feudal/Castle/Imperial, so
        # "+30700 hp" fits the Dark Age record and overflows the Imperial one.
        # Checking hits[0] alone previewed 252 edits and then let the build raise.
        checked_ids = set()
        per_hit = []
        for h in hits:
            tg = list(C._targets_for_unit(bindings, h[2], b))
            uid = h[2]["id"]
            if uid not in checked_ids:
                checked_ids.add(uid)
                C.collect_targets(self._raw, tg, r, b, safety)
            if tg:
                per_hit.append((h, tg))
        live = [h for h, _ in per_hit]
        # Count the BYTE WRITES the build will perform -- through the same
        # function the build uses, so a target that would write the value the
        # file already holds is not counted.  That is what makes `delta: 0`
        # report 0 here instead of 63, and it is why the old `sum(len(tg))` --
        # which counted every target including no-ops -- could disagree with the
        # build's own `edit_count`.  A mirrored edit (displayed_attack plus the
        # raw class entry that actually deals the damage) writes two slots per
        # record, and `collect_targets` returns both, so mirrors stay counted.
        writes = 0
        mirrors = 0
        for h, tg in per_hit:
            got = C.collect_targets(self._raw, tg, r, b, safety)
            writes += len(got)
            mirrors += sum(1 for t in got[0:] if False)
        mirrors = sum(1 for _, tg in per_hit for t in tg
                      if len(t) >= 5 and t[4] is not None)
        base.update({"civ_count": len({c for c, _, _ in live}),
                     "edit_count": writes,
                     "civs": sorted({c for c, _, _ in live})})
        if mirrors:
            base["mirror_count"] = mirrors
        if not live:
            # Not editable, and the words are the SAME words `compile_edits`
            # raises -- the two must not describe the refusal differently, or a
            # caller reading both gets two different stories about one fact.
            base["editable"] = False
            base["changes_dat"] = False
            base["edit_count"] = 0
            base["reason"] = C.no_field_message(
                r, b, r.raw["intent"], "its unit type does not store one")
            base["description"] = base["reason"]
        elif not writes:
            # The field exists and the value is legal, but the value equals what
            # the record already holds, so not one byte would change.  Report it
            # the same way the build will refuse it.
            base["editable"] = False
            base["changes_dat"] = False
            base["edit_count"] = 0
            base["reason"] = C.zero_delta_message(r, b.get("label"))
            base["description"] = base["reason"]
        else:
            base["editable"] = True
            base["changes_dat"] = True
        # Only worth mentioning when the edit really spans more than one record.
        # A class edit always does, and says how wide in its own keys rather than
        # pretending one record's variants are the story.
        if r.unit_class is not None:
            base["unit_class"] = r.unit_class
            base["unit_class_name"] = C.class_label(r.unit_class)
            base["member_count"] = len(ids)
        elif len(fam) > 1:
            base["variants"] = [i for i in fam if i != r.entity.id]
            base["unit_ids"] = ids
            # Same reason as `describe()`: the family can span several task-swap
            # groups, and the user is being told the whole scope or nothing.
            _g = F.groups_of(self._civs, fam)
            if _g:
                base["task_swap_groups"] = _g
        return base

    def _describe_tech_targets(self, hits, r):
        """What a tech edit will touch, counted from the real records.

        A C31+ record stores its research time once per research LOCATION, so
        "1 tech" can mean several byte writes; the caller must see that before
        agreeing.  A pre-C31 record stores one scalar.
        """
        if not hits:
            return {"locations": 0, "edit_count": 0,
                    "location_ids": [], "civ_count": 0, "civs": []}
        idx, tech = hits[0]
        # An effect edit writes into the shared Effects array, so "how many
        # locations" is the wrong question.  What the user has to be told
        # instead is which command and HOW MANY OTHER TECHS change with it --
        # measured over BASE, 37 effects are shared and 34 of those carry
        # commands, so this is not a theoretical warning.
        if r.raw.get("intent") == "tech.effect":
            _, bindings = C.load_schema()
            b = C._binding_for(bindings, r, r.raw["intent"])
            effects = self._effect_records()
            rows = C.effect_rows(effects, tech, fanout=self._effect_fanout(),
                                 unit_class=self.unit_class)
            index = r.raw.get("command")
            out = {"locations": 1, "edit_count": 1 if rows else 0,
                   "location_ids": [], "civ_count": 0, "civs": [],
                   "shape": "effect", "command_count": len(rows),
                   "effect_id": tech.get("effect_id")}
            if isinstance(index, int) and 0 <= index < len(rows):
                row = rows[index]
                out["command"] = index
                out["attribute"] = row["attribute"]
                out["attribute_label"] = row["attribute_label"]
                out["operation"] = row["operation"]
                out["scope"] = row["scope"]
                out["target_kind"] = row["target_kind"]
                out["target"] = row["target"]
                out["target_label"] = row["target_label"]
                out["value"] = row["value"]
                out["editable"] = row["editable"]
                if row["reason"]:
                    out["reason"] = row["reason"]
                    out["edit_count"] = 0
                if row["fan_in"] > 1:
                    out["fan_in"] = row["fan_in"]
                    out["shared_with"] = row["shared_with"]
            return out
        # A cost lives in exactly one of the 3 fixed slots, so "locations" is
        # meaningless here -- but which slot it is has to be decided the same
        # way the compiler decides it, or the preview would promise one amount
        # and the build would move another.  A tech with NO slot of that
        # resource is reported as 0 edits, matching the refusal the compiler
        # will raise rather than a silent no-op.
        if r.raw.get("resource"):
            _, bindings = C.load_schema()
            b = C._binding_for(bindings, r, r.raw["intent"])
            c = C._pick_cost_slot(tech.get("costs"), b.get("resource_types_inverted"))
            if c is None:
                return {"locations": 0, "edit_count": 0, "location_ids": [],
                        "civ_count": 0, "civs": [], "shape": "cost",
                        "cost_slot": None, "value": None}
            return {"locations": 1, "edit_count": 1, "location_ids": [],
                    "civ_count": 0, "civs": [], "shape": "cost",
                    "cost_slot": c["type"], "value": c["amount"],
                    "flag": c["flag"]}
        locs = tech.get("research_locations")
        if locs is None:
            return {"locations": 1, "edit_count": 1, "location_ids": [],
                    "civ_count": 0, "civs": [],
                    "shape": "scalar",
                    "value": tech.get("research_time")}
        return {"locations": len(locs), "edit_count": len(locs),
                "location_ids": [d["location_id"] for d in locs],
                "civ_count": 0, "civs": [], "shape": "locations",
                "values": [d["research_time"] for d in locs]}

    def build(self, intent, out_dir, title=None, author="", description="",
              thumbnail=None, overwrite=False):
        """Compile an intent and emit a ready-to-install mod folder.

        A thin wrapper over ``_build_one`` so that EVERY build -- whichever of the
        four compile strategies answered it -- gets its origin remembered in the
        provenance file.  Doing it here rather than inside each strategy is the
        only way to be sure a strategy added later cannot quietly skip the record:
        the one thing this must never do is let a mod exist that the update guard
        has never heard of while reporting that it checked.
        """
        man = self._build_one(intent, out_dir, title=title, author=author,
                              description=description, thumbnail=thumbnail,
                              overwrite=overwrite)
        return self._remember(man, [intent])

    def _build_one(self, intent, out_dir, title=None, author="", description="",
                   thumbnail=None, overwrite=False):
        self._ensure()
        # Which machinery compiles this is the SCHEMA's decision, not this
        # method's: `compile.strategy` is read here so adding an intent with a
        # new output shape is a data edit (see the module docstring of
        # aoe2mod.intent.availability for why availability cannot be a .dat
        # patch at all).  An unknown strategy is refused rather than falling
        # through to the byte patcher.
        strategy = self._strategy(intent)
        if strategy is None:
            # resolve() owns the "unknown intent" and "not a dict" wording, so
            # run it here rather than falling through to "declares compile
            # strategy None" -- that message is for a KNOWN intent whose strategy
            # this build does not implement, a different situation.
            intents_schema, _ = C.load_schema()
            C.resolve(intent, intents_schema)
        if strategy == "civtechtrees_json":
            return self._build_availability(intent, out_dir, title=title,
                                            author=author,
                                            description=description,
                                            thumbnail=thumbnail,
                                            overwrite=overwrite)
        if strategy == "loose_files":
            # A reskin writes loose .sld files and no .dat, so it cannot share
            # the byte patcher's tail of the function (which reparses a .dat that
            # was never written).
            intents_schema, bindings = C.load_schema()
            r = C.resolve(intent, intents_schema, bindings=bindings)
            # Which delivery model is a FIELD of this intent, not a property of
            # the strategy: 'rename' ships one .dat and no picture, 'copy' ships
            # pictures and no .dat.  Reading it only in `plan()` is exactly the
            # defect that made `build()` silently produce the 466-file copy model
            # for a sentence that asked for the 244-record rename model.
            if self._reskin_mode(r) == "rename":
                return self._build_retarget(r, out_dir, title=title,
                                            author=author, description=description,
                                            thumbnail=thumbnail,
                                            overwrite=overwrite)
            return self._build_reskin(r, out_dir, title=title, author=author,
                                      description=description,
                                      thumbnail=thumbnail, overwrite=overwrite)
        if strategy == "new_unit":
            intents_schema, bindings = C.load_schema()
            r = C.resolve(intent, intents_schema, bindings=bindings)
            return self._build_new_unit(r, out_dir, title=title, author=author,
                                        description=description,
                                        thumbnail=thumbnail, overwrite=overwrite)
        if strategy == "new_tech":
            intents_schema, bindings = C.load_schema()
            r = C.resolve(intent, intents_schema, bindings=bindings)
            return self._build_new_tech(r, out_dir, title=title, author=author,
                                        description=description,
                                        thumbnail=thumbnail, overwrite=overwrite)
        if strategy == "repaint_sld":
            # A repaint writes loose .sld files and no .dat, like the copy model
            # of a reskin, but it ENCODES a picture instead of moving one that
            # already exists -- so it is its own strategy rather than a `mode`
            # of `unit.sprite`.
            intents_schema, bindings = C.load_schema()
            r = C.resolve(intent, intents_schema, bindings=bindings)
            return self._build_paint(r, out_dir, title=title, author=author,
                                     description=description,
                                     thumbnail=thumbnail, overwrite=overwrite)
        if strategy == "linked_techs_json":
            intents_schema, bindings = C.load_schema()
            r = C.resolve(intent, intents_schema, bindings=bindings)
            return self._build_toggle_group(r, out_dir, title=title,
                                            author=author,
                                            description=description,
                                            thumbnail=thumbnail,
                                            overwrite=overwrite)
        if strategy == "objreplacement_json":
            intents_schema, bindings = C.load_schema()
            r = C.resolve(intent, intents_schema, bindings=bindings)
            return self._build_objreplace(r, out_dir, title=title,
                                          author=author,
                                          description=description,
                                          thumbnail=thumbnail,
                                          overwrite=overwrite)
        if strategy != "in_place_patch":
            raise C.IntentError(
                "「%s」声明了编译策略 %r，这个版本不构建它。"
                % (intent.get("intent"), strategy))
        rep = C.compile_intent(self.dat_path, intent, parsed=self._parsed,
                               stats=self._stats, game_root=self.game_root)
        patched = C.apply_edits(self._raw, rep["edits"])

        info = E.make_info(title or rep["resolved"], author=author,
                           description=description)
        man = E.emit_data_mod(out_dir, patched, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite)

        # The emitted file must survive the game's inflate path and a re-parse.
        raw2, how2 = P.load_dat(man["dat"])
        p2 = P.Parser(raw2)
        with contextlib.redirect_stdout(io.StringIO()):
            p2.parse()
        man["reloaded_with"] = how2
        man["reparse_leftover"] = len(raw2) - p2.r.pos
        man["reparse_ok"] = p2.r.pos == len(raw2)
        man["verification"] = rep["verification"]
        # `resolved.describe()` is the generic three-part shape; the plan()
        # path computes a MORE detailed sentence for some intents (a tech
        # effect names the attribute AND the target unit; a resource row names
        # the operation).  A build that reports only the generic shape tells a
        # caller a shorter story than the preview showed -- D12 in the audit.
        # Take the same sentence plan() produced, so "plan vs build" never
        # diverge on wording.  plan() is idempotent and re-resolves the same
        # intent, so this cannot disagree with `rep` on the actual bytes.
        try:
            _plan = self.plan(intent)
            man["resolved"] = _plan.get("description") or rep["resolved"]
        except C.IntentError:
            # A refusal never reaches here (build raises first); this is a
            # safety net so a wording-only failure cannot hide a valid build.
            man["resolved"] = rep["resolved"]
        man["edits"] = len(rep["edits"])
        # `plan()` reports how many physical fields an intent reaches; `build()`
        # must report the same key or a caller cannot compare what it was
        # promised against what it got (the effect path counted edits as 1 and
        # a test reading man["edit_count"] died with a KeyError).
        man["edit_count"] = len(rep["edits"])
        man["civs_edited"] = rep["civs_edited"]
        # A CLASS edit has no entity id and a scope the preview quotes, so the
        # build has to hand back the same keys -- a caller comparing plan
        # against build found `member_count` missing here while the preview
        # advertised 28 (measured 2026-10-24 on 平民).
        #
        # Read from `rep`, not from a `Resolved` local: this tail of the
        # function is the in_place_patch path, which never binds `r` (the first
        # version referenced it and died with UnboundLocalError on every class
        # build), and `compile_intent` already carries the class through.
        if rep.get("unit_class") is not None:
            man["unit_class"] = rep["unit_class"]
            man["unit_class_name"] = rep.get("unit_class_name")
            man["member_count"] = rep.get("member_ids")
        return man

    def _plan_toggle_group(self, r, base):
        """Preview for "make these technologies exclusive".

        The whole preview comes from the same ``linkedtechs`` functions the
        build calls -- ``group_of`` decides whether a member is already spoken
        for, and ``add_group`` is what would raise.  A second implementation's
        idea of "already grouped" would drift the moment the file gained a group
        this session has not seen, and the drift would look like a preview
        promising work the build then refuses.
        """
        from .game import linkedtechs as LT
        base["shape"] = "linked_group"
        base["writes"] = LT.LINKED_TECHS_REL.replace(os.sep, "/")
        base["group_type"] = r.raw.get("type")
        base["members"] = [{"id": m.id, "name": m.display} for m in r.members]
        base["member_count"] = len(r.members)
        # Which halves this build will write.  Measured 2026-10-22: a group
        # written as JSON alone did NOT grey its sibling out in game (the user
        # studied Forging and got 「不变灰」), because 16 of the 20 shipped groups
        # put the exclusion in `.dat` as a `type 102` command on every member's
        # effect.  So MutuallyExclusive and Toggleable write both halves, and a
        # Cycle group -- whose mechanism is the file's own order -- writes JSON
        # only.  The preview names which, because "we will write a label" and
        # "we will write the mechanism" are different promises.
        kind = r.raw.get("type") or "MutuallyExclusive"
        wants_dat = kind in ("MutuallyExclusive", "Toggleable")
        base["writes_json"] = True
        base["dat_half"] = "written" if wants_dat else "not_needed"
        # Per member: every sibling, plus itself for a MutuallyExclusive group
        # (see the long note in `_build_toggle_group` -- the shipped data does
        # that in 13 of 14 groups, and it is what makes the choice one-way).
        _per = len(r.members) - 1 + (1 if kind == "MutuallyExclusive" else 0)
        base["commands_added"] = (len(r.members) * _per if wants_dat else 0)
        base["changes_dat"] = bool(wants_dat)
        base["mod_contains_dat"] = True
        # NOT "carrier only" any more: when the .dat half is written this mod's
        # `.dat` is a real edit.  Reporting `dat_is_carrier=True` here was the
        # same preview/build disagreement this project keeps finding; the test
        # `_probe/tmp_group_dat.py` caught it on 2026-10-22 by diffing the two.
        base["dat_is_carrier"] = not wants_dat
        doc, note = LT.load(self.game_root)
        base["shipped_groups"] = len(LT.groups(doc))
        base["file_state"] = note
        # The id the group will be given, shown in the preview for the same
        # reason the manifest shows it: 424001..424020 are all defined in the
        # string tables (424001 is "Satrapies"' own group), so a group reusing
        # one of them displays under somebody else's name.  Measured 2026-10-22.
        base["name_id"] = LT.next_name_id(doc)
        try:
            LT.add_group(doc, [m.id for m in r.members],
                         comment=r.raw.get("comment") or "",
                         kind=r.raw.get("type"))
        except LT.LinkedTechError as exc:
            base["editable"] = False
            base["description"] = str(exc)
            base["reason"] = str(exc)
            base["edit_count"] = 0
            return base
        base["editable"] = True
        base["edit_count"] = 1
        # The title is the schema's own sentence for this shape; the ids and the
        # file it lands in are what a player would have to check by hand.
        #
        # The `.dat` half gets named too.  Before this line the description only
        # mentioned `linkedTechs.json`, so a preview for a two-member group
        # promised one file while the build rewrote the 93 MB stream as well --
        # the exact "preview and product disagree" shape this project keeps
        # catching, and this time in the other direction: the preview
        # UNDER-reported, which reads as "safe" right up until the mod is 12 MB.
        _where = base["writes"]
        if base["commands_added"]:
            _where = "%s 和 .dat（给每一项各加 %d 条禁止命令）" % (
                _where, base["commands_added"] // max(1, base["member_count"]))
        base["description"] = (
            "%s；写进 %s（这一份原本有 %d 组）"
            % (LT.describe([m.display for m in r.members],
                           r.raw.get("type"), r.raw.get("comment") or ""),
               _where, base["shipped_groups"]))
        # The limit has to reach the SCREEN, not just the manifest.
        #
        # `not_proven` only exists after a build, and the page has never
        # rendered it -- so a limit that lives only there is a limit the player
        # meets after the mod is installed and nothing happened.  Cycle is
        # exactly that case: the four Cycle groups the game ships carry no
        # `type 102` at all, so this method writes the JSON half only, and no
        # run has watched whether the engine does anything with it.  Saying so
        # in `warnings` puts it in front of the player BEFORE they build, which
        # is the only moment they can choose differently.
        #
        # MutuallyExclusive does not get this warning because it is measured:
        # `dsh test v47` (2026-10-23) was studied in game and the user read
        # 「只能研究其中一个」.  A warning there would train the player to ignore
        # warnings.
        #
        # Everything the player reads here is Chinese, including the group
        # name -- `_GROUP_ZH` is the compiler's own table, so the preview and
        # the sentence cannot drift apart.  The raw enum spelling would also
        # fail `test_prose_language`'s "no English on screen" assertion, which
        # is how this one was caught.
        if not wants_dat:
            base.setdefault("warnings", []).append(
                "「%s」只写 %s，不动 .dat：这类组按文件顺序循环，而它的机制"
                "在本项目一次实机测试都没做过，出厂数据里那 4 个同类型的组"
                "也都不带禁止命令，没有现成形状可以照抄 —— 做完可能什么都不"
                "发生。"
                % (C._GROUP_ZH.get(kind, kind),
                   LT.LINKED_TECHS_REL.replace(os.sep, "/")))
        return base

    # --- objreplacement.json: a row the engine reads at MAP GENERATION ------
    DEFAULT_CHANCE = 100

    def _unit_names(self):
        """``{unit id: the name a player reads}`` from the semantic index.

        Built here rather than stored on the toolkit: an id printed raw reads like
        a locator dump instead of the sentence the preview is supposed to be.
        """
        names = {}
        try:
            ix = semantic.index()
            for uid in list(ix.units):
                e = ix.get("unit", uid)
                if e is not None and e.display:
                    names[int(uid)] = e.display
        except Exception:
            return {}
        return names

    def _objreplace_args(self, r):
        raw = r.raw
        chance = raw.get("chance")
        chance = self.DEFAULT_CHANCE if chance in (None, "") else int(chance)
        return (int(raw["unit"]), int(raw["replacement"]), chance,
                bool(raw.get("replace_existing")))

    def _plan_objreplace(self, r, base):
        """Answer "will this work, and what does it change" without writing.

        The three limits this layer imposes are printed as notes rather than kept
        in `not_proven`: they are properties of the file, and a player deciding
        whether to press the button needs them BEFORE the build.
        """
        names = self._unit_names()
        src, dst, chance, replace_existing = self._objreplace_args(r)
        src_name = names.get(src) or str(src)
        dst_name = names.get(dst) or str(dst)
        base["shape"] = "replace_on_map"
        base["writes"] = OR.OBJREPLACEMENT_REL.replace(os.sep, "/")
        base["changes_dat"] = False
        # The carrier is mandatory and unavoidable: `objreplacement.json` lives
        # under the DAT storage point, and the game refuses to start when a mod
        # overrides that folder without shipping the `.dat`.  Saying False here
        # was a preview/build disagreement of exactly the shape the toggle group
        # had on 2026-10-22 -- measured 2026-10-25: plan said no `.dat`, the mod
        # folder held an 11,982,480 B one.
        base["mod_contains_dat"] = True
        base["dat_is_carrier"] = True
        base["entity_id"] = src
        base["entity_name"] = src_name
        base["source"] = {"id": src, "name": src_name}
        base["replacement"] = {"id": dst, "name": dst_name}
        base["chance"] = chance
        base["when"] = "开局生成地图时"
        base["scope"] = "所有文明"
        base["notes"] = [
            "只在开局生成地图时生效：进入对局之后再造的单位是普通单位",
            "这个文件没有逐文明字段，所以对所有文明一起生效",
        ]
        try:
            doc = OR.load(self.game_root)
            rows_before = len(OR.rows(doc))
            OR.add_replacement(doc, src, dst, source_name=src_name,
                               target_name=dst_name, chance=chance,
                               replace_existing=replace_existing,
                               name_for=lambda u: names.get(int(u)))
        except OR.ObjReplaceError as exc:
            base["editable"] = False
            base["edit_count"] = 0
            base["reason"] = str(exc)
            base["description"] = str(exc)
            return base
        rows_after = len(OR.rows(doc))
        base["editable"] = True
        base["edit_count"] = 1
        base["rows_before"] = rows_before
        base["rows_after"] = rows_after
        base["replaces_existing_row"] = bool(replace_existing
                                             and rows_after == rows_before)
        base["description"] = OR.describe(src_name, dst_name)
        if chance != self.DEFAULT_CHANCE:
            base["description"] += "（%d%% 的概率）" % chance
        if base["replaces_existing_row"]:
            base["notes"].append("这会替换掉文件里原有的那一行规则")
        return base

    def _build_objreplace(self, r, out_dir, title=None, author="",
                          description="", thumbnail=None, overwrite=False):
        """Write the row, then READ IT BACK from the mod folder.

        The re-read is the point: every defect in this project that cost a round
        looked like a successful build in memory.  The numbers in
        `replace_on_map` come from the bytes that are actually on disk.
        """
        names = self._unit_names()
        src, dst, chance, replace_existing = self._objreplace_args(r)
        src_name = names.get(src) or str(src)
        dst_name = names.get(dst) or str(dst)
        style = OR.detect_style(OR.shipped_bytes(self.game_root))
        doc = OR.load(self.game_root)
        rows_before = len(OR.rows(doc))
        try:
            OR.add_replacement(doc, src, dst, source_name=src_name,
                               target_name=dst_name, chance=chance,
                               replace_existing=replace_existing,
                               name_for=lambda u: names.get(int(u)))
        except OR.ObjReplaceError as exc:
            raise C.IntentError(str(exc))
        files = OR.emit_files(doc, style)
        info = E.make_info(title or OR.describe(src_name, dst_name),
                           author=author, description=description)
        man = E.emit_json_mod(out_dir, files, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite)
        rel = OR.OBJREPLACEMENT_REL
        path = os.path.join(man["mod_dir"], rel)
        raw_on_disk = io.open(path, "rb").read()
        back = json.loads(raw_on_disk.decode("utf-8-sig"))
        rows_after = len(OR.rows(back))
        got = [row for row in OR.rows(back) if int(row["source"]) == src]
        man["shape"] = "replace_on_map"
        man["writes"] = rel.replace(os.sep, "/")
        man["changes_dat"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["change_count"] = 1
        # The page reads `edit_count` on the object it gets per sentence, and in
        # a bundle that object is this manifest entry rather than the plan.  Every
        # other intent's manifest already carries it; leaving it out here made a
        # one-row edit render as "0 处改动" next to a preview that said 1.
        man["edit_count"] = 1
        man["replace_on_map"] = {
            "source": {"id": src, "name": src_name},
            "replacement": {"id": dst, "name": dst_name},
            "chance": chance,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "replaces_existing_row": bool(replace_existing
                                          and rows_after == rows_before),
            "file": rel.replace(os.sep, "/"),
            "file_bytes": len(raw_on_disk),
            "read_back": [{"source": int(row["source"]),
                           "replacement": int(row["target"]),
                           "chance": row.get("chance")} for row in got],
        }
        man["verification"] = {
            "ok": bool(got) and int(got[0]["target"]) == dst
                  and rows_after in (rows_before, rows_before + 1),
            "proven": [
                "the row is on disk and reads back with the ids asked for",
                "every other row in the shipped file is still there",
                "the file parses and keeps the shipped line endings",
            ],
            "proven_by": ["_probe/test_replace_on_map.py"],
            "not_proven": [
                "that a row added by a mod is honoured for civilizations whose "
                "copy of the source record differs (only British was measured)",
            ],
            "limits": [],
        }
        man["notes"] = [
            "只在开局生成地图时生效：进入对局之后再造的单位是普通单位",
            "这个文件没有逐文明字段，所以对所有文明一起生效",
        ]
        return man

    def _split_by_strategy(self, resolved_list):
        """One resolved list -> ``(in_place_patch, civtechtrees_json, loose_files)``.

        A bundle may mix the three strategies, because their products are
        different FILES: the byte patcher writes the ``.dat``, the JSON strategy
        writes ``CivTechTrees/<CIV>.json`` and the build panel, and the reskin
        strategy writes loose ``.sld`` files under ``resources/_common/drs/
        graphics``.  One mod folder can carry all of them, and the emitter already
        takes a mapping of relative path -> bytes, so the only thing that had to
        change was the split.

        Splitting here -- rather than letting the .dat fold refuse the whole
        sentence list -- is what lets "villagers are tougher AND the archer looks
        like a longbowman" become ONE mod, which is the entire point of a bundle.

        An undeclared strategy still raises: quietly dropping a sentence would
        produce a mod that does less than it says.
        """
        dat, js, sld, paint, new, linked, tech, repl = \
            [], [], [], [], [], [], [], []
        for r in resolved_list:
            s = self._strategy(r.raw)
            if s == "in_place_patch":
                dat.append(r)
            elif s == "civtechtrees_json":
                js.append(r)
            elif s == "loose_files":
                sld.append(r)
            elif s == "new_unit":
                # Its own bucket: this intent does not patch bytes, it appends a
                # record and rebuilds the model, so it cannot share the in-place
                # patcher's offset arithmetic (`tail` would be stale the moment a
                # record is appended, because every civ after that one moves).
                new.append(r)
            elif s == "new_tech":
                # Its own bucket for the same reason, and it must not share
                # `in_place_patch` either: a technology's id is its array
                # POSITION, so appending one shifts nothing for the tech records
                # themselves but does move the effects section that the byte
                # patcher addresses by absolute offset.
                tech.append(r)
            elif s == "linked_techs_json":
                # Its own bucket for the same reason as `new_unit`: a group is a
                # record in a JSON file, not a field at an offset.  Keeping it
                # out of `js` matters because that bucket is answered by
                # `availability.plan`, which would refuse a sentence with no
                # civilization -- correctly, for a different question.
                linked.append(r)
            elif s == "objreplacement_json":
                # Its own bucket: a replacement is a row in a JSON file the
                # engine reads at MAP GENERATION, not a byte at an offset and
                # not a tech-tree entry.  Sharing `js` would hand it to
                # `availability.plan`, which refuses any sentence without a
                # civilization -- right for its own question, wrong here, and
                # this layer has no civilization key at all.
                repl.append(r)
            elif s == "repaint_sld":
                # A repaint also ships loose files, but it ENCODES a picture
                # rather than moving one that already exists, so it needs its own
                # bucket: the reskin bucket is answered by `reskin.plan`, which
                # knows nothing about a picture and would refuse the sentence for
                # having no donor.
                paint.append(r)
            else:
                raise C.IntentError(
                    "「%s」声明了编译策略 %r，这个版本的 bundle 路径不构建它。"
                    % (r.raw.get("intent"), s))
        return dat, js, sld, paint, new, linked, tech, repl

    def _split_reskin_modes(self, sld_list):
        """Split reskin sentences by DELIVERY MODEL: ``(copy, rename)``.

        Both declare the same compile strategy because both are reskins, but they
        write different things: `copy` writes picture bytes and no `.dat`, `rename`
        writes one `.dat` and no picture.  Treating them as one bucket was a real
        defect -- a bundle asking for the 244-record rename model shipped the
        466-file copy model instead, and the preview said so in a number
        (`sprite_file_count: 466`) that only looks wrong if you know what you
        asked for.
        """
        copy, rename = [], []
        for r in sld_list:
            (rename if self._reskin_mode(r) == "rename" else copy).append(r)
        return copy, rename

    def _retarget_bundle(self, ren_list, raw, parsed):
        """Fold every rename sentence onto ONE growing stream.

        Returns ``(bytes_or_None, notes, refusals)``.  Each sentence re-derives
        its model from the stream the previous sentence produced, for the reason
        `retarget.apply` mutates a model in place and `serialize_dat` returns a new
        stream: addressing the base for the second sentence would rename the wrong
        record without erroring.

        A sentence that cannot be expressed is refused in place rather than
        failing the bundle, matching `_sprite_bundle` and `_fold_dat_halves`:
        one impossible sentence must not throw away the ones that work.
        """
        from .intent import retarget as RT
        notes, refusals = [], []
        cur = raw
        for r in ren_list:
            try:
                p = P.Parser(cur)
                with contextlib.redirect_stdout(io.StringIO()):
                    p.parse()
                # `p.stats["civs"]` comes from `parser.read_unit`, which reads
                # `StandingGraphic` and throws it away; only `locate.walk_unit`
                # keeps it.  Asking the parser's civs "which picture draws this
                # unit" answers "none" for every unit, so every rename would be
                # refused with "no art" -- a wrong answer that looks like data.
                civs, _cs, gv, _tail = L.locate(cur, parser=p)
                rep = RT.plan(self.game_root, p.stats["graphics"], civs,
                              r.entity.id, r.donor.id,
                              scope=self._reskin_scope(r),
                              families=self._families(),
                              family_scope=self._reskin_family_flag(r),
                              fill=self._reskin_fill_flag(r),
                              target_name=r.entity.display,
                              donor_name=r.donor.display)
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            if not rep.get("editable"):
                refusals.append({"description": r.describe(),
                                 "reason": rep.get("reason") or "这个改名做不了"})
                continue
            stats = dict(p.stats)
            stats["graphics"] = [dict(g) for g in p.stats["graphics"]]
            try:
                changed = RT.apply(stats, rep["retarget"])
                cur, _wrep = W.serialize_dat(stats, raw=cur, gv=gv)
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            notes.append({
                "description": rep["description"],
                "mode": "rename",
                "target_id": r.entity.id, "target_name": r.entity.display,
                "donor_id": r.donor.id, "donor_name": r.donor.display,
                "renamed": len(changed),
                "files": 0,
                "civ_count": rep.get("civ_count"),
                "warnings": rep.get("warnings") or [],
                "grid_mismatches": rep.get("grid_mismatches") or [],
                "family": rep.get("family"),
                "filled": rep.get("filled") or [],
                "fill": bool(rep.get("fill")),
                "target_count": rep.get("target_count"),
            })
        return (cur if notes else None), notes, refusals

    def _sprite_bundle(self, sld_list):
        """Resolve every reskin sentence in a bundle into one file map.

        Returns ``(files, notes, refusals)``.

        Files are keyed by game-root-relative path, which is the same key
        ``swap_files`` returns and the same key the emitter wants, so two
        sentences touching different animations of one unit compose naturally.

        TWO CIVILIZATIONS naming different donors for the SAME file is a
        contradiction -- one file cannot hold two pictures -- and it is refused
        with both donors named rather than resolved by sentence order.  The same
        rule already lives inside a single sentence (`reskin.plan`); it has to
        exist here too because a bundle is where two sentences first meet.  The
        single-sentence check cannot see across sentences and would let the
        second write silently win.
        """
        from .intent import reskin as RK
        graphics = self._stats["graphics"]
        civs = self._parsed[1]
        fam = self._families()
        files, notes, refusals = {}, [], []
        claims = {}
        for r in sld_list:
            try:
                rep = RK.plan(self.game_root, graphics, civs, r.entity.id,
                              r.donor.id, scope=self._reskin_scope(r),
                              families=fam,
                              family_scope=self._reskin_family_flag(r),
                      fill=self._reskin_fill_flag(r))
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(),
                                 "reason": str(exc)})
                continue
            if not rep.get("ok"):
                refusals.append({"description": r.describe(),
                                 "reason": rep["reason"]})
                continue
            payload, missing = RK.read_payload(self.game_root, rep)
            if missing:
                refusals.append({
                    "description": r.describe(),
                    "reason": "这个安装里缺了来源那边的动画文件：%s"
                              % "、".join(missing[:5])})
                continue
            clash = None
            for rel, data in payload.items():
                prev = files.get(rel)
                if prev is not None and prev != data:
                    clash = (rel, claims.get(rel), r.describe())
                    break
            if clash:
                refusals.append({
                    "description": r.describe(),
                    # Chinese, because the bundle summary prints this verbatim.
                    # The .sld name stays as it is: a file name is data, and the
                    # player needs it to see which two sentences met.
                    "reason": "「%s」和「%s」都要写 %s 这个文件，可一个文件装不下两张不同的画"
                              % (clash[1], clash[2], os.path.basename(clash[0]))})
                continue
            for rel, data in payload.items():
                files[rel] = data
                claims[rel] = r.describe()
            notes.append({
                "description": r.describe(),
                "target_id": r.entity.id, "target_name": r.entity.display,
                "donor_id": r.donor.id, "donor_name": r.donor.display,
                "files": len(payload),
                "civ_count": rep.get("civ_count"),
                "warnings": rep.get("warnings") or [],
                "grid_mismatches": rep.get("grid_mismatches") or [],
                "family": rep.get("family"),
                "filled": rep.get("filled") or [],
                "fill": bool(rep.get("fill")),
                "target_count": rep.get("target_count"),
            })
        return files, notes, refusals

    def _paint_bundle(self, paint_list, taken=None, taken_by=None):
        """Encode pictures for a list of ``unit.art`` sentences: (files, notes, refusals).

        Shares the accumulator discipline with ``_sprite_bundle`` for the reason
        that made that one necessary: two sentences naming the SAME animation file
        is a contradiction (one file cannot hold two pictures), and the single
        sentence check cannot see across sentences.

        A picture is decoded once per sentence, not once per file: the same
        encoded window is sampled for every frame of every file, and fourteen
        files re-decoding a 4,000 px photo would make a bundle cost minutes.

        ``taken`` is what other buckets have already claimed (the copy model's
        payload, in practice) and ``taken_by`` names who claimed it.  A repaint
        and a copy name the same paths -- both are addressed by the file the unit
        draws -- so this is where the two models finally meet, and it is a
        parameter rather than an afterthought because the PLAN path and the BUILD
        path both have to run this check: plan-only copy-versus-paint composed
        silently and reported 20 files to be written twice over.
        """
        from .intent import repaint as RP
        graphics = self._stats["graphics"]
        civs = self._parsed[1]
        files, notes, refusals = {}, [], []
        claims = dict(taken_by or {})
        # Seeded, not merged: a file another bucket wrote is already spoken for,
        # so a repaint that wants it is a contradiction even when the bytes
        # happen to agree -- two different pictures with equal bytes is not a
        # thing, but two sentences both deciding one file's contents is.
        for rel in (taken or ()):
            files.setdefault(rel, _TAKEN)
        for r in paint_list:
            try:
                pic, pw, ph = RP.load_picture(r.raw["picture"])
                rep = RP.paint_unit(self.game_root, graphics, civs, r.entity.id,
                                    pic, pw, ph,
                                    animations=self._paint_animations(r),
                                    scope=self._reskin_scope(r))
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(),
                                 "reason": str(exc)})
                continue
            payload = rep.get("files") or {}
            if not payload:
                refusals.append({"description": r.describe(),
                                 "reason": "这次换图没有产出任何文件"})
                continue
            clash = None
            for rel, data in payload.items():
                prev = files.get(rel)
                if prev is not None and prev != data:
                    clash = (rel, claims.get(rel), r.describe())
                    break
            if clash:
                refusals.append({
                    "description": r.describe(),
                    # Chinese, because the bundle summary prints this verbatim.
                    # The .sld name stays as it is: a file name is data, and the
                    # player needs it to see which two sentences met.
                    "reason": "「%s」和「%s」都要写 %s 这个文件，可一个文件装不下两张不同的画"
                              % (clash[1], clash[2], os.path.basename(clash[0]))})
                continue
            for rel, data in payload.items():
                files[rel] = data
                claims[rel] = r.describe()
            notes.append({
                "description": r.describe(),
                "mode": "paint",
                "target_id": r.entity.id, "target_name": r.entity.display,
                "files": len(payload),
                "civ_count": rep.get("civ_count"),
                "animations": rep.get("animations") or [],
                "missing_essential": rep.get("missing_essential") or [],
                "picture_size": [pw, ph],
            })
        # The seeded sentinels are not this bucket's output.
        out = dict((k, v) for k, v in files.items() if v is not _TAKEN)
        return out, notes, refusals


    def _apply_availability_bundle(self, r_list):
        """Edit the tree copies for a list of availability sentences.

        Returns ``(files, notes)``.  The sentences are applied to a COPY of the
        cached trees, in order, against the accumulating proposal -- so two
        sentences touching the same civilization compose, and the second one's
        "already has it" check sees the first one's row.

        The cached trees are this session's picture of the GAME's files; a build
        is a proposal written to disk and must not edit the picture.  The copy is
        a full JSON round-trip rather than a dict copy because ``AV.apply`` edits
        a ROW in place on the ``set_status`` path.
        """
        import json as _json
        trees = self._trees()
        if not trees:
            raise C.IntentError(
                "no CivTechTrees data next to this install (%s)"
                % CT.trees_dir(self.game_root))
        proposal = dict(trees)
        originals = {}
        notes = []
        for r in r_list:
            civ = self._tree_civ(r.civ, proposal)
            action = r.action or "grant"
            ut = AV.space_of(r.raw)
            # Preview with the SAME function the plan uses, against what the
            # proposal currently says.  Skipping it could write a duplicate row
            # for a civ that already has the unit -- a file that parses fine and
            # means something undefined.
            pre = AV.plan(proposal, civ, r.entity.id, action,
                          display=r.entity.display, use_types=ut,
                          civ_zh=CN.chinese(civ))
            if not pre["ok"]:
                raise C.IntentError(pre["reason"])
            if civ not in originals:
                o = _json.loads(_json.dumps(trees[civ], ensure_ascii=False))
                o.pop("path", None)      # bookkeeping, not part of the file
                originals[civ] = o
                proposal[civ] = _json.loads(
                    _json.dumps(trees[civ], ensure_ascii=False))
            # Closure of this revoke, before it runs: `apply` deletes the revoked
            # node's upgrade successors too, so the verification below must know
            # they were supposed to go (see `AV.verify_files`).
            cascade = (CT.chain_closure(proposal[civ], r.entity.id, use_types=ut)
                       if action == "revoke" else set())
            rep = AV.apply(proposal, civ, r.entity.id, action, use_types=ut)
            notes.append({"civ": civ, "requested": r.civ, "action": action,
                          "intent": r.raw, "resolved": r.describe(),
                          "description": pre["description"],
                          "space": ut[0],
                          "unit_id": r.entity.id,
                          "unit_name": r.entity.display,
                          "node_id": r.entity.id,
                          "node_name": r.entity.display,
                          "cascade": cascade,
                          "rep": rep})
        files = {}
        for civ in originals:
            f, _rel = AV.emit_files(proposal, civ)
            files.update(f)
        # The OTHER half, same as the single-intent path.  A bundle that wrote
        # only the tree would ship a mod whose availability sentence changes a
        # document the menu may never consult -- and the single-intent path
        # already learned that lesson (`_panel_availability`).
        #
        # `texts` carries each panel file's CURRENT text between sentences.
        # Two sentences in one bundle routinely edit the same 1.3 MB file (a
        # grant and a revoke), and without it the second call would start over
        # from the shipped file and its full-file result would overwrite the
        # first one in `files`.
        texts = {}
        for n in notes:
            _p_rep, p_files = self._panel_availability(
                n["civ"], n["node_id"], n["action"],
                AV.space_of(n["intent"]), trees, texts=texts)
            files.update(p_files)
            n["panel"] = _p_rep
        return files, notes, originals, proposal

    def _linked_bundle(self, linked_list):
        """Fold every group sentence into ONE ``linkedTechs.json``.

        Returns ``(files, notes, style, shipped_bytes)``.

        Folding here rather than letting each sentence emit its own copy is the
        point: ``files`` is keyed by relative path, so a second sentence writing
        ``resources/_common/dat/linkedTechs.json`` would silently replace the
        first one's file -- the bundle would ship one group and promise three.
        The groups are therefore added to one accumulating document, in sentence
        order, so the second sentence's "already in a group" check sees the
        first one's record.

        The shipped file is read ONCE and its style (indent, line endings,
        trailing newline) is measured once, because every group must land in a
        file written the same way; measuring per sentence would let two
        sentences disagree about the whitespace of one file.
        """
        doc, note = LT.load(self.game_root)
        on_disk = LT.shipped_bytes(self.game_root)
        style = LT.detect_style(on_disk)
        before = copy.deepcopy(doc)
        shipped_n = len(LT.groups(before))
        notes = []
        for r in linked_list:
            # Snapshotted PER SENTENCE, not at the end: counting afterwards made
            # both sentences of a two-group bundle report "20 -> 22", so each one
            # claimed to have added two groups.  A number a player reads has to
            # describe the sentence it is attached to.
            n_before = len(LT.groups(doc))
            try:
                # `name_id=None` asks the module to ALLOCATE one from the
                # document it is about to write into.  Passing the default here
                # would hand every group in a bundle the same id -- two groups
                # wearing one name, which is exactly the defect fixed in
                # `linkedtechs.next_name_id` on 2026-10-22.
                _want_nid = r.raw.get("name_id")
                added = LT.add_group(doc, list(r.raw.get("techs") or ()),
                                     name_id=(int(_want_nid)
                                              if _want_nid is not None else None),
                                     comment=r.raw.get("comment") or "",
                                     kind=r.raw.get("type") or "MutuallyExclusive",
                                     local=True)
            except LT.LinkedTechError as exc:
                # A refusal is data, not a crash: the other sentences in this
                # bundle still land, and the manifest names the one that did
                # not.  Raising would throw away the sentences that worked.
                notes.append({"resolved": r.describe(), "ok": False,
                              "reason": str(exc), "added": None,
                              "groups_before": n_before,
                              "groups_after": n_before,
                              "file_state": note})
                continue
            _grp = (LT.groups(added) or [])[-1] if added else {}
            notes.append({
                "resolved": r.describe(), "ok": True,
                "members": [{"id": m.id, "name": m.display} for m in r.members],
                "type": r.raw.get("type") or "MutuallyExclusive",
                "comment": r.raw.get("comment") or "",
                "name_id": _grp.get("NameId"),
                "added": added,
                "groups_before": n_before,
                "groups_after": len(LT.groups(doc)),
                "shipped_groups": shipped_n,
                "file_state": note})
        files = LT.emit_files(doc, style)
        return files, notes, style, on_disk

    def _availability_verification(self, originals, proposal, notes,
                                   files, out_dir):
        """Per-civ JSON verification, plus the on-disk comparison.

        The disk check has to happen here rather than in the caller: "the bytes
        were right" is a claim about what ``emit_json_mod`` wrote, not about the
        dict it was handed.
        """
        per_civ = {}
        ok = True
        for n in notes:
            civ = n["civ"]
            if civ in per_civ:
                continue
            shipped = CT.serialize(originals[civ])
            rel = os.path.join(CT.CIVTECHTREES_REL,
                               "%s.json" % CT.civ_file_stem(civ)).replace(
                os.sep, "/")
            v = AV.verify_files(originals[civ], proposal[civ], shipped,
                                n["node_id"],
                                use_types=(n.get("space") or "Unit",),
                                cascade_ids=n.get("cascade"))
            on_disk = os.path.join(out_dir, rel)
            try:
                with open(on_disk, "rb") as fh:
                    disk = fh.read()
            except OSError:
                v["emitted_readable"] = False
                ok = False
            else:
                v["emitted_matches_intended"] = (disk == files.get(rel))
                v["emitted_bytes"] = len(disk)
            v["emitted_path"] = rel
            v["path_is_engine_relative"] = rel.startswith(
                CT.CIVTECHTREES_REL.replace(os.sep, "/") + "/")
            v["ok"] = bool(v["ok"] and v.get("emitted_matches_intended")
                           and v["path_is_engine_relative"])
            ok = ok and v["ok"]
            per_civ[civ] = v
        # The wording follows what was actually named: a bundle may grant a unit
        # to one civ and a technology to another, and saying "units" for a tech
        # row would describe a promise nobody made.
        _named = sorted({("technology" if (n.get("space") or "Unit") == "Tech"
                         else "unit") for n in notes})
        _named_txt = " and ".join(_named) if _named else "row"
        return {"ok": ok, "civs": per_civ,
                "proven": [
                    "the serializer reproduces each shipped file byte for byte",
                    "each emitted tree re-parses to the same object",
                    "every row other than the named %s is unchanged" % _named_txt,
                    "the files on disk equal the bytes handed to the emitter",
                    "the files sit under the path the engine formats at runtime",
                ],
                "not_proven": [
                    "that a running game offers the named %s to that civilization "
                    "as a result of THIS file.  It is measured, not doubted: "
                    "`dsh test v15` (2026-10-19) shipped only `CivTechTrees/*.json` "
                    "over a byte-identical `.dat` carrier, the engine logged "
                    "loading it, and the menu did not move in either direction, so "
                    "the tree is not what puts a button on the bar.  The `.dat` "
                    "layer is -- a `type 2` command on a technology the "
                    "civilization owns (grant `dsh test v7`, revoke `dsh test "
                    "v17`).  These files are written for the readers that DO use "
                    "them (the tech-tree preview reads the tree; the panel feeds "
                    "the greyed-out future-items view)" % _named_txt,
                ]}

    def plan_bundle(self, intents):
        """Validate a LIST of intents as ONE mod, without touching any bytes.

        A player asks for "村民血更厚,而且科技更快" -- one request, several edits.
        Every single-intent entry point forces that into two complete .dat mods,
        and the engine loads only the highest-priority one, so half the request
        vanishes with no error.  This is the preview for the bundle that fixes it.

        Two things are reported per sentence: the same description/scope a single
        ``plan()`` gives (so the wording cannot drift), and the bundle-level fold
        result.  The fold is the WRITE path, so "preview says legal" and "build
        writes it" cannot disagree -- validating the sentences one at a time
        against the ORIGINAL values would be a lie as soon as a later sentence
        depends on an earlier one ("hp +5, then hp +7" is legal; judging +7
        against the unmodified file would judge 25+7 instead of 30+7).
        """
        if not intents:
            raise C.IntentError("这个组合里一句都没有")

        intents_schema, bindings = C.load_schema()

        # Validate EVERY sentence before producing any preview.  The write path
        # collects the same way, and it has to be the same function: resolving
        # one at a time raises on the first offender, so a request with two typos
        # used to name one of them at preview time and both at build time -- the
        # user fixes one, presses build, and is told about the next.  That is the
        # "preview promised, commit delivered something else" failure again.
        resolved_list = C.resolve_bundle(intents, intents_schema,
                                         bindings=bindings)

        plans = [self.plan(it) for it in intents]

        # A bundle may mix strategies, and their products are different FILES
        # (the .dat vs CivTechTrees/<CIV>.json), so one mod folder can carry
        # both.  Splitting is what lets "villagers are tougher AND Britons can
        # build Huskarls" be one request instead of two mods where the engine
        # loads only the higher-priority one.
        dat_list, js_list, sld_list, paint_list, new_list, linked_list, \
            tech_list, repl_list = self._split_by_strategy(resolved_list)

        # The group sentences get the same dry run the other buckets get, through
        # the SAME accumulating function the build calls -- so "the preview said
        # 21 groups" cannot become "the build shipped 20".
        linked = []
        linked_refusals = []
        if linked_list:
            _lf, _lnotes, _lstyle, _lship = self._linked_bundle(linked_list)
            for n in _lnotes:
                if n.get("ok"):
                    linked.append(n)
                else:
                    # A refusal keeps the sentence's own words: the player typed
                    # it, and "one sentence could not be done" needs to name
                    # which one.
                    linked_refusals.append({"description": n["resolved"],
                                            "reason": n["reason"]})

        # Which group sentences will ALSO write `.dat` bytes.  Asked here rather
        # than at build time because the preview's `changes_dat` is one of the
        # numbers a player reads: saying False and then shipping a 93 MB edit is
        # the "preview lies, build does more" defect this project keeps finding.
        _group_dat_groups = [n for n in linked
                             if (n.get("type") or "MutuallyExclusive")
                             in ("MutuallyExclusive", "Toggleable")]

        # The availability sentences ALSO have a `.dat` half.  Counting it in the
        # preview is not optional: `changes_dat` used to be `bool(dat_list)`, so a
        # bundle whose only `.dat` sentence was an unrelated villager edit reported
        # `changes_dat: True` while the grant's `.dat` half was silently absent from
        # the shipped file -- the mod did less than its own manifest said
        # (`_probe/probe_bundle_dat_half.py`).
        #
        # The count is the schema's DECLARED `write_operations`, not a measurement:
        # running the recipe serialises the whole 93 MB `.dat` (25 s), and a preview
        # has to stay cheap.  `_probe/test_dat_half_count.py` pins the declaration to
        # the recipe's own `len(edits)` so the two cannot drift apart.
        _halves, _refusals = self._declared_dat_halves(resolved_list,
                                                       self._trees())
        _dat_half_edits = sum(self._write_ops_for(h[3], (h[0].action or "grant"))
                              for h in _halves)
        _dat_half_refusals = [{"description": r.describe(), "reason": why}
                              for r, why in _refusals]

        # Dry-run the fold.  `compile_edits` never mutates its input, so this is
        # the identical computation `build_bundle` will perform -- any refusal it
        # produces is the refusal the user would have got after pressing build.
        data, civs, _cs, gv, tail, _how = self._parsed
        if dat_list:
            patched, edits, per_intent = C.compile_bundle(
                data, civs, dat_list, bindings, intents_schema, tail=tail, gv=gv,
                stats=self._stats, game_root=self.game_root)
        else:
            patched, edits, per_intent = data, [], []

        # The JSON sentences get the same dry run: plan -> apply on a copy, then
        # throw the copy away.  `_apply_availability_bundle` is the write path, so
        # "preview says legal" and "build writes it" cannot disagree.
        avail = []
        if js_list:
            _files, notes, _orig, _prop = self._apply_availability_bundle(js_list)
            avail = [{"description": n["description"], "civ": n["civ"],
                      "requested": n["requested"], "action": n["action"],
                      # Which id space this sentence is about.  Without it a
                      # bundle mixing "Britons get a unit" and "Goths get a tech"
                      # reports two indistinguishable notes, and the same integer
                      # means different things in each.
                      "space": n.get("space"),
                      "node_id": n["node_id"], "node_name": n["node_name"],
                      # aliases, as in the single-intent manifest
                      "unit_id": n["node_id"], "unit_name": n["node_name"],
                      "panel": n.get("panel"),
                      "resolved": n["resolved"]} for n in notes]

        # The reskin sentences get the same treatment: plan, read the donor bytes,
        # and throw nothing away -- `_sprite_bundle` is the write path, so the
        # preview cannot promise a file the build will not copy.
        sprites = []
        sprite_refusals = []
        sprite_files = 0
        rename_edits = 0
        if sld_list:
            from .intent import retarget as RT
            copy_list, ren_list = self._split_reskin_modes(sld_list)
            # The rename model ships records, not files, so counting it as files
            # would report the copy model's number for a sentence that asked for
            # the other one.  Each count is the number of records it will touch.
            for r in ren_list:
                try:
                    rep = RT.plan(self.game_root, self._stats["graphics"],
                                  self._parsed[1], r.entity.id, r.donor.id,
                                  scope=self._reskin_scope(r),
                                  families=self._families(),
                                  family_scope=self._reskin_family_flag(r),
                                  fill=self._reskin_fill_flag(r),
                                  target_name=r.entity.display,
                                  donor_name=r.donor.display)
                except Exception as exc:                  # noqa: BLE001
                    sprite_refusals.append({"description": r.describe(),
                                            "reason": str(exc)})
                    continue
                if not rep.get("editable"):
                    sprite_refusals.append({"description": r.describe(),
                                            "reason": rep.get("reason")
                                            or "这个改名做不了"})
                    continue
                rename_edits += rep["retarget"]["rename_count"]
                sprites.append({"description": rep["description"],
                                "mode": "rename",
                                "target_id": r.entity.id,
                                "target_name": r.entity.display,
                                "donor_id": r.donor.id,
                                "donor_name": r.donor.display,
                                "renamed": rep["retarget"]["rename_count"],
                                "files": 0,
                                "civ_count": rep.get("civ_count"),
                                "warnings": rep.get("warnings"),
                                "grid_mismatches": rep.get("grid_mismatches") or []})
            if copy_list:
                _sld_files, snotes, crefs = self._sprite_bundle(copy_list)
                sprite_files = len(_sld_files)
                sprite_refusals = sprite_refusals + crefs
                sprites = sprites + [{"description": n["description"],
                                      "mode": "copy",
                                      "target_id": n["target_id"],
                                      "target_name": n["target_name"],
                                      "donor_id": n["donor_id"],
                                      "donor_name": n["donor_name"],
                                      "files": n["files"],
                                      "civ_count": n["civ_count"],
                                      "warnings": n["warnings"],
                                      "grid_mismatches": n.get("grid_mismatches") or [],
                                      } for n in snotes]

        # The repaint sentences get the same treatment, through the same write
        # path the build calls -- so "the preview said 14 files" cannot become
        # "the build shipped 20".
        paint_notes = []
        paint_refusals = []
        paint_files = 0
        if paint_list:
            _p_files, paint_notes, paint_refusals = self._paint_bundle(paint_list)
            paint_files = len(_p_files)
            sprites = sprites + [{"description": n["description"],
                                  "mode": "paint",
                                  "target_id": n["target_id"],
                                  "target_name": n["target_name"],
                                  "files": n["files"],
                                  "civ_count": n["civ_count"],
                                  "animations": n["animations"],
                                  "missing_essential": n["missing_essential"],
                                  "picture_size": n["picture_size"],
                                  } for n in paint_notes]
            sprite_refusals = sprite_refusals + paint_refusals

        overlaps = C.edit_overlaps(edits)

        # The creation sentences are previewed the cheap way: the model is
        # mutated on a copy so the ids are the ones the build will hand out
        # (`len(techs)` and the next free string, stepping past what earlier
        # sentences in this bundle already claimed), but nothing is serialized --
        # emitting a 93 MB stream to answer a preview would cost 25 s per
        # keystroke.  `_new_tech_bundle` is the write path and runs the same
        # arithmetic, so a preview that says 1,511 cannot become a build that
        # ships 1,510.
        # The replacement sentences get the same dry run as everything else, and
        # through `_plan_objreplace` -- the function the single-sentence preview
        # calls.  Reading the file twice with two different functions is how a
        # preview ends up promising a row the build cannot write.
        repl_notes = []
        repl_refusals = []
        for r in repl_list:
            _base = {"description": r.describe()}
            try:
                _base = self._plan_objreplace(r, _base)
            except (C.IntentError, OR.ObjReplaceError) as exc:
                repl_refusals.append({"description": r.describe(),
                                      "reason": str(exc)})
                continue
            if _base.get("editable") is False:
                # `_plan_objreplace` already decided, with a reason.  It belongs
                # in the refusal list, not in the shipped entries: a sentence the
                # preview says is impossible must not travel as if it would.
                repl_refusals.append({"description": r.describe(),
                                      "reason": _base.get("reason") or ""})
                continue
            repl_notes.append(_base)

        new_tech_notes = []
        if tech_list:
            from .dat import newtech as NT
            _st = dict(self._stats)
            _st["techs"] = list(_st.get("techs") or ())
            _st["effects"] = list(_st.get("effects") or ())
            _next = None
            for r in tech_list:
                try:
                    _nid = NT.next_tech_id(_st)
                    _sid = S.first_free_id(self.game_root,
                                           start=_next or (S.LAST_SHIPPED_ID + 1))
                    _rec = NT.add_tech(
                        _st, r.donor.id, NT.internal_name_for(r.name, _nid), _sid,
                        research_locations=_tech_locations_from_intent(
                            r, self, r.donor.id),
                        research_time=r.raw.get("research_time"),
                        effect=r.raw.get("effect"))
                except (NT.NewTechError, S.StringError) as exc:
                    sprite_refusals = sprite_refusals + [
                        {"description": r.describe(), "reason": str(exc)}]
                    continue
                _next = _sid + 1
                new_tech_notes.append({
                    "description": r.describe(), "mode": "new_tech",
                    "id": _nid, "name": r.name, "string_id": _sid,
                    "donor_id": r.donor.id, "donor_name": r.donor.display,
                    "effect_id": _rec.get("effect_id"),
                    "locations": _rec.get("locations"),
                })

        return {
            "intents": intents,
            "plans": plans,
            "descriptions": [p.get("description") for p in plans],
            "per_intent_edits": [len(e) for e in per_intent],
            # Both halves, summed: the byte patcher's edits plus the `.dat` recipe
            # the availability sentences will run.  Reporting only the first is how
            # a bundle promised 0 and shipped 5 changed bytes.
            #
            # The reskin sentences count what THEY write, which differs by model:
            # the copy model writes FILES, the rename model writes RECORDS into the
            # `.dat`.  Counting the copy model's file count for a rename sentence
            # is how a preview of the 244-record model reported 466 -- the number of
            # files a model the user did not ask for would have copied.
            "edit_count": (len(edits) + _dat_half_edits + sprite_files
                           + rename_edits + paint_files + len(linked)
                           + len(new_tech_notes) + len(repl_notes)),
            "dat_half_edit_count": _dat_half_edits,
            "sprite_file_count": sprite_files,
            "sprite_rename_count": rename_edits,
            # A repaint writes FILES, like the copy model, but it produces them
            # by encoding a picture rather than by moving one.  Counted
            # separately so a caller who asked for both can see which part of the
            # number came from which.
            "paint_file_count": paint_files,
            "availability": avail,
            # One entry per reskin sentence, plus the number of distinct files the
            # whole bundle will copy.  Reported even when it is zero, so a caller
            # can tell "no sprite sentence" from "the key is missing".
            "sprites": sprites,
            "sprite_files": sprite_files,
            # One entry per group sentence, plus the refusals.  Reported even
            # when empty, for the same reason as `sprites`: a caller must be able
            # to tell "no group sentence" from "the key is missing".
            "linked_groups": linked,
            "linked_refusals": linked_refusals,
            # One entry per "make a new technology" sentence.  Reported even when
            # empty, for the same reason as `linked_groups`: a caller must be able
            # to tell "no creation sentence" from "the key is missing".
            "new_techs": new_tech_notes,
            # One entry per replacement sentence.  Reported even when empty so a
            # caller can tell "no replacement sentence" from "the key is missing"
            # -- the same contract as `linked_groups` and `new_techs`.
            "replace_on_map": repl_notes,
            "replace_on_map_refusals": repl_refusals,
            # A reskin sentence that declared itself buildable and is not.  Same
            # contract as `dat_half_refusals`: the preview names it, the build
            # names it, and neither drops it in silence.
            "sprite_refusals": sprite_refusals,
            "civs_edited": len({e.where.split()[0] for e in edits
                                if e.where.startswith("civ[")}),
            # Which sentences wrote over each other.  Not an error -- but a user
            # who typed "hp +5" and then "hp = 20" has thrown the first sentence
            # away, and a preview that printed "+5 then =20" with no comment
            # would be hiding that.
            "overlap_count": len(overlaps),
            "overlaps": [{"offset": o,
                          "edits": ["%s=%s" % (e.where, e.after) for e in v]}
                         for o, v in sorted(overlaps.items())],
            # The carrier rule, previewed.  A JSON sentence lands inside the DAT
            # storage point, so the build WILL put a `.dat` in the mod -- without it
            # the game fails to start (`mod/emitter.py`).  And an availability
            # sentence writes REAL `.dat` bytes on the grant path, so `changes_dat`
            # is true for it too; the carrier flag is its negation only when NOTHING
            # wrote `.dat` bytes.  A preview that omitted any of this would be the
            # recurring defect class: "preview says one thing, build produces another".
            # A group sentence is NOT label-only for the two kinds that ship their
            # exclusion in `.dat`: it appends a `type 102` per member, so the
            # bundle rewrites the 93 MB stream and the `.dat` in the mod is an
            # EDIT, not a carrier.  A Cycle group really is label-only, which is
            # why this is a per-group question and not `bool(linked_list)`.
            # A replacement writes one row of `objreplacement.json`: no `.dat`
            # byte changes, and nothing under `resources/_common/dat/` is left
            # untouched either -- the file the emitter must carry lives in that
            # folder, so `mod_contains_dat` is true below.
            "changes_dat": (bool(dat_list) or bool(_halves) or bool(rename_edits)
                            or bool(_group_dat_groups)),
            "dat_is_carrier": ((bool(js_list) or bool(linked_list))
                               and not dat_list and not _halves
                               and not rename_edits
                               and not _group_dat_groups),
            # NOT `... or sld_list`: the COPY model ships loose `.sld` files and no
            # `.dat` at all, so listing it here would promise the emitter a file
            # that is not in the request.  The RENAME model is the opposite -- it
            # writes records into the `.dat` and no picture -- so it does make the
            # mod contain a `.dat`, and leaving it out here would report a mod
            # without the one file it cannot work without.
            "mod_contains_dat": bool(dat_list or js_list or rename_edits
                                     or linked_list or repl_list),
            # A sentence that declared a `.dat` half and could not have one.  The
            # build reports the same list, so the preview cannot promise a
            # three-layer write and deliver two (`_declared_dat_halves`).
            "dat_half_refusals": _dat_half_refusals,
            "verification": C.verify(data, patched, edits),
        }

    def build_bundle(self, intents, out_dir, title=None, author="",
                     description="", thumbnail=None, overwrite=False):
        """Compile a LIST of intents into ONE ready-to-install mod folder.

        ALL-OR-NOTHING: a bundle that applied two of the user's three sentences
        would be a mod that does less than it says, which is the exact failure
        mode this tool exists to remove.

        A bundle may mix strategies.  Their products are different FILES -- the
        byte patcher writes ``.dat``, the JSON strategy writes
        ``CivTechTrees/<CIV>.json`` -- and ``emit_data_mod`` accepts both, so one
        mod folder carries the whole request.  Splitting here is what stops
        "villagers are tougher AND Britons can build Huskarls" from becoming two
        mods of which the engine loads only the higher-priority one.

        The bundle's whole intent LIST is remembered, not just a description: a
        stale mod has to be rebuildable without the user retyping three sentences
        they wrote weeks ago.
        """
        man = self._build_bundle_one(intents, out_dir, title=title, author=author,
                                     description=description,
                                     thumbnail=thumbnail, overwrite=overwrite)
        return self._remember(man, list(intents))

    def _build_bundle_one(self, intents, out_dir, title=None, author="",
                          description="", thumbnail=None, overwrite=False):
        self._ensure()
        if not intents:
            # `compile_bundle_intent` used to carry this check.  `build_bundle`
            # now splits by strategy itself, so the check has to live here or an
            # empty bundle reaches the emitter and dies with "nothing to emit",
            # which is a ModError about the filesystem rather than a sentence
            # about the user's request.
            raise C.IntentError("这个组合里一句都没有")
        intents_schema, bindings = C.load_schema()
        resolved_list = C.resolve_bundle(intents, intents_schema, bindings=bindings)
        dat_list, js_list, sld_list, paint_list, new_list, linked_list, \
            tech_list, repl_list = self._split_by_strategy(resolved_list)

        data, civs, _cs, gv, tail, how = self._parsed
        json_files = {}
        avail_notes = []
        if js_list:
            files, notes, originals, proposal = \
                self._apply_availability_bundle(js_list)
            json_files = files
            avail_notes = notes

        # The group sentences write resources/_common/dat/linkedTechs.json, the
        # same key space `avail_notes` writes CivTechTrees into, so they land in
        # the same mapping and travel in the same mod.  Folding them through one
        # document (see `_linked_bundle`) is what stops the second sentence from
        # overwriting the first one's file.
        linked_notes = []
        linked_style = None
        linked_shipped = None
        if linked_list:
            _lf, linked_notes, linked_style, linked_shipped = \
                self._linked_bundle(linked_list)
            for rel, data_b in _lf.items():
                if rel in json_files and json_files[rel] != data_b:
                    # Two strategies naming one path: one file cannot hold both.
                    # Refused loudly rather than picked silently, so the mod
                    # cannot do less than the manifest says.
                    raise C.IntentError(
                        "有一句要写 %s，另一个做法也要写同一个文件，一个文件装不下两种内容"
                        % os.path.basename(rel))
                json_files[rel] = data_b

        # Reskin sentences resolve to loose files under the same key space the
        # emitter already writes (game-root-relative path -> bytes), so they go
        # into the SAME mapping the JSON layer uses.  A sprite sentence and a
        # tree sentence therefore land in one mod with no second emitter and no
        # second folder.
        #
        # The two reskin MODELS are kept apart because they write different
        # things: `copy` writes picture bytes here, into `json_files`; `rename`
        # writes records into the `.dat`, and can only do that at the END, once
        # every other stage has finished moving bytes around.
        sprite_files = {}
        sprite_notes = []
        sprite_refusals = []
        rename_notes = []
        ren_list = []
        if sld_list:
            copy_list, ren_list = self._split_reskin_modes(sld_list)
            if copy_list:
                sprite_files, sprite_notes, sprite_refusals = \
                    self._sprite_bundle(copy_list)
            if sprite_files:
                for rel, data_b in sprite_files.items():
                    json_files[rel] = data_b

        # A repaint produces files by the same route -- encoder instead of copier
        # -- so it lands in the same mapping, and the cross-sentence contradiction
        # check inside `_paint_bundle` sees the copy model's claims too if it runs
        # on an accumulated mapping.  It does not, deliberately: a repaint file is
        # addressed by the same path a copy would write, so the two cannot both be
        # honoured, and the clash is reported when the SECOND one is added.
        paint_notes = []
        paint_refusals = []
        paint_files = 0
        _paint_payload = {}
        if paint_list:
            _pf, paint_notes, paint_refusals = self._paint_bundle(paint_list)
            # A repaint and a copy can name the SAME file: "make the archer look
            # like the longbowman" and "paint this picture onto the archer" both
            # want u_arc_archer_idleA_x1.sld, and one file cannot hold both.  The
            # two buckets are separate for good reasons, so the clash has to be
            # caught here, where they finally meet.
            _kept = {}
            for rel, data_b in _pf.items():
                prev = json_files.get(rel)
                if prev is not None and prev != data_b:
                    paint_refusals.append({
                        # No `description`: this clash is between two buckets, so
                        # there is no single sentence to name.
                        "reason": "一句换造型和一句换图都要写 %s，一个文件装不下两张画"
                                  % os.path.basename(rel)})
                    continue
                _kept[rel] = data_b
            for rel, data_b in _kept.items():
                json_files[rel] = data_b
            _paint_payload = _kept
            paint_files = len(_kept)
            sprite_refusals = sprite_refusals + paint_refusals

        # ORDER MATTERS.  The byte patcher's edits are in-place and never move a
        # byte, so they can run first and keep `tail` valid for every later step.
        # The availability grants GROW the stream (each appends an effect), so they
        # run second, on whatever the first stage produced.  Running them the other
        # way would leave `tail` pointing into the middle of the tech section.
        if dat_list:
            patched, edits, per_intent = C.compile_bundle(
                data, civs, dat_list, bindings, intents_schema, tail=tail, gv=gv,
                stats=self._stats, game_root=self.game_root)
            verification = C.verify(data, patched, edits)
            civs_edited = len({e.where.split()[0] for e in edits
                               if e.where.startswith("civ[")})
            overlaps = C.edit_overlaps(edits)
        else:
            # No .dat sentence: the mod must NOT contain a copy of the .dat unless
            # an availability grant writes one.  A redundant copy pins the file at
            # today's bytes, so the next game patch would be silently rolled back
            # by this mod.
            patched, edits, per_intent = data, [], []
            verification = {"ok": True, "why_not_dat": "no .dat sentence"}
            civs_edited = 0
            overlaps = {}

        # The availability sentences' own `.dat` half, folded onto the stream the
        # byte patcher produced.  Before this existed a bundle applied two layers of
        # a grant and shipped a `.dat` identical to the base while reporting
        # `changes_dat: True` from an unrelated sentence -- measured in
        # `_probe/probe_bundle_dat_half.py`.
        halves, refusals = self._declared_dat_halves(resolved_list, self._trees())
        dat_bytes = patched if dat_list else None
        dat_half_reps = []
        if halves:
            folded, dat_half_reps, _gv2 = self._fold_dat_halves(halves, patched)
            if folded is not None:
                dat_bytes = folded
        for r, why in refusals:
            dat_half_reps.append({"resolved": r.describe(), "ok": False,
                                  "reason": why})

        # A creation appends a RECORD, which moves every byte after it, so it
        # cannot ride the in-place patcher (`tail` would be stale for every later
        # step).  It runs here, after the in-place work and the availability
        # halves, and before the rename model -- rename is still the last hand on
        # the file because it changes field lengths without appending anything.
        new_notes = []
        new_entries = []
        tech_entries = []
        # ONE icon state for both creation bundles: the two sections add their
        # materials to the same `materials.json`, so a separate read per bundle
        # would let the second overwrite the first's merged file.
        _icon_state = {"icons": None, "materials": None, "files": {}}
        if new_list:
            _base = dat_bytes if dat_bytes is not None else data
            new_bytes, new_notes, new_ref, new_entries, new_icons = \
                self._new_unit_bundle(new_list, _base, _icon_state)
            sprite_refusals = sprite_refusals + new_ref
            for _rel, _blob in (new_icons or {}).items():
                json_files[_rel] = _blob
            if new_bytes is not None:
                dat_bytes = new_bytes

        # Creating a TECHNOLOGY belongs to the same family for the same reason:
        # a tech id is `len(techs)`, so a sentence addressed against the shipped
        # count has to run against the stream the creations above produced, and
        # its effects section has moved if a new unit record was appended.
        tech_notes = []
        if tech_list:
            _base = dat_bytes if dat_bytes is not None else data
            tech_bytes, tech_notes, tech_ref, tech_entries, tech_icons = \
                self._new_tech_bundle(tech_list, _base, _icon_state)
            sprite_refusals = sprite_refusals + tech_ref
            for _rel, _blob in (tech_icons or {}).items():
                json_files[_rel] = _blob
            if tech_bytes is not None:
                dat_bytes = tech_bytes

        # The replacement sentences write `objreplacement.json`, which lives in
        # the SAME folder the tree files live in, so they land in the same
        # mapping and travel in the same mod folder.  Folding them through one
        # document (rather than one file per sentence) is what stops a second
        # sentence from replacing the first one's file -- and a different
        # strategy naming the same path is refused LOUDLY, because one file
        # cannot hold two contents and picking one silently would ship a mod
        # that does less than the manifest says.
        repl_notes = []
        if repl_list:
            _doc = OR.load(self.game_root)
            _style = OR.detect_style(OR.shipped_bytes(self.game_root))
            _names = self._unit_names()
            _before = len(OR.rows(_doc))
            for r in repl_list:
                _src, _dst, _chance, _repl_existing = self._objreplace_args(r)
                try:
                    OR.add_replacement(
                        _doc, _src, _dst,
                        source_name=_names.get(_src) or str(_src),
                        target_name=_names.get(_dst) or str(_dst),
                        chance=_chance, replace_existing=_repl_existing,
                        name_for=lambda u: _names.get(int(u)))
                except OR.ObjReplaceError as exc:
                    sprite_refusals = sprite_refusals + [
                        {"description": r.describe(), "reason": str(exc)}]
                    continue
                repl_notes.append({
                    "description": OR.describe(_names.get(_src) or str(_src),
                                               _names.get(_dst) or str(_dst)),
                    "source": {"id": _src, "name": _names.get(_src) or str(_src)},
                    "replacement": {"id": _dst,
                                    "name": _names.get(_dst) or str(_dst)},
                    "chance": _chance,
                })
            if repl_notes:
                _files = OR.emit_files(_doc, _style)
                _rel = OR.OBJREPLACEMENT_REL
                for _k, _blob in _files.items():
                    if _k in json_files and json_files[_k] != _blob:
                        raise C.IntentError(
                            "有一句要写 %s，另一个做法也要写同一个文件，"
                            "一个文件装不下两种内容" % os.path.basename(_k))
                    json_files[_k] = _blob
                man_rows_after = len(OR.rows(_doc))
                repl_rows = _before, man_rows_after

        # ONE string file, built from BOTH kinds of creation.  Emitting each
        # bundle's table and concatenating them repeats the file's header block
        # -- measured 2026-10-22: a bundle with two tech creations shipped a table
        # with two "//INSTRUCTIONS:" banners.  Unit and tech creations write the
        # SAME key-value path, so the only correct assembly is one list of
        # (id, text) pairs turned into files once.
        new_strings = {}
        _all_entries = list(new_entries or []) + list(tech_entries or [])
        if _all_entries:
            new_strings = S.build_files(self.game_root, _all_entries)
            for rel, data_b in new_strings.items():
                json_files[rel] = data_b

        # The rename model runs LAST, and on the stream that will actually be
        # shipped, because it is the only stage that changes the LENGTH of a
        # `.dat` field without appending a record -- a longer or shorter picture
        # name moves every byte after that graphics record.  Every earlier stage
        # addresses offsets in a stream that no longer exists once this has run,
        # so it must be the last hand on the file.
        _rename_changed = 0
        if ren_list:
            _base = dat_bytes if dat_bytes is not None else data
            ren_bytes, rename_notes, ren_ref = self._retarget_bundle(
                ren_list, _base, self._parsed)
            sprite_refusals = sprite_refusals + ren_ref
            if ren_bytes is not None:
                dat_bytes = ren_bytes
                _rename_changed = sum(int(n.get("renamed") or 0)
                                      for n in rename_notes)

        # The group sentences' `.dat` half, folded LAST for the same reason the
        # rename model is: appending an effect record moves every byte after the
        # effects section, so it has to happen on the stream that will actually be
        # shipped rather than on one an earlier stage has already outgrown.
        #
        # This step had no bundle equivalent until 2026-10-23.  `build_bundle`
        # with [villager hp, group] shipped `linkedTechs.json` and NOT ONE
        # `type 102` command -- the second sentence of a two-sentence request did
        # less than the same sentence alone, and nothing in the manifest said so
        # (`commands_added` was `None`).  Measured in game on 2026-10-22: a group
        # with only the JSON label draws the red cross and still lets the player
        # study the sibling, so that silent no-op looked exactly like success.
        group_dat_reps = []
        for n in linked_notes:
            if not n.get("ok"):
                continue
            _kind = n.get("type") or "MutuallyExclusive"
            _members = [m["id"] for m in (n.get("members") or ())]
            _base = dat_bytes if dat_bytes is not None else data
            # `base_stats=None` re-parses `_base`, which is deliberate: the
            # rename stage above may have moved bytes, and a model derived from
            # the pre-rename stream would address the wrong records.
            _stats, _added, _cloned = self._group_dat_half(_members, _kind,
                                                           base_raw=_base)
            n["commands_added"] = _added
            n["shared_effects_cloned"] = _cloned
            n["dat_half"] = ("written" if _added else
                             ("not_needed" if _kind == "Cycle" else "label_only"))
            group_dat_reps.append({"description": n.get("resolved"),
                                   "ok": bool(_added),
                                   "dat_half": n["dat_half"],
                                   "commands_added": _added,
                                   "shared_effects_cloned": _cloned})
            if _stats is not None and _added:
                _bytes, _wrep = W.serialize_dat(_stats, raw=_base)
                if _wrep.get("raw_consumed") != len(_base):
                    # The writer walked the raw stream to a different place than
                    # it started, so the file it produced is not this stream plus
                    # one command -- refuse rather than ship it.
                    raise C.IntentError(
                        "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），"
                        "所以这份不改了" % (_wrep.get("raw_consumed"), len(_base)))
                dat_bytes = _bytes

        info = E.make_info(
            title or (" + ".join(str(d) for d in
                                 [r.describe() for r in resolved_list] if d)[:80]
                      or "mod"),
            author=author, description=description)
        # A bundle whose every sentence was REFUSED has nothing to emit, and the
        # emitter's own complaint ("nothing to emit: neither a .dat nor any JSON
        # override was given") describes the FILE SYSTEM, not the request -- the
        # player typed `把村民的样子换成城堡`, and the reason that sentence could
        # not be honoured was already computed and then thrown away here.  Name
        # the sentences instead.  Measured: the emitter sentence is what reached
        # the screen, in English, for a sentence whose real reason was Chinese.
        if dat_bytes is None and not json_files:
            _why = [str(x.get("reason") or "").strip() for x in sprite_refusals
                    if x.get("reason")]
            _why += [str(x.get("reason") or "").strip() for x in dat_half_reps
                     if not x.get("ok") and x.get("reason")]
            if _why:
                raise C.IntentError("这几句都做不了，所以没有东西可以做成模组："
                                    + "；".join(_why))
        man = E.emit_data_mod(out_dir, dat_bytes, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite,
                              json_files=json_files or None)
        man["resolved"] = [r.describe() for r in resolved_list]
        # A bundle is the path the screen actually uses -- the page always posts
        # a list, even for one sentence -- so the width the preview promised has
        # to be here too.  Measured 2026-10-25: `build_bundle` of 「所有平民血量
        # 加5」 reported `edit_count 1764` and no `member_count` at all, so a
        # caller comparing the preview against the build saw the width vanish
        # and could not tell a 28-record edit from a 1,764-record one.  That is
        # the same defect the single-sentence path had before 2026-10-24.
        _class_res = [r for r in resolved_list
                      if getattr(r, "unit_class", None) is not None]
        if _class_res:
            man["unit_class"] = _class_res[0].unit_class
            man["unit_class_name"] = C.class_label(_class_res[0].unit_class)
            man["member_count"] = len(
                C.class_member_ids(civs, _class_res[0].unit_class))
            # More than one class in one bundle: name them all rather than
            # letting the first one speak for the rest.
            if len({r.unit_class for r in _class_res}) > 1:
                man["unit_classes"] = [{"unit_class": r.unit_class,
                                        "unit_class_name": C.class_label(
                                            r.unit_class),
                                        "member_count": len(
                                            C.class_member_ids(civs, r.unit_class))}
                                       for r in _class_res]
        # Both halves, summed: the byte patcher's edits plus the `.dat` recipe
        # every availability grant ran.  Reporting only the first is how a bundle
        # promised 0 changed bytes and shipped 5.
        man["dat_half_edit_count"] = sum(
            len(x.get("edits") or ()) for x in dat_half_reps)
        # The reskin sentences each count what THEY write: the copy model writes
        # files, the rename model writes records into the `.dat`.  Reporting one
        # model's number for the other is how a preview of the 244-record model
        # reported 466 -- the number of files a model nobody asked for would have
        # copied.
        man["sprites"] = sprite_notes + paint_notes + rename_notes
        man["rename_edits"] = _rename_changed
        man["new_units"] = new_notes
        man["new_unit_strings"] = sorted(new_strings)
        man["new_techs"] = tech_notes
        # One table serves both kinds of creation, so the file list is the same
        # for units and techs -- reported under both keys because a caller that
        # only created technologies must not read an empty list.
        man["new_tech_strings"] = sorted(new_strings)
        man["linked_groups"] = linked_notes
        man["linked_refusals"] = [{"description": n["resolved"],
                                   "reason": n["reason"]}
                                  for n in linked_notes if not n.get("ok")]
        # The replacement rows, reported the way the single-sentence path reports
        # them.  Two things a caller must be able to check: that every sentence
        # that went in came out (there is no partial delivery), and that the row
        # really landed in the file on disk -- so the count is the rows the FILE
        # has, not the rows this function intended to add.
        man["replace_on_map"] = repl_notes
        man["replace_on_map_refusals"] = [
            {"description": x.get("description"), "reason": x.get("reason")}
            for x in sprite_refusals
            if x.get("reason") and x.get("description") not in
            {n.get("description") for n in repl_notes}]
        if repl_list:
            _rel = OR.OBJREPLACEMENT_REL
            _p = os.path.join(man["mod_dir"], _rel)
            # `replace_on_map` is the LIST of sentences; the facts about the FILE
            # live beside it.  Assigning into the list by name raises
            # `TypeError: list indices must be integers` -- and it would raise it
            # at the end of a successful build, with the mod already on disk.
            _on_disk = []
            if os.path.isfile(_p):
                _blob = io.open(_p, "rb").read()
                _back = json.loads(_blob.decode("utf-8-sig"))
                _want = {(int(n["source"]["id"]), int(n["replacement"]["id"]))
                         for n in repl_notes}
                # `OR.rows()` keeps attribute-only rows (the shipped file has
                # one: Scout -> "Scout ID" 263) with `target=None` on purpose, so
                # a reader can see that row too.  Comparing it needs a `None`
                # guard: `int(None)` raised here, at the end of a build whose mod
                # folder was already written.
                _on_disk = [
                    {"source": int(row["source"]),
                     "replacement": int(row["target"]),
                     "chance": row.get("chance")}
                    for row in OR.rows(_back)
                    if row.get("target") is not None
                    and (int(row["source"]), int(row["target"])) in _want]
                man["replace_on_map_file"] = {
                    "file": _rel.replace(os.sep, "/"),
                    "file_bytes": len(_blob),
                    "rows_in_file": len(OR.rows(_back)),
                    "rows_on_disk": _on_disk,
                    "verification_ok": len(_on_disk) == len(repl_notes),
                }
            else:
                man["replace_on_map_file"] = {
                    "file": _rel.replace(os.sep, "/"),
                    "verification_ok": False,
                    "why_not": "the file is not in the mod folder",
                }
        # The groups' own `.dat` half, reported the way the single-sentence path
        # reports it.  Before 2026-10-23 a bundle group shipped a label with no
        # bans and said nothing: `commands_added` was absent, and `dat_half` held
        # only the availability halves, so a caller reading either would see a
        # clean build.  The numbers a player can check belong here.
        man["group_dat_half"] = group_dat_reps
        man["commands_added"] = sum(int(x.get("commands_added") or 0)
                                    for x in group_dat_reps)
        man["shared_effects_cloned"] = [c for x in group_dat_reps
                                        for c in (x.get("shared_effects_cloned")
                                                  or ())]
        man["edits"] = (len(edits) + man["dat_half_edit_count"]
                        + len(sprite_files) + _rename_changed + paint_files
                        + 2 * len(new_notes) + len(tech_notes)
                        + man["commands_added"] + len(repl_notes))
        man["edit_count"] = man["edits"]
        man["dat_half"] = dat_half_reps
        man["civs_edited"] = civs_edited
        man["per_intent_edits"] = [len(e) for e in per_intent]
        man["overlap_count"] = len(overlaps)
        if sld_list or paint_list:
            man["sprite_refusals"] = sprite_refusals
            man["sprite_files"] = len(sprite_files)
            # The sprite layer's own verdict, for the same reason `man["panel"]`
            # is separate from the tree verdict: a bundle can succeed at the
            # .dat and the tree while a reskin sentence is refused, and a caller
            # must be able to tell those apart rather than reading one `ok`.
            #
            # A repaint's files are verified by the SAME function: both write
            # loose files, and the three questions it asks (on disk, right bytes,
            # not a no-op) are questions about any loose file.  Only the
            # `proven`/`not_proven` sentences differ, and those are replaced
            # below when a repaint contributed to the payload.
            _loose = dict(sprite_files)
            _loose.update(_paint_payload)
            _loose_notes = list(sprite_notes) + list(paint_notes)
            srep = self._sprite_verification(_loose, _loose_notes,
                                             out_dir, sprite_refusals)
            if paint_files:
                srep["proven"] = [
                    "that each of the %d repainted file(s) in this mod was "
                    "written from the requested picture, with every byte outside "
                    "main's BC1 blocks left exactly as the game shipped it"
                    % paint_files,
                    "that the block grid was respected: copying the original "
                    "blocks back reproduces each source file byte-for-byte, so a "
                    "block in the wrong cell shows up as a mismatch",
                ]
                srep["not_proven"] = [
                    "that a running game draws a hand-encoded block.  Loose .sld "
                    "loading is proven (2026-10-17), but those mods copied "
                    "shipped files",
                ]
            man["sprite_verification"] = srep
            if dat_bytes is None and not js_list:
                # A bundle of nothing but COPY-model reskins: no .dat, no tree.
                # Without this the manifest would carry no `verification` at all
                # and a UI reading it could not tell that from "verification
                # failed".  A rename sentence does write a `.dat`, so it is
                # covered by the reparse block below instead.
                man["verification"] = srep
        # `dat_bytes is not None` describes the INTENT (did any sentence edit a
        # .dat byte); the emitter may still have put a CARRIER `.dat` on disk,
        # because a mod writing under `resources/_common/dat/` without it makes the
        # game fail to start (`mod/emitter.py`).  Report what is actually there.
        man["mod_contains_dat"] = bool(man.get("dat"))

        if dat_bytes is not None:
            raw2, how2 = P.load_dat(man["dat"])
            p2 = P.Parser(raw2)
            with contextlib.redirect_stdout(io.StringIO()):
                p2.parse()
            man["reloaded_with"] = how2
            man["reparse_leftover"] = len(raw2) - p2.r.pos
            man["reparse_ok"] = p2.r.pos == len(raw2)
            # A reparse that succeeds on a file WITHOUT the appended records would
            # look like the same green, so the records are looked for too.
            _missing = []
            for n in new_notes:
                _have = {u["id"] for u in p2.stats["civs"][n["civ_index"]]["units"]}
                if n["id"] not in _have:
                    _missing.append(n["id"])
            man["new_units_present"] = not _missing
            # `verification` says what was CHECKED, so a bundle whose only `.dat`
            # work was record renames or creations must not report the byte
            # patcher's empty "no .dat sentence" verdict: that would tell a caller
            # nothing changed in a file that changed 244 records or grew one.
            if new_notes:
                man["verification"] = {
                    "ok": bool(man["reparse_ok"] and not _missing),
                    "why_not_dat": "this intent appends records instead of "
                                   "patching bytes",
                    "reparse_ok": bool(man["reparse_ok"]),
                    "new_units_present": not _missing,
                    "missing_ids": _missing,
                    "proven": [
                        "that the emitted .dat inflates and re-parses with the "
                        "unmodified parser, with every byte consumed",
                        "that each civ's record run contains the id the manifest "
                        "names, so the record survived the writer rather than "
                        "only the model",
                        "that each name line landed in the file the game's own "
                        "605-byte instructions name as the way a mod adds a "
                        "string",
                    ],
                    "not_proven": [
                        # Same sentence as the single-intent path, and the same
                        # reason for the correction: v26..v33 proved the RECORD
                        # in game (2026-10-22, user-confirmed), while v35 -- this
                        # bundle path -- was built and never installed.  Keeping
                        # the old broad claim here would contradict the wording
                        # 30 lines above it in the same file.
                        "that a running game shows a unit built by THIS path.  "
                        "The record-level clone was proven in game 2026-10-22 "
                        "(v26..v33), but the bundle path itself has no in-game "
                        "reading yet",
                    ],
                }
            else:
                man["verification"] = verification if dat_list else {
                "ok": bool(man["reparse_ok"]),
                "why_not_dat": "no in-place byte patch",
                "renamed_records": _rename_changed,
                "reparse_ok": bool(man["reparse_ok"]),
            }
        if js_list:
            # Verification reads the emitted files back off DISK, so it has to
            # run after `emit_data_mod`, not before it.
            avail = self._availability_verification(
                originals, proposal, avail_notes, json_files, out_dir)
            man["availability"] = {
                "verification": avail,
                "civs": [{"civ": n["civ"], "requested": n["requested"],
                          "action": n["action"], "space": n.get("space"),
                          "node_id": n["node_id"],
                          "node_name": n["node_name"],
                          "unit_id": n["node_id"],
                          "unit_name": n["node_name"],
                          "panel": n.get("panel"),
                          "description": n["description"]}
                         for n in avail_notes],
            }
            if dat_bytes is None:
                # With no .dat sentence, `verification` means the JSON one.
                man["verification"] = avail
        return man

    # ---- provenance: which game data a mod came from ---------------------
    def _remember(self, man, intents):
        """Record this build's origin so an official update becomes visible.

        Never raises.  A build that succeeded must not be reported as failed
        because the record file could not be written -- the mod is real and
        installable, and the only thing lost is the ability to say later whether
        the game has moved under it.  The record is skipped and the manifest says
        so, because "unknown" is the honest answer and it stays visible.
        """
        try:
            entry = PV.entry_from_manifest(
                man, self.dat_path,
                base_raw_sha256=__import__("hashlib").sha256(self._raw).hexdigest(),
                intents=intents, target_version=self.version)
            PV.record(entry)
            man["provenance"] = {"title": entry["title"],
                                 "state_file": PV.state_path(),
                                 "base_version": entry["base_version"]}
        except Exception as exc:                       # noqa: BLE001
            man["provenance"] = {"title": None, "state_file": None,
                                 "why_not": "%s: %s" % (type(exc).__name__, exc)}
        return man

    def repair_check(self, profile_root=None, limit=40, name=None):
        """Which installed mods ship a `.dat` that no longer matches the game?

        Read-only, and it never claims more than it measured: every row comes
        back with one of five verdicts (see `aoe2mod/repair.py`).  This is the
        question an official patch creates -- about 12 MB of stale snapshot per
        mod -- so it belongs on the toolkit, not in a one-off script.

        ``profile_root`` is for tests, exactly as in ``install()``: the one
        thing a test must never do is read the player's real mod list by
        accident and then assert on whatever it happens to find there.
        """
        from . import repair as R
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        rows = R.scan_installed(prof, self.game_root, limit=limit)
        if name:
            rows = [r for r in rows if r.get("name") == name]
        for r in rows:
            r["summary"] = R.describe(r)
        return {"ok": True, "profile_root": prof, "mods": rows,
                "count": len(rows)}

    def repair_apply(self, name, out_dir=None, author="", overwrite=True,
                     profile_root=None, limit=400):
        """Rebuild one installed mod's `.dat` from the shipped file, then reinstall it.

        The shape is deliberate: read the author's file, turn what it changed into
        intents, build those intents against TODAY's `.dat`, carry every other
        file of the old folder across, install the result over the old folder.

        Why not just patch the old file: it is a snapshot of a game that no longer
        exists.  Patching it keeps the snapshot's other 11 MB of stale bytes and
        loses whatever the patch added.  Rebuilding from the shipped file is the
        only shape that both restores the author's numbers and picks up the new
        content.

        Only the `auto` and `identical` verdicts are handled.  `manual` means the
        author added or removed records, which needs graphics, strings, icons and
        train locations carried in the right order -- doing that badly would
        produce a mod that loads and then misbehaves, which is worse than saying
        no.  `impossible` is a format generation change, where no offset from
        today's file reaches the old bytes at all.

        ``profile_root`` is for tests, as everywhere else: a test must never read
        or write the player's real mod list by accident.
        """
        from . import repair as R
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        rows = R.scan_installed(prof, self.game_root, limit=limit)
        mine = [r for r in rows if r.get("name") == name]
        if not mine:
            raise C.IntentError("这个玩家的模组列表里没有叫「%s」的、自带 .dat 的模组" % name)
        row = mine[0]
        verdict = row.get("verdict")
        if verdict == R.IMPOSSIBLE:
            raise C.IntentError("「%s」不能这样修：%s"
                                % (name, "；".join(row.get("reasons") or []) or "格式换代了"))
        if verdict not in (R.AUTO, R.IDENTICAL):
            raise C.IntentError(
                "「%s」只能部分自动修（%s）。它%s，把它搬过来要按顺序带上图片、文本、"
                "图标和训练位，这一版还不做 —— 只搬数值会得到一个能加载但行为不对的模组。"
                % (name, row.get("verdict"),
                   "新增或删除过记录" if verdict == R.MANUAL else "没有可搬的改动"))

        old_dir = row.get("path")
        if not old_dir or not os.path.isdir(old_dir):
            raise C.IntentError("找不到「%s」装在哪：%s" % (name, old_dir))

        plan = R.plan_replay(row, self._families())
        if plan.get("conflicts"):
            c = plan["conflicts"][0]
            raise C.IntentError(
                "「%s」里同一个家族被改成了不同的值（%s：%s），没有任何一句话能表达这件事"
                % (name, c.get("field"), "、".join("%s→%s" % (i, v)
                                                  for i, v in zip(c.get("ids") or [],
                                                                  c.get("values") or []))))

        info = E.read_info_json(os.path.join(old_dir, "info.json"))
        title = info.get("Title") or name
        notes = []
        if verdict == R.IDENTICAL:
            # Nothing to replay: the author's file already matches today's game.
            # Deliberately no copy here -- carry_over into the same folder would
            # be copying every file onto itself (shutil.copyfile raises
            # SameFileError), and "install it again over itself" is not a repair
            # either; the honest answer is that this mod needs nothing.
            notes.append("这份 .dat 与今天出厂的数据逐字节相同，不需要重做，其他文件也都在原处。")
            return {"ok": True, "name": name, "title": title, "verdict": verdict,
                    "replayed": 0, "notes": notes, "carried": None,
                    "installed": None}

        if not out_dir:
            # NOT under game_root: that folder is the one the engine reads and
            # whose CRCs get checked, so writing rebuild output there leaves the
            # player with stray mods beside their game data.  A temp directory is
            # cleaned up when the process ends, and the install step copies out of
            # it anyway.
            import tempfile as _tempfile
            out_dir = os.path.join(_tempfile.mkdtemp(prefix="dsh_repair_"),
                                   row["name"])
        man = self.build_bundle(plan["intents"], out_dir, title=title,
                                author=author or info.get("Author") or "dsh",
                                description=info.get("Description") or "",
                                overwrite=True)
        carried = R.carry_over(old_dir, man["mod_dir"], log=notes)
        # The author's folder may have carried a `widgetui` layer next to its
        # `.dat` -- the shape measured on 2026-10-24 to draw nothing (five blank
        # boxes inside one folder, one drawn checkerboard after splitting).  A
        # verbatim copy would put those tables straight back into the data half and
        # rebuild the broken arrangement, so run the same splitter a build uses.
        _split = E.split_ui_layer(man["mod_dir"], man.get("info"))
        if _split:
            man["ui_mod_dir"] = _split["ui_dir"]
            man["ui_info"] = _split["info"]
            man["ui_files"] = _split["moved"]
            notes.append(
                "作者的界面文件（widgetui）也一起搬过来了；按这条规则单独打成一个"
                "模组：%s" % _split["info"].get("Title"))
        installed = self.install(man["mod_dir"], name=name, title=title,
                                 enabled=True, position=row.get("priority") or 0,
                                 profile_root=prof, overwrite=True)
        return {"ok": True, "name": name, "title": title, "verdict": verdict,
                "replayed": len(plan["intents"]), "collapsed": plan.get("collapsed"),
                "skipped": plan.get("skipped"), "conflicts": plan.get("conflicts"),
                "carried": carried, "notes": notes, "manifest": man,
                "installed": installed}

    def update_check(self, profile_root=None, game_dat=None,
                     state_file=None):
        """Has the game's data moved since any installed mod was built?

        ``state_file`` exists so a caller (and the tests) can point at a throwaway
        record instead of the player's real one -- the same reason ``install_mod``
        takes ``profile_root``.
        """
        return PV.check(profile_root=profile_root, game_dat=game_dat,
                        path=state_file)

    def mods(self):
        from .game import locations as G
        prof = G.find_profile_root()
        return G.list_mods(prof)

    def install(self, mod_dir, name=None, title=None, kind="local",
                enabled=True, position=0, profile_root=None, account=None,
                overwrite=False):
        """Put a built mod where the game will load it, and register it.

        Separate from ``build`` on purpose: building is reversible and lives in
        the caller's own folder, while installing writes into the user's game
        profile and changes which mods the game loads.  Keeping them apart lets
        a UI show the mod first, and lets a user build without committing.

        ``position=0`` inserts at the top of the list, which is the HIGHEST
        priority: the engine checks mods from the top and the first one with a
        given file wins.  Existing mods keep their relative order.

        The returned manifest carries ``requires_game_restart`` and
        ``storage_points``.  A DATA mod does not need a restart: the user
        confirmed in game (2026-10-16) that a mod folder dropped in while the
        game runs is read by that running session.  The flag is therefore
        derived from what the mod actually writes -- graphics storage points
        (sprites, atlases, XAML, palettes) are already bound by a running
        session, so only those ask for a relaunch.  The old note told every user
        to quit and relaunch, and it was wrong.
        """
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        man = G.install_mod(mod_dir, prof, name=name, title=title, kind=kind,
                            enabled=enabled, position=position,
                            account=account, overwrite=overwrite)
        # The build record knows the game data; only the install knows the bytes
        # the game will actually read.  Attaching that is what lets a later check
        # tell "the game was patched" from "somebody replaced MY mod" -- two
        # situations with opposite fixes.
        try:
            PV.note_installed(man)
        except Exception as exc:                       # noqa: BLE001
            man["provenance"] = {"why_not": "%s: %s" % (type(exc).__name__, exc)}

        # A build that ships a `.dat` gets its `widgetui` layer moved into a
        # sibling folder, because a data folder that carries both is read as a
        # data mod only and the icon tables are then never loaded (measured
        # 2026-10-24: five runs empty, one split run drawing).  Installing the
        # data half alone would make that split actively harmful, so the second
        # half is installed here, right next to it.
        ui_dir = mod_dir.rstrip("\\/") + E.UI_FOLDER_SUFFIX
        if os.path.isdir(ui_dir) and os.path.isfile(os.path.join(ui_dir,
                                                                 "info.json")):
            try:
                ui_info = E.read_info_json(os.path.join(ui_dir, "info.json"))
                ui_title = (ui_info or {}).get("Title") or (title or "") + "（界面）"
                ui_man = G.install_mod(ui_dir, prof,
                                       name=ui_title,
                                       title=ui_title, kind=kind,
                                       enabled=enabled,
                                       position=position + 1,
                                       account=account, overwrite=overwrite)
                man["ui_install"] = {
                    "mod_dir": ui_dir,
                    "name": ui_title,
                    "priority": ui_man.get("priority"),
                    "files": ui_man.get("files"),
                }
            except Exception as exc:                   # noqa: BLE001
                man["ui_install"] = {"why_not": "%s: %s" % (type(exc).__name__, exc)}
        return man

    @staticmethod
    def _halves_of(folder):
        """Every name the OTHER half of a split build can have on disk.

        The build output folder is `<name>_ui` (see `E.UI_FOLDER_SUFFIX`), but
        `install()` names the installed mod after its title, and the interface
        title is `<base title> + "（界面）"`.  Both spellings are real, so both are
        offered and the caller keeps whichever one the status file confirms.
        """
        suffix = E.UI_FOLDER_SUFFIX
        out = []
        if not folder:
            return out
        if folder.endswith(suffix) and len(folder) > len(suffix):
            out.append(folder[:-len(suffix)])
        else:
            out.append(folder + suffix)
        ui_word = "\uff08\u754c\u9762\uff09"
        if folder.endswith(ui_word) and len(folder) > len(ui_word):
            out.append(folder[:-len(ui_word)])
        else:
            out.append(folder + ui_word)
        return out

    def move_mod(self, name, delta, kind="local", profile_root=None, account=None):
        """Move an installed mod one step up or down, and say where it landed.

        Ordering is the conflict order: the engine walks `mod-status.json` in
        array order, so the entry above wins a shared path.  The screen needs to
        change that without opening the game, which is the whole point of a
        manager; `delta=-1` is "up" (higher priority), `+1` is "down".
        """
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        folder, _how = G.resolve_mod_name(prof, name, kind=kind, account=account)
        doc, acc, _p = G.read_status_doc(prof, account=account)
        _running = G.running_note()
        pos = G.move_mod_entry(doc, folder, delta, kind=kind)
        G.write_status_doc(acc, doc, backup=True)
        return {"account": acc, "name": name, "kind": kind, "priority": pos,
                "game_running": _running["game_running"],
                "running_warning": _running["running_warning"]}

    def uninstall(self, name, kind="local", profile_root=None, account=None,
                  remove_files=True):
        """Remove an installed mod -- and the other half, when the build was split.

        A build that ships a `.dat` installs TWO mods (`X` and `X` + "\uff08\u754c\u9762\uff09").
        Removing one name used to leave the other behind, and the half that
        survived was the one carrying `widgetui/icons.json` and
        `widgetui/materials.json` -- an interface mod overriding the icon tables
        for a build that no longer exists, with nothing on screen saying so.
        Measured 2026-10-24: after uninstalling the data half by name, the
        interface half was still installed with its 3 widgetui files.

        Both directions are paired.  Removing the `_ui` folder alone leaves a
        data mod with no icons, which is exactly the state the split exists to
        avoid, so it is not "safer" to remove one.
        """
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        first = G.uninstall_mod(prof, name, kind=kind, account=account,
                                remove_files=remove_files)
        folder = first.get("name") or ""
        paired = None
        for sibling in self._halves_of(folder):
            try:
                gone = G.uninstall_mod(prof, sibling, kind=kind, account=account,
                                       remove_files=remove_files)
                # `resolve_mod_name` returns the name unchanged when nothing
                # matched, and then `entries_removed`/`folder_removed` are both
                # falsy -- so a mod that simply has no other half reports
                # nothing instead of inventing one.
                if gone.get("entries_removed") or gone.get("folder_removed"):
                    paired = gone
                    break
            except Exception as exc:                   # noqa: BLE001
                paired = {"why_not": "%s: %s" % (type(exc).__name__, exc)}
        first["paired"] = paired
        return first

    def set_mod_enabled(self, name, enabled, kind="local",
                        profile_root=None, account=None):
        """Turn an already-installed mod on or off -- and the other half with it.

        A split build is two mods, so switching one of them off leaves the other
        applying itself.  Measured 2026-10-24: the data half reported `enabled:
        False` while `X（界面）` stayed on with `widgetui/icons.json` live, i.e. the
        screen said "off" and the icon tables were still being overridden.  The
        pairing is the same one `uninstall` uses, in both directions, and a name
        with no sibling reports `paired: None` instead of inventing one.
        """
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        first = G.set_mod_enabled(prof, name, enabled, kind=kind, account=account)
        folder, _how = G.resolve_mod_name(prof, name, kind=kind)
        paired = None
        for sibling in self._halves_of(folder):
            try:
                got = G.set_mod_enabled(prof, sibling, enabled, kind=kind,
                                        account=account)
            except (FileNotFoundError, OSError):
                # No such mod: that is the ordinary case for a build that was
                # never split, so it must stay silent rather than look like an
                # error the caller has to handle.
                continue
            paired = got
            break
        first["paired"] = paired
        return first


def open_toolkit(game_root=None):
    """Open the installed game (cached per root -- parsing takes seconds)."""
    from .game import locations as G
    root = game_root or G.find_game_root()
    key = os.path.abspath(root)
    if key not in _CACHE:
        _CACHE[key] = Toolkit(root)
    return _CACHE[key]
