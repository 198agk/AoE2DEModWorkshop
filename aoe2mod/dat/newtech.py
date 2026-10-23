"""Create a technology record that the shipped ``.dat`` does not have.

The record format
-----------------
A tech is ``62 + len(name) + 9 * n_locations`` bytes at ``GV_C31`` and above
(measured: 1,510 shipped records span 71..134 B, mean 89.7, and the formula
reproduces all 1,510).  It carries no id: a technology is addressed by its
POSITION in the array (``aoe2mod/dat/locate.py:433`` says so and every reader
relies on it), so appending a record gives it the id ``len(techs)``.

Why the id matters more here than for units
-------------------------------------------
Units and technologies share one integer space in ``CivTechTrees/*.json``'s
``Node ID``.  The shipped data uses 0..1,509 for techs and 0..2,749 for units,
so they overlap (43 ids are both); the first integer that is neither is 2,113
(``_probe/report_tech_create_recon.md`` measured this).  Appending one record
therefore produces tech 1,510, which ``CivTechTrees`` already knows as the unit
``CityGate NE (Rubble)``.

That is not a reason to refuse -- the record itself is addressed by position and
nothing in the ``.dat`` cares -- but it does mean the new tech CANNOT be named
in a ``CivTechTrees`` file, and it is why the product says so instead of
pretending the new technology is a full citizen of the tree.  What it can still
have is a research location inside the ``.dat``, which is the half
``tech.toggle_group`` already writes and the half the game reads to decide
whether a button exists.

The four display strings
------------------------
``LanguageDLLName`` / ``Description`` / ``Help`` / ``TechTree`` were hardcoded
to 0 in the writer's ``_new`` branch until 2026-10-22.  String id 0 is defined in
0 of the 17 locale tables (max shipped id 30,030,001), so a synthesised tech
could exist and never say what it was.  They are fields of the record now, and
this module always fills ``lang_name`` from a caller-supplied string id.
"""

import copy

#: Smallest record the writer can emit: header with a 0-length internal name
#: and no research location.  ``62 + len(name) + 9 * n_locations``.
TECH_RECORD_MIN = 62

#: The id an appended record gets.  It is ``len(techs)`` -- not a constant --
#: and it is exported only so tests and the preview can say it out loud.
SHIPPED_TECH_COUNT = 1510

#: First integer that is neither a shipped tech id nor a shipped unit id.
FIRST_UNSHARED_ID = 2113


class NewTechError(Exception):
    """A technology cannot be created the way the sentence asked."""


def next_tech_id(stats):
    """The id the next appended tech record will have."""
    return len(stats.get("techs") or ())


def pick_donor(techs, tech_id):
    """The shipped record to copy, as a plain dict (``KeyError`` if absent)."""
    if isinstance(tech_id, bool) or not isinstance(tech_id, int):
        raise NewTechError("要照哪一项科技做？得说出一项已有的科技。")
    if not (0 <= tech_id < len(techs)):
        raise NewTechError("这个版本里没有第 %d 号科技。" % tech_id)
    return techs[tech_id]


def clone_tech(donor, internal_name, lang_name,
               lang_description=0, lang_help=0, lang_tech_tree=0,
               research_locations=None, cost=None, research_time=None,
               icon_id=None):
    """A ``_new`` record modelled on ``donor``.

    ``internal_name`` is the record's own ASCII name -- it is what a crash dump
    and a data-mod editor show, not what the player reads (that is
    ``lang_name``).  It is written with ``debug_string``, so it may be empty but
    may not be arbitrary binary.

    ``research_locations`` defaults to the donor's, because a technology that
    appears nowhere is invisible and the donor is the only evidence the caller
    gave about where it should live.  Passing a list overrides it.

    ``icon_id`` defaults to the donor's icon (the copy carries it).  It is an
    ``i16`` on the record -- measured out of ``parser.py``'s ``read_tech`` -- so
    the ceiling is 32767 even though the shipped ``icons.json`` Techs table stops
    at 312; a mod may extend that table (the installed Three Kingdoms UI mod
    ships keys up to 548).
    """
    if not isinstance(internal_name, str):
        raise NewTechError("新科技得有一个内部名字。")
    rec = copy.deepcopy(donor)
    rec["_new"] = True
    rec["name"] = internal_name
    rec["lang_name"] = int(lang_name or 0)
    rec["lang_description"] = int(lang_description or 0)
    rec["lang_help"] = int(lang_help or 0)
    rec["lang_tech_tree"] = int(lang_tech_tree or 0)
    if not rec["lang_name"]:
        raise NewTechError("新科技必须有名字，否则游戏里只会显示空白。")
    if research_locations is None:
        research_locations = copy.deepcopy(donor.get("research_locations") or [])
    locs = []
    for loc in research_locations or ():
        if isinstance(loc, dict):
            item = {"location_id": int(loc.get("location_id")),
                    "research_time": int(loc.get("research_time") or 0),
                    "button_id": int(loc.get("button_id") or 0),
                    "hotkey_id": int(loc.get("hotkey_id") or 0)}
        else:
            item = {"location_id": int(loc[0]), "research_time": int(loc[1]),
                    "button_id": int(loc[2]), "hotkey_id": int(loc[3])}
        if item["research_time"] < 0 or item["research_time"] > 32767:
            raise NewTechError("研究时间得在 0 到 32767 之间，收到的是 %d。"
                               % item["research_time"])
        if not (0 <= item["button_id"] < 25 or item["button_id"] == 255):
            raise NewTechError("命令卡只有 0 到 24 格，%d 填不进去。"
                               % item["button_id"])
        locs.append(item)
    rec["research_locations"] = locs
    if research_time is not None:
        for loc in rec["research_locations"]:
            loc["research_time"] = int(research_time)
    if cost is not None:
        # The record's cost slots are replayed verbatim (`w.op()`), not modelled,
        # so a value here cannot be honoured by the writer.  Refusing beats
        # accepting it and shipping a tech that costs nothing.
        raise NewTechError("这个版本还不能给新科技定成本"
                           "（成本槽是逐字节重放的，写不进去）。")
    if icon_id is not None:
        icon_id = int(icon_id)
        if icon_id < 0 or icon_id > 32767:
            raise NewTechError("科技图标号只能是 0..32767（记录里那个字段是 16 位），"
                               "收到的是 %d。" % icon_id)
        rec["icon_id"] = icon_id
    return rec


def add_tech(stats, donor_id, internal_name, lang_name, **kw):
    """Append one ``_new`` tech record.  Returns ``{id, record, donated_by}``.

    Works on a COPY of ``stats["techs"]`` -- the caller owns the model and a
    preview must not be able to change it.

    ``effect`` (optional) is a command string like ``"4,0,3,-1,1"``: the new tech
    gets its OWN effect record with that one command, and its ``effect_id`` is
    rewritten to point at it.  The effect is appended to ``stats["effects"]`` and
    its id is ``len(effects)`` for the same reason a tech's is (records are
    addressed by position).  Without it the new tech inherits the donor's
    ``effect_id`` -- which means "do whatever the donor does", and that is the
    honest default for "make one like this".
    """
    techs = list(stats.get("techs") or ())
    donor = pick_donor(techs, donor_id)
    new_id = len(techs)
    raw_effect = kw.pop("effect", None)
    rec = clone_tech(donor, internal_name, lang_name, **kw)
    effect_id = rec.get("effect_id")
    if raw_effect is not None:
        cmd = parse_effect(raw_effect)
        effects = list(stats.get("effects") or ())
        effect_id = len(effects)
        effects.append({"name": "NewEffect%d" % new_id,
                        "commands": [cmd],
                        "_new": True})
        stats["effects"] = effects
        rec["effect_id"] = effect_id
    techs.append(rec)
    stats["techs"] = techs
    return {"id": new_id, "record": rec, "donated_by": donor_id,
            "locations": len(rec["research_locations"]),
            "effect_id": effect_id}


def parse_effect(text):
    """``"4,0,3,-1,1"`` -> ``(4, 0, 3, -1, 1.0)``, the writer's 5-tuple.

    Refused rather than guessed: a command is a type plus three small integers
    plus one float, and a typo in any of them is a technology that does something
    the player did not ask for.
    """
    parts = [p.strip() for p in str(text or "").split(",")]
    if len(parts) != 5:
        raise NewTechError(
            "效果要写成 5 个用逗号隔开的数字（类型、a、b、c、数值），收到的是「%s」。"
            % (text,))
    try:
        ctype = int(parts[0])
        a = int(parts[1]); b = int(parts[2]); c = int(parts[3])
        d = float(parts[4])
    except ValueError:
        raise NewTechError(
            "效果里的每一项都得是数字，收到的是「%s」。" % (text,))
    if not (0 <= ctype <= 255):
        raise NewTechError("效果类型是 1 个字节，%d 填不进去。" % ctype)
    for name, val in (("a", a), ("b", b), ("c", c)):
        if not (-32768 <= val <= 32767):
            raise NewTechError("效果里的 %s 是 2 字节整数，%d 填不进去。" % (name, val))
    return (ctype, a, b, c, d)



def internal_name_for(text, new_id):
    """An ASCII internal name derived from the player's words.

    The record's own name is not what a player reads, and it must survive
    ``debug_string``: ASCII letters, digits and underscores only.  Chinese is
    dropped rather than transliterated -- ``NewTech1510`` is honest, and
    inventing a pinyin spelling would be a name the game never uses.
    """
    keep = "".join(ch for ch in str(text or "") if ch.isascii()
                   and (ch.isalnum() or ch == "_"))
    return ("NewTech%d" % new_id if not keep else "NewTech%d_%s"
            % (new_id, keep[:24]))
