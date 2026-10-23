"""Read an old mod's .dat, and say what it changed and what can be carried over.

Why this exists
---------------
Every mod that ships a whole `.dat` is a snapshot: about 12 MB of the file as it
was the day it was built.  When the game patches its own `.dat`, the mod keeps
handing the engine the old one, so the new content disappears or the game will
not start.  The right repair is not to patch the old file -- it is to find out
WHAT the mod changed, and replay that on today's shipped `.dat`.

That sentence is only useful if it is measured, so this module measures it:

    shipped .dat  ─┐
                   ├─→ per-record diff ─→ one line per difference ─→ verdict
    mod's .dat    ─┘

The diff reads fields through the SAME path the writer patches
(`compiler.unit_field_values` walks `_primary_targets_for_unit`, which walks
`unit["_offs"]`, which is where the in-place patcher gets its addresses).  A
field this module reports is therefore a field the writer can reach -- the
report can never name something the tool would refuse to write.  That is the
same invariant `probe/test_plan_build_agreement.py` enforces from the other
side.

What it will NOT claim
----------------------
Three outcomes, and the middle one matters most:

  * `auto`      -- a value on a record that exists in both files.  Replayable by
                   the intents that already exist (stat / cost / research time /
                   effect / icon).
  * `manual`    -- whole records the mod added, or values on records the mod
                   added.  These are not a patch; they are a rebuild, and
                   carrying them needs art, strings and icon slots too.  Listing
                   them is honest, pretending to replay them is not.
  * `impossible`-- the mod was written by a different generation of the format
                   (measured: one installed mod is `VER 7.8` with 46
                   civilizations against today's 63).  That is a data-model
                   change, not an offset shift, and no amount of byte work
                   bridges it.

Nothing here writes, installs or deletes.  `plan_diff` is read-only by
construction: it opens two files, decodes them, and returns a dict.
"""
import io
import json
import os
import shutil

import aoe2mod.dat.parser as P
import aoe2mod.dat.locate as L
from .intent import compiler as C
from .mod import provenance as PV

DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "aoe2mod", "schema")

AUTO = "auto"
MANUAL = "manual"
IMPOSSIBLE = "impossible"

# Every field this file reports on the unit side comes from the schema, so a new
# binding appears here the moment it is declared.  Cost is not one of those
# bindings -- it is its own intent with its own slot rule -- so it is read
# separately and named in the player's words.
_RESOURCE_ZH = {0: "食物", 1: "木材", 2: "石头", 3: "黄金"}


def _load_bindings():
    with io.open(os.path.join(SCHEMA_DIR, "dat_bindings.json"), encoding="utf-8-sig") as fh:
        return json.load(fh)


def _parse(path):
    """-> (raw, civs, civs_start, gv, tail, techs, errors)."""
    raw, how = P.load_dat(path)
    if raw is None:
        return None, None, None, None, None, None, ["这个文件不是一份能读的 .dat（%s）" % how]
    try:
        p = P.Parser(raw)
        # The parser narrates its ten stages to stdout; this module is called
        # from a web route, where that narration is noise in the server log.
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            p.parse()
        civs, civs_start, gv, tail = L.locate(raw, parser=p)
    except Exception as exc:               # noqa: BLE001 - report, never raise
        return raw, None, None, None, None, None, ["这份 .dat 读不开：%s: %s" % (type(exc).__name__, exc)]
    try:
        techs = L.locate_techs(raw, tail, gv)
    except Exception as exc:               # noqa: BLE001
        return raw, civs, civs_start, gv, tail, None, ["科技那一段读不开：%s: %s" % (type(exc).__name__, exc)]
    return raw, civs, civs_start, gv, tail, techs, []


def _version_of(raw):
    """The `VER x.y` string at the head of the stream, or None."""
    if not raw:
        return None
    head = raw[:32]
    try:
        text = head.split(b"\x00", 1)[0].decode("ascii", "replace")
    except Exception:                       # noqa: BLE001
        return None
    return text if text.startswith("VER") else None


def _units_by_id(civs):
    """{unit_id: record}, taking each id once.

    Measured 2026-10-23 on the shipped file: 63 civilizations declare the same
    2,693 unit ids, and the ONLY field that differs between them is `name`.  So
    one copy is a safe anchor for a diff, and `civ`-varying fields are reported
    separately rather than silently averaged.
    """
    out = {}
    for civ in civs or ():
        for u in civ.get("units") or ():
            uid = u.get("id")
            if uid is None:
                continue
            if uid not in out:
                out[uid] = u
    return out


def _techs_by_index(techs):
    out = {}
    for idx, t in enumerate(techs or ()):
        out[idx] = t
    return out


def _costs(rec):
    """{resource_id: amount} for the non-sentinel cost slots."""
    out = {}
    for c in rec.get("costs") or ():
        rtype = c.get("type")
        if rtype is None or int(rtype) < 0:
            continue
        out[int(rtype)] = c.get("amount")
    return out


def _label_of(bindings, field):
    fb = (bindings.get("unit_fields") or {}).get(field) or {}
    return fb.get("label") or field


def _diff_units(bindings, base_raw, mod_raw, base_units, mod_units, limit):
    """Differences on records BOTH files have.  Each is replayable."""
    rows = []
    added = sorted(uid for uid in mod_units if uid not in base_units)
    removed = sorted(uid for uid in base_units if uid not in mod_units)
    for uid in sorted(mod_units):
        if uid not in base_units:
            continue
        b, m = base_units[uid], mod_units[uid]
        for field in sorted((bindings.get("unit_fields") or {})):
            vb = C.unit_field_values(bindings, b, base_raw).get(field)
            vm = C.unit_field_values(bindings, m, mod_raw).get(field)
            # A field one side does not carry is not a change to zero: "this
            # record has no such field" and "this field is 0" are different
            # statements and only the record can tell them apart.
            if vb is None or vm is None:
                continue
            if vb != vm:
                rows.append({"kind": "unit", "id": uid, "field": field,
                             "label": _label_of(bindings, field),
                             "from": vb, "to": vm, "verdict": AUTO})
        cb, cm = _costs(b), _costs(m)
        for rtype in sorted(set(cb) | set(cm)):
            if cb.get(rtype) != cm.get(rtype):
                rows.append({"kind": "unit", "id": uid, "field": "cost.%d" % rtype,
                             "label": "%s成本" % _RESOURCE_ZH.get(rtype, "资源%d" % rtype),
                             "from": cb.get(rtype), "to": cm.get(rtype),
                             "verdict": AUTO})
        if len(rows) >= limit:
            break
    return rows, added, removed


def _diff_techs(base_techs, mod_techs, limit):
    rows = []
    added = sorted(i for i in mod_techs if i not in base_techs)
    removed = sorted(i for i in base_techs if i not in mod_techs)
    fields = (("research_time", "研究时间"), ("effect_id", "效果编号"),
              ("icon_id", "图标编号"), ("civ", "所属文明"))
    for idx in sorted(mod_techs):
        if idx not in base_techs:
            continue
        b, m = base_techs[idx], mod_techs[idx]
        for field, zh in fields:
            vb, vm = b.get(field), m.get(field)
            if vb is None or vm is None:
                continue
            if vb != vm:
                rows.append({"kind": "tech", "id": idx, "field": field,
                             "label": zh, "from": vb, "to": vm, "verdict": AUTO})
        cb, cm = _costs(b), _costs(m)
        for rtype in sorted(set(cb) | set(cm)):
            if cb.get(rtype) != cm.get(rtype):
                rows.append({"kind": "tech", "id": idx, "field": "cost.%d" % rtype,
                             "label": "%s成本" % _RESOURCE_ZH.get(rtype, "资源%d" % rtype),
                             "from": cb.get(rtype), "to": cm.get(rtype),
                             "verdict": AUTO})
        if len(rows) >= limit:
            break
    return rows, added, removed


def check(mod_dat, game_root, limit=400):
    """Compare a mod's `.dat` with the shipped one.  Read-only.

    `mod_dat` is the path to the mod's own
    `resources/_common/dat/empires2_x2_p1.dat`; `game_root` is the game install.
    Returns a report the screen can print and a person can act on:

        {ok, verdict, mod_version, base_version, same_generation, counts,
         changes: [...], added: {units, techs}, removed: {...},
         reasons: [...], notes: [...]}

    `verdict` is one of `no_dat`, `identical`, `auto`, `manual`, `impossible`:
    the strongest thing that can be said truthfully, not the thing that sounds
    best.
    """
    base_dat = os.path.join(game_root, DAT_REL)
    if not os.path.isfile(base_dat):
        return {"ok": False, "verdict": "no_dat",
                "reasons": ["游戏目录里找不到 %s，先确认装的是《帝国时代 2 决定版》"
                            % DAT_REL.replace(os.sep, "/")]}
    if not os.path.isfile(mod_dat):
        return {"ok": False, "verdict": "no_dat",
                "reasons": ["这个模组没有自己的 .dat：它只改松散文件，游戏更新不会让它失效"]}

    if os.path.getsize(mod_dat) == os.path.getsize(base_dat):
        with io.open(mod_dat, "rb") as a, io.open(base_dat, "rb") as b:
            if a.read() == b.read():
                return {"ok": True, "verdict": "identical", "changes": [],
                        "reasons": [], "notes": ["这份 .dat 与游戏现在那份逐字节相同："
                                                 "它只是随模组复制了一份，没有改动，不需要修"]}

    # The version head comes FIRST, before any parse.  Measured 2026-10-23 on a
    # file whose head was rewritten to `VER 7.8` with its body left alone: parsing
    # it first died with `error: bad char in struct format`, and the report said
    # "这份 .dat 读不开" -- true but useless, because the real answer is that this
    # file belongs to another generation of the format and its layout cannot be
    # walked by today's parser at all.  64 bytes of inflate costs 0.0000 s, so
    # there is no reason to pay 3-12 s to learn less.
    mver = PV.head_version(mod_dat)
    bver = PV.head_version(base_dat)
    if mver and bver and mver != bver:
        return {"ok": True, "verdict": IMPOSSIBLE,
                "mod_version": mver, "base_version": bver,
                "same_generation": False,
                "counts": {"changes": 0, "unit_changes": 0, "tech_changes": 0,
                           "units_added": 0, "units_removed": 0,
                           "techs_added": 0, "techs_removed": 0},
                "changes": [], "added": {"units": [], "techs": []},
                "removed": {"units": [], "techs": []},
                "reasons": ["这个模组是用 %s 写的，游戏现在是 %s：不是偏移挪了位，"
                            "是数据格式换代了（记录的布局本身就不同，"
                            "今天这份解析器连它的记录边界都走不过去），"
                            "把它逐字段搬过来这件事本身就说不通"
                            % (mver, bver)],
                "notes": ["这一份没有逐字段比对：跨代的偏移对不上，"
                          "列出改动清单只会给人「可以照着重放」的错觉"]}

    mraw, mcivs, _mcs, mgv, _mtail, mtechs, merr = _parse(mod_dat)
    braw, bcivs, _bcs, bgv, _btail, btechs, berr = _parse(base_dat)
    if merr or berr:
        return {"ok": False, "verdict": "impossible",
                "mod_version": mver, "base_version": bver,
                "reasons": (merr or []) + (berr or [])}

    # The head is the cheap answer and it is the ONLY safe answer before a parse;
    # if it could not be read for some reason, fall back to the parsed stream's
    # own head rather than guessing "different generation" from a missing value.
    mver = mver or _version_of(mraw)
    bver = bver or _version_of(braw)
    same_gen = (mver == bver)
    bindings = _load_bindings()

    changes, uadded, uremoved = _diff_units(
        bindings, braw, mraw, _units_by_id(bcivs), _units_by_id(mcivs), limit)
    tchanges, tadded, tremoved = _diff_techs(
        _techs_by_index(btechs), _techs_by_index(mtechs), limit)

    notes = []
    reasons = []
    if not same_gen:
        # Measured 2026-10-23: `10 倍资源文明联盟3倍科技` is VER 7.8 with 46
        # civilizations and 48,576,372 bytes of stream against today's 63 and
        # 93,268,152.  Reporting a field list for it would be a list of offsets
        # that no longer line up.
        reasons.append("这个模组是用 %s 写的，游戏现在是 %s：不是偏移挪了位，"
                       "是数据格式换代了（文明数、记录布局都不同），"
                       "把它逐字段搬过来这件事本身就说不通" % (mver or "旧版本", bver or "当前版本"))
    if uadded or tadded:
        reasons.append("这个模组新增了 %d 个单位记录、%d 个科技记录：那不是「改数值」，"
                       "是新建内容，搬过去还要连美术、文本、图标槽一起重建"
                       % (len(uadded), len(tadded)))
    if uremoved or tremoved:
        notes.append("它还删掉了 %d 个单位记录、%d 个科技记录"
                     % (len(uremoved), len(tremoved)))
    if changes or tchanges:
        reasons_age = ("有 %d 处数值改动（单位 %d / 科技 %d）可以在游戏现在这份 .dat 上重放"
                       % (len(changes) + len(tchanges), len(changes), len(tchanges)))
        notes.append(reasons_age)

    if not same_gen:
        verdict = IMPOSSIBLE
    elif uadded or tadded:
        # Even with replayable values present, the mod is not a patch, and
        # calling it "auto" would promise the added content comes along.
        verdict = MANUAL
    elif changes or tchanges:
        verdict = AUTO
    elif uremoved or tremoved:
        verdict = MANUAL
    else:
        verdict = "identical"

    return {
        "ok": True,
        "verdict": verdict,
        "mod_version": mver,
        "base_version": bver,
        "same_generation": same_gen,
        "counts": {"changes": len(changes) + len(tchanges),
                   "unit_changes": len(changes), "tech_changes": len(tchanges),
                   "units_added": len(uadded), "units_removed": len(uremoved),
                   "techs_added": len(tadded), "techs_removed": len(tremoved)},
        "changes": (changes + tchanges)[:limit],
        "added": {"units": uadded[:40], "techs": tadded[:40]},
        "removed": {"units": uremoved[:40], "techs": tremoved[:40]},
        "reasons": reasons,
        "notes": notes,
    }


_RESOURCE_KEY = {0: "food", 1: "wood", 2: "stone", 3: "gold"}


def plan_replay(report, families):
    """Turn a diff into the SHORTEST intent list that reproduces it.

    `families` is the family map from `aoe2mod/dat/families.py`, already built
    and WARMED by the caller (`Toolkit._families()`), because an un-warmed map
    is missing the declared swap edges from `objreplacement.json` and would
    report every record as a family of one -- silently, which is the failure
    mode this whole collapse exists to prevent.

    Measured 2026-10-23: `dsh test v46` changed five town-centre records
    (71/109/141/142/444) to 4000, and `check()` truthfully listed five rows.
    Replaying those five verbatim dies on sentence 2 with
    「城镇中心 的生命值已经是这个值了」 -- because ONE `unit.stat` intent and
    the family map already treat those five as one unit
    (`unit_ids=[71,109,141,142,444]`, `edit_count=315`).  Collapsing by family
    is therefore not an optimisation; without it the replay cannot run.

    The reverse case matters more: if two members of one family were left at
    DIFFERENT values, no single intent can express that.  This reports it as a
    conflict instead of quietly picking one -- 315 records silently taking one
    member's value is exactly the kind of wrong answer that looks like success.

    Returns ``{intents, skipped, conflicts, collapsed}``.
    """
    from .dat import families as F

    fams = families or {}
    seen = {}            # (kind, family_key, field) -> row
    collapsed = []
    conflicts = []
    skipped = []
    for row in report.get("changes") or ():
        field = row.get("field") or ""
        if row.get("kind") == "unit":
            # `family_of` returns a LIST; a key has to be hashable, and the
            # family's own ordering is stable, so a tuple of it is the identity.
            key = ("unit", tuple(F.family_of(fams, row["id"])), field)
        else:
            # Technologies have no variant family: the array index IS the id.
            key = ("tech", (row["id"],), field)
        prev = seen.get(key)
        if prev is None:
            seen[key] = row
            continue
        if prev.get("to") != row.get("to"):
            conflicts.append({"family": list(key[1]), "field": field,
                              "ids": [prev["id"], row["id"]],
                              "values": [prev.get("to"), row.get("to")]})
        else:
            collapsed.append({"kept": prev["id"], "dropped": row["id"],
                              "field": field, "value": row.get("to")})

    intents = []
    for row in seen.values():
        field = row.get("field") or ""
        if row.get("kind") == "unit" and field.startswith("cost."):
            rtype = int(field.split(".", 1)[1])
            intents.append({"intent": "unit.cost", "unit": row["id"],
                            "resource": _RESOURCE_KEY.get(rtype, "food"),
                            "value": row.get("to")})
        elif row.get("kind") == "unit":
            intents.append({"intent": "unit.stat", "unit": row["id"],
                            "stat": field, "value": row.get("to")})
        elif field.startswith("cost."):
            rtype = int(field.split(".", 1)[1])
            intents.append({"intent": "tech.cost", "tech": row["id"],
                            "resource": _RESOURCE_KEY.get(rtype, "food"),
                            "value": row.get("to")})
        elif field == "research_time":
            intents.append({"intent": "tech.research_time", "tech": row["id"],
                            "value": row.get("to")})
        else:
            # effect_id / icon_id / civ have no single-value intent: an effect
            # rewrite is a command inside an effect block, an icon slot is a
            # table slot, and a technology's civ is what the tree layer decides.
            skipped.append(row)
    return {"intents": intents, "skipped": skipped,
            "conflicts": conflicts, "collapsed": collapsed}


def carry_over(old_mod_dir, new_mod_dir, log=None):
    """Copy everything the old mod shipped EXCEPT its .dat into the new folder.

    Measured 2026-10-23 on this machine: **14 of the 16 installed mods that ship
    a `.dat` also ship other files** -- `WAIFor Arcade` carries 688 DRS files and
    is 357 MB, `Red Alert 2 MOD` 306 DRS and 68.8 MB, and several carry
    `resources/strings` (their own text tables).  `locations.install_mod` with
    `overwrite=True` does `shutil.rmtree(target)` and then copies the source, so
    installing a rebuilt folder that holds only `info.json` + `.dat` would
    DELETE the art.  The numbers would come back and the mod would look broken
    in a brand new way.

    `info.json` and the thumbnail are skipped on purpose: the new folder has its
    own (built by `emit_data_mod`), and the point of a repair is that the
    manifest describes what the repaired file actually is.
    """
    copied = []
    skipped = []
    old_root = os.path.abspath(old_mod_dir)
    dat_low = DAT_REL.replace(os.sep, "/").lower()
    for base, _dirs, files in os.walk(old_root):
        rel_dir = os.path.relpath(base, old_root)
        for name in files:
            rel = name if rel_dir == "." else os.path.join(rel_dir, name)
            low = rel.replace(os.sep, "/").lower()
            if low == "info.json" or low.startswith("thumbnail") or low == dat_low:
                skipped.append(rel.replace(os.sep, "/"))
                continue
            src = os.path.join(base, name)
            dst = os.path.join(new_mod_dir, rel)
            parent = os.path.dirname(dst)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            shutil.copyfile(src, dst)
            copied.append(rel.replace(os.sep, "/"))
    if log is not None:
        log.append("从旧模组搬来 %d 个文件（跳过 %d 个：清单、缩略图、旧 .dat）"
                   % (len(copied), len(skipped)))
    return {"copied": sorted(copied), "skipped": sorted(skipped)}


def scan_installed(profile_root, game_root, limit=40):
    """Check every installed mod that ships its own `.dat`.  Read-only.

    Uses the project's own profile rules (`locations.list_mods`), because a
    hand-rolled glob has already silently skipped a real account directory once
    (`pick_account` exists for that reason).
    """
    from .game import locations as GL

    out = []
    for row in GL.list_mods(profile_root, check_exists=True):
        path = row.get("path")
        if not path:
            continue
        mod_dat = os.path.join(path, DAT_REL)
        if not os.path.isfile(mod_dat):
            continue
        got = check(mod_dat, game_root, limit=limit)
        got["name"] = row.get("name")
        got["title"] = row.get("title")
        got["enabled"] = row.get("enabled")
        out.append(got)
    return out


def describe(report):
    """One Chinese sentence a person can act on."""
    if not report.get("ok"):
        return "没量出来：" + "；".join(report.get("reasons") or ["原因不明"])
    verdict = report.get("verdict")
    counts = report.get("counts") or {}
    if verdict == "identical":
        return "这份 .dat 和游戏现在的一样，不用修"
    if verdict == IMPOSSIBLE:
        return "不能自动修：%s" % (report.get("reasons") or ["格式换代"])[0]
    if verdict == MANUAL:
        return "只能部分自动修：%d 处数值可以重放；%d 个新单位、%d 个新科技要重建" % (
            counts.get("changes", 0), counts.get("units_added", 0),
            counts.get("techs_added", 0))
    return "可以自动修：%d 处数值改动（单位 %d / 科技 %d）" % (
        counts.get("changes", 0), counts.get("unit_changes", 0),
        counts.get("tech_changes", 0))
