# -*- coding: utf-8 -*-
"""Locate, validate and pack ONE named field of a unit or a technology record.

WHY THIS EXISTS
---------------
`unitfields` and `techfields` answer "where is every field of this record".  They
do not answer "may this value be written there" -- that check lived inside
`ui/server.py`, one copy for a unit and one for a technology.  A third caller
appeared: `App.rebuild` replays a build record's `unit.field` / `tech.field`
intents after a game patch, and it needs the same checks against a DIFFERENT
buffer (the game's own file, not the editor's session).

Copying those checks a third time would produce three ideas of "read-only" and
three ideas of "the value did not change".  That divergence is the defect class
this project has already paid for twice (see `techlabels.RESOURCE_ZH`, where a
copied comment had the cost-resource order backwards).  So the checks live here,
once, and every caller routes through them.

WHAT IT DELIBERATELY DOES NOT KNOW
----------------------------------
Nothing about sessions, HTTP, mods or the screen.  It reads bytes and returns
either a packed field or a Chinese refusal.
"""
from __future__ import annotations

import struct

#: Byte widths of every scalar the two record families use.
KINDS = {"u8": 1, "u16": 2, "i16": 2, "i32": 4, "u32": 4, "f32": 4}

#: The hard wall each width imposes.  A value outside it is not a clamp: it is
#: the neighbouring field, so it is refused rather than truncated.
WIDTH = {"u8": (0, 255), "u16": (0, 65535), "i16": (-32768, 32767),
         "i32": (-2147483648, 2147483647), "u32": (0, 4294967295),
         "f32": (-3.4e38, 3.4e38)}

FMT = {"u8": "<B", "u16": "<H", "i16": "<h", "i32": "<i", "u32": "<I", "f32": "<f"}

#: How each family names itself in a sentence.  A refusal that says "这条记录"
#: while the player is looking at a technology reads like a different object.
WHERE = {"unit": "这条记录", "tech": "这条科技"}


def labels(kind):
    """The label table for one record family."""
    if kind == "tech":
        from aoe2mod.game import techlabels as TL
        return TL
    from aoe2mod.game import fieldlabels as FL
    return FL


def index(kind, raw, gv):
    """`{key: {"start","end"}}` for every record of `kind` in `raw`.

    A unit is keyed `(civ_index, unit_id)` because the `.dat` stores one copy per
    civilisation and editing British's 村民 must not touch French's.  A
    technology is keyed by its position in the array: the record carries no id.

    The scan walks 93 MB (~7 s for units, ~6.5 s for techs) and patches the
    parser's own `read_*` while it does, so a leftover byte means the addresses
    are NOT the ones the engine would walk -- raised rather than handed out.
    """
    if kind == "tech":
        from aoe2mod.dat import techfields as TF
        techs, _stats, leftover = TF.scan(raw, gv, light=True)
        if leftover:
            raise RuntimeError(
                "科技扫描没有走完整个文件（还剩 %d 字节），说明记录的字段地址不可信，"
                "这时候让你编辑会写进隔壁字段。" % (leftover,))
        return {t["index"]: {"start": t["start"], "end": t["end"]}
                for t in techs}
    from aoe2mod.dat import unitfields as UF
    units, _stats, leftover = UF.scan(raw, gv, light=True)
    if leftover:
        raise RuntimeError(
            "字段扫描没有走完整个文件（还剩 %d 字节），说明记录的字段地址不可信，"
            "这时候让你编辑会写进隔壁字段。" % (leftover,))
    return {(u["civ_index"], u["id"]): {"start": u["start"], "end": u["end"]}
            for u in units}


def fields_at(kind, raw, gv, rec):
    """Every named field of one record, decoded from `raw` on demand."""
    if kind == "tech":
        from aoe2mod.dat import techfields as TF
        return TF.fields_at(raw, gv, rec["start"])
    from aoe2mod.dat import unitfields as UF
    return UF.fields_at(raw, gv, rec["start"])


def plan(kind, raw, gv, rec, name, value):
    """May this value be written to this field?  Pack it if so.

    Returns ``{"ok": True, offset, packed, before, value, kind, field, label}``
    or ``{"ok": False, error, ...}``.  `unchanged` is set on the one refusal that
    is not a mistake -- a value the player typed that equals what is there.

    Four refusals, each a way to lose an edit while reporting success:

      * a name that is not in this record -- there is no "close enough" field,
        and a typo must not resolve to a neighbour;
      * a read-only field (a length prefix, a count the list itself defines);
      * a string, whose length prefix makes a fixed-width write meaningless:
        shortening leaves stale bytes, lengthening overwrites the next field;
      * a value outside the field's own byte width.
    """
    L = labels(kind)
    where = WHERE.get(kind, "这条记录")
    flds = fields_at(kind, raw, gv, rec)
    f = flds.get(name)
    if f is None:
        close = [k for k in flds if name.lower() in k.lower()][:6]
        return {"ok": False,
                "error": "%s里没有叫 %s 的字段" % (where, name),
                "did_you_mean": close}
    meta = L.meta_for(name)
    label = meta.get("zh") or name
    if meta.get("ro"):
        return {"ok": False,
                "error": "「%s」是只读的：%s" % (
                    label,
                    meta.get("hint")
                    or "它的值由数据本身决定，改了会让整条记录读不下去。")}
    fkind = f["kind"]
    if fkind == "str":
        return {"ok": False,
                "error": "「%s」是字符串，不能用定宽方式改写：它的长度前缀写了字节数，"
                         "改短会留下残字、改长会覆盖下一个字段。" % (label,)}
    old = f["value"]
    try:
        new = float(value) if fkind == "f32" else int(value)
    except (TypeError, ValueError):
        return {"ok": False,
                "error": "%s 要填%s，收到的是 %r" % (
                    label, "小数" if fkind == "f32" else "整数", value)}
    W = WIDTH.get(fkind)
    if W and not (W[0] <= new <= W[1]):
        return {"ok": False,
                "error": "「%s」在文件里只占 %s，装不下 %s（范围 %s..%s）" % (
                    label, fkind, new, W[0], W[1])}
    # Then the sane range: advice, but checked, because a HitPoints of -3 is a
    # crash you can only diagnose by reading the file back.
    if "lo" in meta and new < meta["lo"]:
        return {"ok": False,
                "error": "%s 不能小于 %s（%s）" % (
                    label, meta["lo"],
                    meta.get("hint") or "这是引擎里合理的下限")}
    if "hi" in meta and new > meta["hi"]:
        return {"ok": False,
                "error": "%s 不能大于 %s（%s）" % (
                    label, meta["hi"],
                    meta.get("hint") or "这是引擎里合理的上限")}
    same = (new == old) if fkind == "f32" else (int(new) == old)
    if same:
        return {"ok": False, "error": "值没变，还是 %s" % (old,),
                "unchanged": True}
    packed = struct.pack(FMT[fkind], new)
    off = f["offset"]
    before_bytes = bytes(raw[off:off + len(packed)])
    return {"ok": True, "field": name, "label": label, "kind": fkind,
            "offset": off, "before": old, "value": new,
            "packed": packed, "before_bytes": before_bytes,
            # How many bytes this write actually flips.  0 is possible even when
            # the VALUE differs -- `1.45` and `1.4` can round to the same f32 --
            # and a caller must not report an edit that moved no byte.
            "changed": sum(1 for a, b in zip(before_bytes, packed) if a != b)}


def apply(buf, offset, packed):
    """Put `packed` at `offset` and say how many bytes actually changed.

    Diffing only the field's own bytes, not the whole 93 MB stream: `before` IS
    the diff, and a field is 1..4 bytes.  Comparing whole buffers per edit took
    ~0.4 s and allocated two copies.
    """
    before = bytes(buf[offset:offset + len(packed)])
    changed = sum(1 for a, b in zip(before, packed) if a != b)
    if changed:
        buf[offset:offset + len(packed)] = packed
    return {"before_bytes": before, "changed": changed}
