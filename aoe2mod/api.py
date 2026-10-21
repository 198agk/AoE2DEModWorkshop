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
import os

from .dat import parser as P
from .dat import locate as L
from .dat import families as F
from .dat import writer as W
from .game import civtechtrees as CT
from .game import civnames as CN
from .game import buildpanel as BP
from .game import icons as IC
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
        base["record_bytes"] = len(_img)
        base["description"] = (
            "照 %s 在 %s 做一个新单位「%s」（编号 %d，%d 字节的记录，名字用字符串 %d）"
            % (r.donor.display, civ_zh, r.name, new_id, len(_img),
               string_id))
        base["edit_count"] = 2
        base["warnings"] = [
            "新单位的图标是照着做的那个单位的（图标的号 0..999 已满，这个工具不会去改图标那层）",
            "它出现在照着做的那个单位自己的建造按钮里，因为建造位置是从原记录抄来的",
        ]
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
        # A deep copy: `add_unit` mutates the model in place and this Toolkit
        # answers every later call from the same cached object, so building from
        # the cache would add the unit to this session's model as a side effect of
        # a build that may yet fail.
        stats = copy.deepcopy(self._stats)
        stats, rec = NU.add_unit(stats, self._raw, self._parsed[3], self._parsed[2],
                                 civ_index, r.donor.id, new_id,
                                 name_string_id=string_id,
                                 hp=r.raw.get("hp"))
        data, rep = W.serialize_dat(stats, raw=self._raw)
        if rep.get("raw_consumed") != len(self._raw):
            raise C.IntentError(
                "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），所以这份不改了"
                % (rep.get("raw_consumed"), len(self._raw)))
        string_files = S.build_files(self.game_root, [(string_id, r.name)])
        info = E.make_info(title or ("新单位 %s" % r.name), author=author,
                           description=description)
        man = E.emit_data_mod(out_dir, data, info, thumbnail=thumbnail,
                              base_dir=self.game_root, overwrite=overwrite,
                              json_files=string_files or None)
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
        man["new_unit"] = {
            "id": new_id, "name": r.name, "string_id": string_id,
            "civ": civ_name, "civ_index": civ_index,
            "donor_id": r.donor.id, "donor_name": r.donor.display,
            "record_bytes": rec["bytes"], "slot": rec["slot"],
            "strings": sorted(string_files) if string_files else [],
        }
        man["resolved"] = r.describe()
        # Records plus flags, matching the schema's declared count: one appended
        # record and one slot flipped.  A byte count here would not compare
        # against any other intent's edit_count.
        man["edits"] = 2
        man["edit_count"] = 2
        man["civs_edited"] = 1
        man["changes_dat"] = True
        man["dat_is_carrier"] = False
        man["mod_contains_dat"] = bool(man.get("dat"))
        man["verification"] = {
            "ok": bool(man["reparse_ok"] and man["unit_added"]),
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
                "that a running game draws or lists the new unit.  No test in this "
                "project has loaded a record the toolkit created",
            ],
        }
        return man

    def _new_unit_bundle(self, new_list, base_raw):
        """Fold every "make a new unit" sentence onto ONE stream.

        Returns ``(bytes_or_None, notes, refusals, string_files)``.

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
        notes, refusals, string_files = [], [], {}
        stats = None
        civs_start = gv = None
        cur = base_raw
        touched = False
        next_string = None
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
                string_id = S.first_free_id(
                    self.game_root,
                    start=next_string or (S.LAST_SHIPPED_ID + 1))
                stats, rec = NU.add_unit(stats, cur, gv, civs_start, civ_index,
                                         r.donor.id, new_id,
                                         name_string_id=string_id,
                                         hp=r.raw.get("hp"))
            except (NU.NewUnitError, S.StringError) as exc:
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            except Exception as exc:                      # noqa: BLE001
                refusals.append({"description": r.describe(), "reason": str(exc)})
                continue
            next_string = string_id + 1
            for rel, data_b in S.build_files(self.game_root,
                                             [(string_id, r.name)]).items():
                # Two creations in one bundle write the SAME string file, so the
                # lines are accumulated rather than overwritten -- otherwise the
                # second sentence would take the first one's name away.
                string_files[rel] = (string_files.get(rel) or b"") + data_b
            touched = True
            notes.append({
                "description": r.describe(),
                "mode": "new_unit",
                "civ": civ_name, "civ_index": civ_index,
                "id": new_id, "name": r.name, "string_id": string_id,
                "donor_id": r.donor.id, "donor_name": r.donor.display,
                "record_bytes": rec["bytes"], "slot": rec["slot"],
            })
        if not touched:
            return None, notes, refusals, {}
        out, rep = W.serialize_dat(stats, raw=cur)
        if rep.get("raw_consumed") != len(cur):
            raise C.IntentError(
                "写完以后 .dat 的读取位置对不上原来的文件（%s / %s），所以这份不改了"
                % (rep.get("raw_consumed"), len(cur)))
        return out, notes, refusals, string_files

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
        if self._strategy(r.raw) == "repaint_sld":
            return self._plan_paint(r, base)
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
        fam, hits = C.unit_targets(self._civs, r.entity.id, allowed, self._stats,
                                   self.game_root)
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
        if len(fam) > 1:
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
        if strategy != "in_place_patch":
            raise C.IntentError(
                "intent %r declares compile strategy %r, which this build does "
                "not implement" % (intent.get("intent"), strategy))
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
        dat, js, sld, paint, new = [], [], [], [], []
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
            elif s == "repaint_sld":
                # A repaint also ships loose files, but it ENCODES a picture
                # rather than moving one that already exists, so it needs its own
                # bucket: the reskin bucket is answered by `reskin.plan`, which
                # knows nothing about a picture and would refuse the sentence for
                # having no donor.
                paint.append(r)
            else:
                raise C.IntentError(
                    "intent %r declares compile strategy %r, which this build "
                    "does not implement"
                    % (r.raw.get("intent"), s))
        return dat, js, sld, paint, new

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
        dat_list, js_list, sld_list, paint_list, new_list = \
            self._split_by_strategy(resolved_list)

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
                           + rename_edits + paint_files),
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
            "changes_dat": bool(dat_list) or bool(_halves) or bool(rename_edits),
            "dat_is_carrier": (bool(js_list) and not dat_list and not _halves
                               and not rename_edits),
            # NOT `... or sld_list`: the COPY model ships loose `.sld` files and no
            # `.dat` at all, so listing it here would promise the emitter a file
            # that is not in the request.  The RENAME model is the opposite -- it
            # writes records into the `.dat` and no picture -- so it does make the
            # mod contain a `.dat`, and leaving it out here would report a mod
            # without the one file it cannot work without.
            "mod_contains_dat": bool(dat_list or js_list or rename_edits),
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
        dat_list, js_list, sld_list, paint_list, new_list = \
            self._split_by_strategy(resolved_list)

        data, civs, _cs, gv, tail, how = self._parsed
        json_files = {}
        avail_notes = []
        if js_list:
            files, notes, originals, proposal = \
                self._apply_availability_bundle(js_list)
            json_files = files
            avail_notes = notes

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
        new_strings = {}
        if new_list:
            _base = dat_bytes if dat_bytes is not None else data
            new_bytes, new_notes, new_ref, new_strings = \
                self._new_unit_bundle(new_list, _base)
            sprite_refusals = sprite_refusals + new_ref
            if new_bytes is not None:
                dat_bytes = new_bytes
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
        man["edits"] = (len(edits) + man["dat_half_edit_count"]
                        + len(sprite_files) + _rename_changed + paint_files
                        + 2 * len(new_notes))
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
                        "that a running game draws or lists a unit the toolkit "
                        "created.  No test in this project has loaded one",
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
        return man

    def uninstall(self, name, kind="local", profile_root=None, account=None,
                  remove_files=True):
        """Remove an installed mod from the profile and the status file."""
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        return G.uninstall_mod(prof, name, kind=kind, account=account,
                               remove_files=remove_files)

    def set_mod_enabled(self, name, enabled, kind="local",
                        profile_root=None, account=None):
        """Turn an already-installed mod on or off without moving it."""
        from .game import locations as G
        prof = profile_root or G.find_profile_root()
        return G.set_mod_enabled(prof, name, enabled, kind=kind, account=account)


def open_toolkit(game_root=None):
    """Open the installed game (cached per root -- parsing takes seconds)."""
    from .game import locations as G
    root = game_root or G.find_game_root()
    key = os.path.abspath(root)
    if key not in _CACHE:
        _CACHE[key] = Toolkit(root)
    return _CACHE[key]
