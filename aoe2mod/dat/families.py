# -*- coding: utf-8 -*-
"""Variant FAMILIES: one visible object, many .dat records.

Three kinds of variant, one problem
-----------------------------------
All three make a mod stop applying after it looked like it worked.

**1. Age variants.** `Barracks` exists as FOUR .dat records: 12 (Dark), 498
(Feudal), 132 (Castle), 20 (Imperial), all type 80, all displaying string id
5135.  Advancing an age runs an effect command of type 3 ("replace unit a with
unit b") and swaps the whole record out.  `House` (6 records), `Town Center`,
`Mill`, `Lumber Camp`, `Blacksmith` are the same shape.

**2. Task-swap variants.** `Villager (Male)` (83) becomes `Builder` (118),
`Lumberjack` (123), `Farmer` (259) ... the moment the player assigns a job.  The
engine does not re-stat the villager; it REPOINTS the object at a different
unit record inside the same `Bird.TaskSwapGroup`.  A health mod that writes only
id 83 therefore shows 2500/2500 while idle and 25/25 the instant the villager is
sent to build -- verified in-game, and exactly the failure mode of an age
variant.  The group is a plain uint8 on every bird record; in VER 8.9 exactly
three groups are non-empty (1 = 14 male villager jobs, 2 = 13 female villager
jobs, 3 = 5 fishing-variant ships) and it is 0 for the other 88,174 records, so
nonzero is itself the signal "this record is swapped at runtime".

**3. Named assemblies.** `linkedUnits.json` groups records the game presents as
one named object (Lu Bu 2032/2061, Arariboia 2641/2642, the Villagers list).
It is a hint, not ground truth: its `Villagers` entry contains `206 VMDL`,
whose TaskSwapGroup is 0 (it is a dead body record, not a job), so the list must
be filtered by the group rather than trusted wholesale.

**4. Object replacements.** `resources/_common/dat/objreplacement.json` is the
engine's own table of "record A becomes record B at runtime", the fourth and last
place a swap is declared.  It is a separate mechanism from the effect commands:
`objreplacement` does not appear anywhere in the shipped AGE/genieutils sources,
and the eight rows carry conditions effect commands cannot express -- `chance 50`
(a sex swap), `technology` + `technology_state` (Mule Cart, Settlement, Port),
`required_attribute` + `excluded_computer_players` (the packed Town Center).

It is what joins the two villager baskets.  `linkedUnits.json` already lists
BOTH sexes under one `Villagers` entry, and the `chance 50` Villager /
Villager (Female) row is the engine saying why: the two TaskSwapGroup baskets
are two halves of one object.  Without this table an edit to "the villager"
reaches only the male half -- the same silent half-application the baskets
themselves had, one level down.

Because the row is the engine's own declaration, it is unioned unconditionally,
exactly like a task-swap group; no type or name test applies.  (The two villager
rows are the case that proves it: 83 and 293 do NOT share a display name, so no
name-based rule could ever have joined them -- only the declaration can.)

Measured effect of the fourth mechanism on VER 8.9: 30 families / 132 ids ->
26 families / 134 ids, merging Dock+Port, Mill+Settlement, the four Town Center
records with the packed one, Lumber Camp + Mining Camp + Mule Cart, and the two
villager baskets into one 27-member family -- every other family unchanged.

The age-variant rule, and why it is this rule
---------------------------------------------
An earlier attempt grouped records by display-name string id and unit type.  That
is WRONG: it merged the sixteen `Sea Gate` placements (SGTAA/SGTAB/.../SGTDX,
ids 1379..1394) and the sixteen `City Gate` placements (1579..1594) into single
families, because they genuinely share one display name and one type.  They are
compass placements of the same object, not ages of it, and a user who asks for
"a tougher Sea Gate" does not necessarily mean all sixteen.

So the age family is the connected component over the engine's OWN replacement
edges, further restricted to edges whose endpoints agree on
  * unit type, and
  * at least one NONZERO display-name string id.
That yields 27 age families / 100 ids, and adding the three task-swap baskets
gives 30 families / 132 ids on VER 8.9 -- an INTERMEDIATE count, before the
declared swaps above bring it to 26 families / 134 ids.  This rule correctly
  * keeps 12/498/132/20 together (all "Barracks", all type 80, and the engine
    really does swap between them),
  * keeps 70/191/192/463/464/465 together (House),
  * splits the Sea Gate and City Gate placements,
  * rejects `Archer -> Crossbowman` (51/... different display names: different
    units, not ages of one), and
  * rejects `Builder -> FlemisPikeman` (118 -> 1663), a genuine morph that is not
    an age upgrade.

The nonzero-name condition exists because several projectile records carry
LanguageDLLName == 0; without it, 0 == 0 merges unrelated projectiles.

Task-swap groups are unioned in separately and unconditionally within their
group: they are the engine's own declaration that these records are one object,
so no name or type test applies.  Worth knowing when reading the villager
basket -- five members share a display name with their opposite-sex twin (56 and
57 are both "Fisherman", 118 and 212 both "Builder"), so *no* name-based rule
could have told the two baskets apart.  Only the group value can.

`CopyID`/`BaseID` in the record tail are NOT a family signal: measured over civ 1,
copy_id == base_id == the unit's own id for all 2,693 records.
"""
import collections
import json
import os

# effect command type 3 == "replace unit a with unit b"
EFFECT_REPLACE_UNIT = 3

# The fourth mechanism.  Its `FileName`-style root is the game install, not a
# mod, and it sits beside the .dat it describes.
OBJREPLACEMENT_REL = os.path.join("resources", "_common", "dat",
                                  "objreplacement.json")


def _nonzero_names(u):
    """The display-name string ids a record carries, dropping the 0 sentinel."""
    return {d for d in (u.get("_dll_names") or ()) if d}


def declared_edges(game_root):
    """The ``(src, dst)`` swaps ``objreplacement.json`` declares, or ``()``.

    Only rows that carry a ``replacement_object`` are swaps between two records.
    The one attribute-only row (``448 Scout`` -> ``"Scout ID" 263``, a
    replacement *attribute*, not an object) has no ``replacement_object`` and is
    deliberately skipped: it names no record to union with.

    Returns ``(edges, path, why)``; ``why`` is ``""`` when the table was read and
    otherwise says what happened, so a caller can report the honesty boundary
    instead of silently behaving as if the table had been empty.
    """
    path = os.path.join(game_root, OBJREPLACEMENT_REL)
    try:
        with open(path, "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8"))
    except (IOError, OSError) as exc:
        return (), path, "not readable: %s" % exc
    except ValueError as exc:
        return (), path, "not valid JSON: %s" % exc
    edges = []
    for row in doc.get("objects") or ():
        src = row.get("object_id")
        dst = (row.get("object_override") or {}).get("replacement_object")
        if src is None or dst is None or src == dst:
            continue
        edges.append((src, dst))
    return tuple(edges), path, ""


def build_families(civs):
    """Map every unit id to its variant family, as a sorted id list.

    ``civs`` is the locator's civ list.  Records are keyed by unit id and the
    first occurrence wins for the record body -- the 62 playable civs carry
    byte-identical building records -- but display names are UNIONED across every
    civ.  That matters: 57 civs present id 4 as "Archer" while the six Chronicles
    civs present it under the alternate id 405052, and the family rule compares
    name SETS, so a name seen in only one civ must still count.

    The result is memoised on the civ list's identity AND the edge set: a caller
    that walks 136,861 records once per intent would otherwise re-walk them for
    every field of every record it edits, and a cached answer computed before
    ``warm()`` would be silently edge-less.
    """
    key = (id(civs), len(_EDGE_CACHE.get("edges", ())),
           len(_EDGE_CACHE.get("declared", ())))
    hit = _FAM_CACHE.get(key)
    if hit is not None and hit[0] is civs:
        return hit[1]
    fam = _build_families_uncached(civs)
    _FAM_CACHE[key] = (civs, fam)
    return fam


_FAM_CACHE = {}


def _build_families_uncached(civs):
    by_id = {}
    names = {}
    groups = {}
    for civ in civs or ():
        for u in civ.get("units") or ():
            uid = u.get("id")
            if uid is None:
                continue
            if uid not in by_id:
                by_id[uid] = u
            ns = names.setdefault(uid, set())
            ns.update(d for d in (u.get("_dll_names") or ()) if d)
            one = u.get("_dll_name")
            if one:
                ns.add(one)
            # TaskSwapGroup is a per-record uint8 and is identical in every civ
            # for a given id (verified over all 90,190 bird records: zero ids
            # disagree across civs), so recording it once is enough.  The
            # `setdefault(uid, 0)` matters: units with no bird block after all
            # get the key, so a later tsg==0 assignment cannot win by accident.
            groups.setdefault(uid, u.get("task_swap_group") or 0)
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for src, dst in _replacement_edges():
        a, b = by_id.get(src), by_id.get(dst)
        if a is None or b is None:
            continue
        # Same unit type: an age upgrade replaces a building with a building.
        if a.get("type") != b.get("type"):
            continue
        # A shared NONZERO display name: the game itself presents these as one
        # named object, which is what a user means when they name it.  Without
        # the nonzero requirement, LanguageDLLName == 0 records would all merge.
        na, nb = names.get(src, set()), names.get(dst, set())
        if not na or not nb or not (na & nb):
            continue
        union(src, dst)

    # Task-swap groups: union unconditionally, with no type or name test, because
    # the group value IS the engine's own statement that these records are
    # interchangeable at runtime.  Skipping this is what let "change the villager"
    # produce a mod that reverted the moment the villager was given a job.
    by_group = collections.defaultdict(list)
    for uid, g in groups.items():
        if g:
            by_group[g].append(uid)
    for members in by_group.values():
        for uid in members[1:]:
            union(members[0], uid)

    # Declared object replacements (objreplacement.json): unioned with NO type or
    # name test for the same reason as a task-swap group -- the row is the
    # engine's own statement that it swaps one record for the other.  The two
    # villager rows are the case that proves a name test cannot work here: 83 and
    # 293 are "Villager" and "Villager (Female)", different display names, and
    # they are the two halves of one object.  Rows naming a record that is absent
    # from the dat are skipped rather than trusted.
    for src, dst in _EDGE_CACHE.get("declared", ()):
        if src in by_id and dst in by_id:
            union(src, dst)

    grouped = collections.defaultdict(list)
    for uid in list(parent):
        grouped[find(uid)].append(uid)
    fam = {}
    for members in grouped.values():
        if len(members) < 2:
            continue
        members = sorted(members)
        for uid in members:
            fam[uid] = members
    return fam


def family_of(families, unit_id):
    """The family an id belongs to, or a 1-element list for a lone record."""
    return list(families.get(unit_id) or [unit_id])


def groups_of(civs, ids):
    """The distinct NONZERO TaskSwapGroup values carried by ``ids``, sorted.

    A family can span more than one group: once objreplacement.json's declared
    sex swap joins the two villager baskets, the family reports ``[1, 2]``.  A
    caller that reported the single group of the record the user named would be
    describing half of what the edit does -- which is the exact failure this
    module exists to prevent.  Returns ``[]`` for an age family (all groups 0).
    """
    want = set(ids)
    out = set()
    for civ in civs or ():
        for u in civ.get("units") or ():
            if u.get("id") in want:
                g = u.get("task_swap_group") or 0
                if g:
                    out.add(g)
    return sorted(out)


def _replacement_edges():
    """Every (src, dst) the engine can swap, read from the effects section.

    The edges live in effect commands whose ``effect_id`` is referenced by a
    tech; ``warm()`` collects them from the parsed stats the caller holds.
    """
    for edge in _EDGE_CACHE.get("edges", ()):
        yield edge


_EDGE_CACHE = {}


def warm(stats, game_root=None):
    """Collect the replacement edges out of a parsed ``stats`` dict.

    ``game_root`` is where ``objreplacement.json`` is looked for.  It cannot be
    derived from ``stats``: the census carries no path key at all, so a caller
    that omits it gets the effect edges only -- the historical behaviour.  Pass
    it whenever it is known; the two villager baskets only join when it is.
    """
    effects = stats.get("effects") or []
    techs = stats.get("techs") or []
    edges = set()
    for tech in techs:
        ei = tech.get("effect_id")
        if ei is None or ei < 0 or ei >= len(effects):
            continue
        for cmd in (effects[ei].get("commands") or ()):
            if cmd[0] == EFFECT_REPLACE_UNIT and cmd[1] > 0 and cmd[2] > 0:
                edges.add((cmd[1], cmd[2]))
    _EDGE_CACHE["edges"] = sorted(edges)

    declared, path, why = ((), None, "no game_root given")
    if game_root:
        declared, path, why = declared_edges(game_root)
        # Two rows point at ONE target (Lumber Camp and Mining Camp both become
        # Mule Cart).  Keep both rows: each is a separate claim, and dropping one
        # would leave that camp out of the family.
    _EDGE_CACHE["declared"] = tuple(declared)
    _EDGE_CACHE["declared_path"] = path
    _EDGE_CACHE["declared_why"] = why
    return _EDGE_CACHE["edges"]
