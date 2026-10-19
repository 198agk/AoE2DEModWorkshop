# -*- coding: utf-8 -*-
"""The prose the game ships, and the prose it does not.

"Names, icons and descriptions all available" is the goal; the first two are
done and this module is the third.  Its job is mostly to be exact about a gap:

**This build has no unit descriptions at all.**  2,690 of the 2,693 unit records
carry a non-zero `LanguageDLLHelp`, and of the 684 distinct ids they point at,
exactly ONE resolves to text in either language -- id 10500, whose value is
literally "[None]" in English and "[无]" in Chinese.  The whole 105xxx band is
absent from both string tables (0 ids in en, 0 in zh), while both tables carry
the same 36,351 ids, so this is not a missing translation: the ids themselves
were never written.  `help == name + 100000` holds for only 710 of 2,690, so it
is not an arithmetic mistake on our side either.

Therefore a UI must say "this version has no description for this unit" rather
than show a blank box -- or worse, borrow a technology's text and present it as
the unit's.

Technologies are different: they carry real text, unevenly.

    description  1,303 ids -> 541 resolve (zh and en in equal numbers)
    help         1,420 ids ->  31 resolve
    tech_tree    1,420 ids ->   4 resolve

The three fields are per-record blocks in `tech_names.json` (each with its own
`name_string_id`), while `name` is flattened onto the record itself -- reading
`name` like the others reports 0 of 1,510 and looks like a lost locale, which is
how this module's first probe went wrong.
"""
import json
import os

from . import index as _index

TECH_FIELDS = ("description", "help", "tech_tree")

#: Why a unit has no description, phrased for a screen.  The numbers behind it
#: are re-measured by `_probe/test_prose_supply.py`; keeping the sentence free of
#: them means it cannot go stale the way a hardcoded count does.
UNIT_NO_PROSE = ("这个版本没有单位描述：游戏的字符串表里没有单位帮助文本"
                 "（英文和中文都是空的，不是缺翻译）")


def _clean(block):
    """One stored block -> {zh,en,tw,name_string_id} or None if it holds no text."""
    if not isinstance(block, dict):
        # `name` is flattened onto the record; callers pass the fields they want.
        return None
    got = {"name_string_id": block.get("name_string_id") or 0,
           "zh": block.get("zh"), "en": block.get("en"), "tw": block.get("tw")}
    if not (got["zh"] or got["en"] or got["tw"]):
        return None
    return got


def for_entity(entity):
    """Everything this entity can say about itself, and why the rest is missing.

    Returns a dict with `ok`, `fields` (only the fields that carry text) and
    `missing` (field -> reason).  Never invents text.
    """
    if entity is None:
        return {"ok": False, "fields": {}, "missing": {},
                "why": "没有这个实体"}
    if entity.kind == "unit":
        return {"ok": False, "fields": {}, "missing": {},
                "why": UNIT_NO_PROSE}
    raw = getattr(entity, "_extra", None) or {}
    fields = {}
    missing = {}
    for name in TECH_FIELDS:
        block = _clean(raw.get(name))
        if block:
            fields[name] = block
        else:
            stored = (raw.get(name) or {}).get("name_string_id") if isinstance(
                raw.get(name), dict) else 0
            if stored:
                missing[name] = ("这条科技声明了 %s 的文本 id %d，"
                                 "但字符串表里没有这一条" % (name, stored))
            else:
                missing[name] = "这条科技没有%s" % _ZH_FIELD.get(name, name)
    return {"ok": bool(fields), "fields": fields, "missing": missing,
            "why": "" if fields else "这条科技在游戏里没有可显示的文字"}


_ZH_FIELD = {"description": "描述", "help": "帮助文本", "tech_tree": "科技树说明",
             "name": "名字"}


def coverage(idx=None):
    """Counts per field over the whole technology table, for a panel or a test."""
    idx = idx or _index.index()
    out = {}
    for name in TECH_FIELDS + ("name",):
        have_id = has_text = 0
        for e in idx.techs.values():
            raw = getattr(e, "_extra", None) or {}
            if name == "name":
                block = {"name_string_id": e.name_string_id,
                         "zh": e.zh, "en": e.en, "tw": e.tw}
            else:
                block = raw.get(name)
            if isinstance(block, dict) and block.get("name_string_id"):
                have_id += 1
            if _clean(block):
                has_text += 1
        out[name] = {"declared": have_id, "with_text": has_text}
    return out


def write_table(path=None):
    """Write the per-language prose block a UI can ship without the game files.

    Off by default -- the UI reads the game's own tables at runtime, and a second
    copy on disk is a copy that drifts.  Provided so an offline packaging step
    has something honest to embed.
    """
    idx = _index.index()
    rows = {}
    for tid, e in sorted(idx.techs.items()):
        got = for_entity(e)
        if got["fields"]:
            rows[str(tid)] = {"display": e.display, "fields": got["fields"]}
    doc = {"source": "the game's own key-value string tables, via "
                     "aoe2mod.semantic.index; units carry no prose in this build",
           "techs": rows}
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
    return doc
