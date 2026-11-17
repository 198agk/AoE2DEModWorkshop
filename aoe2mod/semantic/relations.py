# -*- coding: utf-8 -*-
"""What else is this record ABOUT -- the reverse direction, in four tables.

A .dat points one way only.  A technology names the building it is researched at
(research_locations[].location_id) and the things its effect commands touch; a
unit names the hoard that shows its button (train_locations[].unit_id).  Nothing
points back.  So "what is related to 铁匠铺" -- reported 2026-11-16, verbatim:
「我想的是能把关联的直接搜出来，比如我搜铁匠铺，就能显示出这个铁匠铺有关的东西」
-- can only be answered by walking every record once and turning the arrows
around.

Measured on the shipped file (2026-11-16, this install): 1,510 technologies,
63 civilisation copies of the unit list; building every table costs 0.48 s and
1.6 s on the first call after a cache miss, after which each lookup is a dict
hit.  Too expensive per request, so the tables hang on the toolkit and are
rebuilt only when the file changes -- the same generation counter `App._gen`
that /api/unit-effects uses.

  research    building id -> [tech id]    the techs offered AT that building
  train       hoard id    -> [unit id]    the units whose button it shows
  targets     tech id     -> [unit id]    the units its commands touch by id
  classes     tech id     -> [label]      the unit CLASSES its commands touch
  modified    unit id     -> [tech id]    the techs that touch it (reverse)

TWO ID SPACES DO NOT MIX, and a third one is not an id space at all.  An effect
command carries its target in one slot whether that target is a unit, a unit
CLASS or a resource, and the three numbers overlap (class 18 exists, resource 18
exists, unit 18 is 铁匠铺).  Only rows whose `target_kind` is exactly "unit" go
into `targets`/`modified`; measured 2026-11-16 on the shipped file that is 5,257
rows against 1,163 class rows and 364 resource rows.  Without the split 雕版
印刷术 came out as a technology that changes 铁匠铺.

Class rows are not dropped, they are the answer to a different question.  锻造
(67) has eleven commands: six of them address 步兵 / 骑兵 / 长枪兵 ... and five
name single odd units.  Filing all eleven as "units this tech changes" would
print 骆驼投石机 and 趸船 under 锻造 and leave out the infantry, which is the
opposite of the truth, so a class row is kept as a NAME (its target_label) in
its own list and drawn with a 「整类」 mark.

Every list is deduplicated and keeps file order, so two calls answer identically.
"""


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _locations(tech):
    """The building ids a technology can be researched at."""
    out = []
    for slot in (tech.get("research_locations") or ()):
        if not isinstance(slot, dict):
            continue
        lid = _int(slot.get("location_id"))
        # 0 and -1 are the engine's "no location", not a building.
        if lid is not None and lid > 0 and lid not in out:
            out.append(lid)
    return out


def _add(table, key, value):
    got = table.setdefault(key, [])
    if value not in got:
        got.append(value)


def build(tk):
    """Every table for the file this toolkit holds.  Never returns None."""
    tk._ensure()
    from aoe2mod.intent import compiler as C
    research, train, targets, classes, modified = {}, {}, {}, {}, {}
    # A class row names no record, but it is still an arrow: "this technology
    # changes the whole tower class" reaches every tower.  Kept the other way
    # round as well (class id -> technologies) so a tower can ask who changes it.
    class_mod, clsname = {}, {}
    techs = tk._tech_records()
    for ti, t in enumerate(techs):
        for lid in _locations(t):
            _add(research, lid, ti)
    # `train_locations[].unit_id` is the HOARD that shows the button -- a building
    # for a unit, the villager record for a building.  See
    # aoe2mod/dat/newunit.py:train_slots.  It is the only pointer in the file from
    # a producing record to its product, so 116 建筑者 -> every building a
    # villager can raise lives here.
    for civ_row in (tk._civs or ()):
        for u in (civ_row.get("units") or ()):
            uid = _int(u.get("id"))
            if uid is None:
                continue
            for slot in (u.get("train_locations") or ()):
                if not isinstance(slot, dict):
                    continue
                bid = _int(slot.get("unit_id"))
                if bid is None or bid <= 0:
                    continue
                _add(train, bid, uid)
    effects = tk._effect_records()
    fanout = tk._effect_fanout()
    ix = tk.index()
    for ti, t in enumerate(techs):
        for r in C.effect_rows(effects, t, fanout=fanout, ix=ix,
                               unit_class=tk.unit_class):
            kind = r.get("target_kind")
            if kind == "class":
                # No record to link to: a class is a number the engine reads,
                # not an entity.  Its label is the only handle there is.
                label = (r.get("target_label") or "").strip()
                if label:
                    _add(classes, ti, label)
                cid = _int(r.get("target"))
                if cid is not None and cid > 0:
                    _add(class_mod, cid, ti)
                    if label:
                        clsname.setdefault(cid, label)
                continue
            if kind != "unit":
                continue                       # a resource id, a different space
            one = _int(r.get("target"))
            if one is None or one <= 0:
                continue
            _add(targets, ti, one)
            _add(modified, one, ti)
    # Which class each record IS.  Read once here, from the same snapshot the
    # rest of the tables come from, so asking "which class is 79" never re-walks
    # 2,693 records.  52 is the class of 79 瞭望箭塔, 235 城堡 and 236 炮塔 --
    # 996 强化堡垒 addresses class 52, and without this map a tower had no way
    # of finding out that it was one of the things the technology changed.
    ucls, class_units = {}, {}
    for uid, facts in (tk._unit_facts() or {}).items():
        cid = _int((facts or {}).get("class"))
        if cid is None:
            continue
        ucls[uid] = cid
        _add(class_units, cid, uid)
    return {"research": research, "train": train, "targets": targets,
            "classes": classes, "modified": modified, "class_mod": class_mod,
            "clsname": clsname, "ucls": ucls, "class_units": class_units,
            "utypes": dict(tk._utypes or {})}


def maps_of(app):
    """The cached tables for the file this App has open, rebuilt per generation."""
    tk = app.tk
    tk._ensure()
    gen = app._gen
    cache = getattr(tk, "_relations", None)
    if cache is None or getattr(tk, "_relations_gen", None) != gen:
        cache = build(tk)
        tk._relations = cache
        tk._relations_gen = gen
    return cache


# The words on screen.  Each group says the DIRECTION out loud, because 锻造 under
# 铁匠铺 means something different from 铁匠铺 under 锻造; a bare list of names
# would leave the player guessing which way round it is.  Two of them change with
# the record: a BUILDING is not trained anywhere, it is BUILT by someone.
LABELS = {
    "research_here": "在这里研究的科技",
    "trains": "在这里造的兵",
    "trained_at": "在哪儿造",
    "built_by": "谁造的",
    "researched_at": "在哪儿研究",
    "modified_by": "改它的科技",
    # Kept apart from the direct list on purpose: "996 changes class 52" is a
    # weaker claim than "996 names 79", and the player who opened a tower wants
    # to see which of the two he is looking at.
    "modified_by_class": "改它这一类的科技",
    "members": "这一类里的记录",
    # The other half of the same arrow.  996 强化堡垒 names 塔 and never names a
    # single tower, so "它改的兵 5" was technically true and completely useless:
    # the player asked 「为什么没有相关项没有塔」.  This group is the records
    # behind the class names, printed with ids so they can be opened.
    "class_members": "它改的整类里的记录",
    "targets": "它改的兵",
    "classes": "它改的类别",
}


def _items(ids, table, kind, skip=()):
    out = []
    for one in (ids or ()):
        if one in skip:
            continue
        e = table.get(one)
        if e is None or not e.is_visible:
            # An unnamed record is engine furniture (1,036 of the unit list);
            # listing it under 铁匠铺 would read as a broken name, not a fact.
            continue
        out.append({"kind": kind, "id": one, "name": e.display})
    return out


def is_building(uid, maps):
    """Is this record a building?

    There is no building table in this game: a building is a unit record whose
    type is 80 (aoe2mod/dat/parser.py:UNIT_TYPE_BUILDING), which is the same test
    the 建筑 tab uses.  Read from the snapshot taken when the tables were built,
    so asking does not re-walk 2,693 records.
    """
    from aoe2mod.dat import parser as _P
    want = getattr(_P, "UNIT_TYPE_BUILDING", 80)
    return (maps.get("utypes") or {}).get(uid) == want


def class_of(uid, maps):
    """(class id, class name) for one record, or (None, None).

    The class is a NUMBER the engine reads (52 is the tower class), so a record
    that is one of a class is also reachable from every technology that names
    the class: 996 强化堡垒 lists 52 among its eight commands and never names
    79 瞭望箭塔, which is why the tower used to look untouched.  Reported
    2026-11-16, verbatim: 「这个不是会作用于塔类吗，为什么没有相关项没有塔」.
    """
    uid = _int(uid)
    cid = (maps.get("ucls") or {}).get(uid)
    if cid is None:
        return None, None
    return cid, (maps.get("clsname") or {}).get(cid)


def groups(kind, uid, maps, ix, skip=()):
    """Every group of records related to one record, in both directions.

    Only what the FILE says.  A relationship this data does not carry -- "this
    technology needs 城堡" lives in required_techs, a different graph -- is not
    invented here.
    """
    uid = _int(uid)
    if uid is None:
        return []
    out = []
    if kind == "class":
        # A class is not a record, but it is not a blank either: 996 names 塔
        # (52) and the ten towers behind that number are exactly what the player
        # was looking for when he asked why no tower was listed.  Reported
        # 2026-11-16, verbatim: 「为什么没有相关项没有塔」.
        out.append(("members", _items(maps.get("class_units", {}).get(uid),
                                      ix.units, "unit", skip)))
        return [(k, v) for k, v in out if v]
    if kind == "tech":
        where = sorted(b for b, ts in maps["research"].items() if uid in ts)
        if where:
            out.append(("researched_at", _items(where, ix.units, "unit", skip)))
        named = [{"kind": "class", "id": None, "name": one}
                 for one in (maps["classes"].get(uid) or ())]
        if named:
            out.append(("classes", named))
        direct = maps["targets"].get(uid) or ()
        out.append(("targets", _items(direct, ix.units, "unit", skip)))
        # The records behind those class names.  A class with no visible member
        # (45 / 46 / 50) contributes nothing, and a record already listed as a
        # directly named target is not repeated here.
        # Each member carries the class it came from.  996 has three classes and
        # 118 records behind them; a flat row of 118 chips answers "is a tower in
        # here" with a scavenger hunt, so the screen can put the class name back
        # in front of the records that belong to it.
        behind, seen = [], set()
        for cid, techs in (maps.get("class_mod") or {}).items():
            if uid not in techs:
                continue
            cname = ((maps.get("clsname") or {}).get(cid)
                     or "第 %d 类" % cid)
            for one in _items((maps.get("class_units") or {}).get(cid), ix.units,
                              "unit", skip):
                if one["id"] in direct or one["id"] in seen:
                    continue
                one["cls"] = cname
                seen.add(one["id"])
                behind.append(one)
        out.append(("class_members", behind))
        return [(k, v) for k, v in out if v]
    # A unit record covers buildings too: this game has no separate building
    # table, only unit records whose type is 80.
    out.append(("research_here", _items(maps["research"].get(uid), ix.techs,
                                        "tech", skip)))
    out.append(("trains", _items(maps["train"].get(uid), ix.units, "unit", skip)))
    hoards = sorted(b for b, us in maps["train"].items() if uid in us)
    if hoards:
        key = "built_by" if is_building(uid, maps) else "trained_at"
        out.append((key, _items(hoards, ix.units, "unit", skip)))
    direct = maps["modified"].get(uid) or ()
    out.append(("modified_by", _items(direct, ix.techs, "tech", skip)))
    # And the technologies that never name this record, only its class.  A class
    # with no members, or no name, contributes nothing: 45 / 46 / 50 are classes
    # the file lists commands for while no visible record carries them, and a
    # group built from those would be a heading over an empty list.
    cid, _cname = class_of(uid, maps)
    if cid is not None:
        via = [t for t in (maps.get("class_mod") or {}).get(cid, ())
               if t not in set(direct)]
        out.append(("modified_by_class", _items(via, ix.techs, "tech", skip)))
    return [(k, v) for k, v in out if v]


def for_record(kind, uid, maps, ix, limit=24, skip=()):
    """groups() with the labels attached and long lists cut to `limit`.

    `limit=None` (or 0) means NO CUT, and the screen asks for that when the
    player clicks 看全部 on a group whose tail it hid: 城堡 has 211 technologies
    in 在这里研究的科技 and 171 units in 在这里造的兵, so the default answer shows
    24 and says how many are left.  Without this branch the hidden ones had no
    way of ever being read -- the count was honest and the records behind it
    were unreachable, which is the same dead end as the old 0 / 0.
    The items are already in memory, so an uncut answer costs the same dict
    lookups plus the join; nothing is re-walked.
    """
    out = []
    cut = limit if isinstance(limit, int) and limit > 0 else None
    for key, items in groups(kind, uid, maps, ix, skip):
        label = LABELS.get(key, key)
        if key == "modified_by_class":
            # Say WHICH class out loud, otherwise the two 改 sections read as a
            # duplicate: 79 瞭望箭塔 has ten techs that name it and twenty-three
            # that name 塔, and the only difference is this word.
            cname = class_of(uid, maps)[1]
            if cname:
                label = "改它这一类（" + cname + "）的科技"
        out.append({"key": key, "label": label,
                    "total": len(items), "items": items[:cut]})
    return out


def siblings(kind, uid, ix, limit=12):
    """Other records that carry the SAME name -- the answer to a real trap.

    Reported shape (2026-11-16): the player searches 铁匠铺, the list shows five
    rows, the pane opens the first one -- and it looks nearly empty, because the
    fifteen technologies hang off 103 while 18, 19 and 105 carry only the cost
    and hit points.  All five are named 铁匠铺 in the file (134 unit names and 7
    tech names repeat; 船坞 appears 15 times), so the pane has to say "there are
    four more of these" instead of looking broken.

    Compared by DISPLAY name, which is what the player typed.  A record with no
    name is never a sibling of anything.
    """
    table = ix.techs if kind == "tech" else ix.units
    me = table.get(uid)
    if me is None or not me.is_visible:
        return []
    name = me.display
    out = []
    for one in sorted(table):
        if one == uid:
            continue
        e = table.get(one)
        if e is None or not e.is_visible or e.display != name:
            continue
        out.append({"kind": kind, "id": one, "name": name})
        if len(out) >= limit:
            break
    return out
