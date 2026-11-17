# -*- coding: utf-8 -*-
"""Group technologies so that researching one closes the others.

``resources/_common/dat/linkedTechs.json`` is the engine's own way of saying
"these technologies are exclusive": the shipped file has 20 groups, and the
mechanism the file expresses is not a new one invented here -- Paphos already
ships ``MutuallyExclusive`` groups (Satrapies / Oligarchy / Democracy /
Tyranny), and those are the same shapes a player would want for a custom
choice.

Why this layer instead of an effect command
-------------------------------------------
The engine's ``type 102`` command ("disable a technology") does exist and was
measured: every effect in the shipped Toggleable groups carries one command per
sibling that disables it, e.g. ``tech 1202 Oligarchy`` effect 1192 begins

    #0 (102, -1, -1, -1, 1203.0)      <- disable Democracy
    #1 (102, -1, -1, -1, 1204.0)      <- disable Tyranny

and the shipped Cycle groups (1215-1217) carry zero such commands.  Writing
those commands by hand is possible, but it means an effect id per technology,
a ``required tech`` list per technology, and a button slot per technology --
three couplings that can each be wrong separately.  The JSON layer states the
same thing in one record and lets the engine derive the rest.

What this module does NOT claim
-------------------------------
The shipped groups are read by the engine -- that is measured, because the
Paphos civilization's choice screen exists.  Whether a group *added by a mod*
is honoured has not been tested yet; that is what a canary experiment is for.
This module writes the file and reports what it did; it does not say the game
will show the choice.

Shape of the file (measured, 20 groups shipped)
-----------------------------------------------
``{"LinkedTechs": [{"NameId": 424001, "Comment": "Satrapies",
                    "Local": true, "Type": "MutuallyExclusive",
                    "Techs": [1195, 1196, 1197]}, ...]}``

* ``NameId`` is a string id; it is *not* part of the mechanic (Pompeii reuses
  424010 for a different group), so it is carried for readability only.
* ``Local`` means per-instance placement; every shipped group is ``true``.
* ``Type`` is one of ``MutuallyExclusive`` / ``Toggleable`` / ``Cycle``.
* ``Techs`` is the member list.
"""

import io
import json
import os

LINKED_TECHS_REL = os.path.join("resources", "_common", "dat", "linkedTechs.json")

TYPES = ("MutuallyExclusive", "Toggleable", "Cycle")

# The first ``NameId`` this project may hand out.  The shipped Paphos block
# occupies 424001..424020, and **all twenty of those ids are defined in the
# string tables** -- 424001 is "Satrapies".  So the old constant here (424001)
# made every group this project wrote display under somebody else's name;
# measured 2026-10-22 by reading the locale tables: 424001..424020 defined,
# 424021 the first free id.
#
# This is not cosmetic.  Two groups sharing a ``NameId`` are indistinguishable
# on screen, and a group named "Satrapies" is a lie about what the player
# chose.  Allocation is therefore computed, never assumed: see
# :func:`next_name_id`.
DEFAULT_NAME_ID = 424021


class LinkedTechError(Exception):
    """A group that cannot be written, with a reason a player can act on."""


def path_for(game_root):
    return os.path.join(game_root, LINKED_TECHS_REL)


def load(game_root):
    """Read the shipped file.  Returns ``(doc, note)``.

    ``note`` is ``"shipped"``, ``"missing"`` or ``"rebuilt"``.  A missing file
    is not an error: a group can still be written, because the engine only
    needs the shape, but the caller has to be told that the other groups the
    player had vanish -- that is a file the player would notice.
    """
    p = path_for(game_root)
    if not os.path.isfile(p):
        return {"LinkedTechs": []}, "missing"
    with io.open(p, encoding="utf-8-sig") as fh:
        try:
            doc = json.load(fh)
        except ValueError as exc:
            return {"LinkedTechs": []}, "rebuilt: %s" % exc
    if not isinstance(doc, dict) or not isinstance(doc.get("LinkedTechs"), list):
        return {"LinkedTechs": []}, "rebuilt: no LinkedTechs array"
    return doc, "shipped"


def shipped_bytes(game_root):
    """The file exactly as it is on disk, or ``None``."""
    p = path_for(game_root)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as fh:
        return fh.read()


def detect_style(raw):
    """The formatting the shipped file uses, so a rewrite does not reformat it.

    This is not cosmetic.  The shipped file is pretty-printed with CRLF; a mod
    that ships the same CONTENT in compact form still replaces the player's file
    on disk, so every line they or another mod ever added shows up as changed.

    Detected from the BYTES, not by trying to reproduce them: the shipped file
    carries hand-written spacing that no `json.dumps` produces (measured --
    ``"StartingTech" :  1215``, a space before the colon and two after), so a
    byte-exact round trip is impossible and pretending to check for one would
    warn on every single build about a difference that is only whitespace.

    Returns a dict for :func:`serialize`: ``indent``, ``newline``,
    ``trailing_newline``.
    """
    if not raw:
        return {"indent": None, "newline": "\n", "trailing_newline": True}
    newline = "\r\n" if b"\r\n" in raw else "\n"
    trailing = raw.endswith(b"\n")
    # The indent is the number of spaces before the first key on a nested line.
    indent = None
    for line in raw.split(newline.encode()):
        stripped = line.lstrip(b" ")
        if stripped and stripped != line and stripped.startswith(b'"'):
            indent = len(line) - len(stripped)
            break
    return {"indent": indent or None, "newline": newline,
            "trailing_newline": trailing}


def groups(doc):
    return list(doc.get("LinkedTechs") or ())


def group_of(doc, tech_id):
    """Every group that already holds ``tech_id``."""
    out = []
    for g in groups(doc):
        if tech_id in (g.get("Techs") or ()):
            out.append(g)
    return out


def next_name_id(doc, start=DEFAULT_NAME_ID):
    """The first ``NameId`` at or after ``start`` that no shipped group uses.

    Computed from the file rather than assumed, because the shipped block is
    not fixed: Paphos added nineteen ids at once, and a community mod that adds
    groups will take ids of its own.  A collision shows up as two groups wearing
    the same name, which looks like a bug in this tool.
    """
    used = set()
    for g in groups(doc):
        try:
            used.add(int(g.get("NameId")))
        except (TypeError, ValueError):
            continue
    nid = int(start)
    while nid in used:
        nid += 1
    return nid


def add_group(doc, techs, name_id=None, comment="", kind="MutuallyExclusive",
              local=True, starting_tech=None, instant=None):
    """Append one group.  ``doc`` is mutated and returned.

    Refusals are deliberate and each is a sentence a player can act on:

    * fewer than two technologies is not a choice;
    * an unknown ``Type`` would be written and then silently ignored;
    * a technology that is already in a group would end up governed by two
      records, and the shipped file never does that (0 of 20 groups overlap).

    A ``Cycle`` group is shaped differently from the other two, and the
    difference is not cosmetic -- it is what the engine reads:

        {"NameId": 424010, "Comment": "Merchant Trade Rates",
         "Type": "Cycle", "StartingTech": 1215, "Instant": true,
         "Techs": [1215, 1216, 1217]}

    All four shipped cycles (424010 / 424012 / 424013 / 424014) carry
    ``StartingTech`` and ``Instant`` and carry NO ``Local`` key; every
    MutuallyExclusive and Toggleable group in the same file carries ``Local``
    first and neither of those two.  Measured 2026-11-11 by reading the
    shipped ``resources/_common/dat/linkedTechs.json`` byte for byte.

    ``StartingTech`` defaults to the first member, which is what all four
    shipped cycles say.  ``Instant`` defaults to true for Cycle (a flip button
    that made the player wait out a research animation is not a flip button).
    Both are refused when they contradict the member list.
    """
    techs = [int(t) for t in techs]
    if len(techs) < 2:
        raise LinkedTechError(
            "一组至少要有两项科技，否则没有可选项。")
    if len(set(techs)) != len(techs):
        raise LinkedTechError("同一项科技在一组里出现了两次。")
    if kind not in TYPES:
        raise LinkedTechError(
            "「%s」不是引擎认识的分组类型；只能是 %s。" % (kind, "、".join(TYPES)))
    taken = {}
    for t in techs:
        already = group_of(doc, t)
        if already:
            taken[t] = already[0].get("Comment") or already[0].get("NameId")
    if taken:
        raise LinkedTechError(
            "这些科技已经在别的组里了：%s。一组科技只能被一条记录管，"
            "否则两条记录会互相覆盖。"
            % "、".join("#%d（%s）" % (k, v) for k, v in sorted(taken.items())))
    if name_id is None:
        name_id = next_name_id(doc)
    if kind == "Cycle":
        first = int(starting_tech) if starting_tech is not None else techs[0]
        if first not in techs:
            raise LinkedTechError(
                "第一页（起始科技 %d）不在这一组的成员里。" % (first,))
        rec = {
            "NameId": int(name_id),
            "Comment": comment,
            "Type": kind,
            "StartingTech": first,
            "Instant": True if instant is None else bool(instant),
            "Techs": techs,
        }
    else:
        rec = {
            "NameId": int(name_id),
            "Comment": comment,
            "Local": bool(local),
            "Type": kind,
            "Techs": techs,
        }
    doc.setdefault("LinkedTechs", []).append(rec)
    return doc


def drop_group(doc, name_id):
    """Remove one group by ``NameId``.  True when something was removed.

    Used when the player deletes the last page of a flip button: the group
    would otherwise name technologies that no longer exist, and the engine
    reads the file before it reads the .dat.
    """
    want = int(name_id)
    before = len(groups(doc))
    doc["LinkedTechs"] = [g for g in groups(doc)
                          if int(g.get("NameId", -1) or -1) != want]
    return len(groups(doc)) != before


def serialize(doc, style=None):
    """The bytes to ship.

    ``ensure_ascii=False`` on purpose: the shipped file is UTF-8 with real CJK
    in ``Comment`` (``"文明联盟"`` shows up in community copies), and escaping it
    to ``\\uXXXX`` would be a different file for no reason.

    Formatting follows ``style`` (see :func:`detect_style`) so that adding one
    group does not rewrite every other line of the player's file.  The shipped
    file is ``indent=2`` with CRLF and a trailing newline.  The default is
    compact, which is what a brand-new file gets when there is nothing to
    imitate.

    Only the SHAPE is imitated (indent, newline, trailing newline).  The shipped
    file also contains hand-written spacing around some colons that no encoder
    reproduces; that whitespace is not preserved, and no check here claims it is.
    """
    style = style or {"indent": None, "newline": "\n"}
    indent = style.get("indent")
    newline = style.get("newline") or "\n"
    if indent:
        text = json.dumps(doc, ensure_ascii=False, indent=indent)
    else:
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    if newline != "\n":
        text = text.replace("\n", newline)
    if style.get("trailing_newline"):
        text += newline
    return text.encode("utf-8")


def emit_files(doc, style=None):
    """``{relative path with / separators: bytes}`` for the mod emitter."""
    return {LINKED_TECHS_REL.replace(os.sep, "/"): serialize(doc, style)}


def cycle_boxes(pages_by_box, minimum=2):
    """Turn the pages this session wrote into ``Cycle`` group descriptions.

    ``pages_by_box`` is ``{(building, button): [tech ids]}`` -- exactly what
    ``pseudopage.read_cycles`` reports for the file being saved.  A box with
    ONE page is not a cycle: pressing it is a plain research button, and the
    engine draws it as one, which is the honest thing for the first page a
    player builds.

    The starting technology is the LOWEST id of the box.  That is not arbitrary:
    a page's units are usually already on the building when the box is first
    built (that is what ``card_put`` wrote), and the pages after it only become
    visible once a page turns them on -- so the earliest record is the one whose
    effect matches what the building already shows.  The shipped cycles are all
    written that way too (424010 starts at 1215, the first of 1215/1216/1217).
    """
    out = []
    for (bld, btn), ids in sorted((pages_by_box or {}).items()):
        techs = [int(t) for t in (ids or ())]
        if len(techs) < int(minimum):
            continue
        out.append({"building": int(bld), "button": int(btn),
                    "techs": techs, "starting": min(techs)})
    return out


def sync_cycles(doc, boxes, comment=""):
    """Make ``doc`` carry exactly the ``Cycle`` groups ``boxes`` describe.

    Returns ``(added, removed)``.  ``removed`` counts records this call had to
    drop, and every one of them shared a technology with a box being written:
    the engine refuses to have one technology governed by two records (the
    shipped file never does it, 0 of 20 groups overlap), so a stale record from
    an earlier save of the same box has to go before the new one can land.

    Groups that touch none of our technologies are left exactly as they are --
    the player's own 20-odd groups, and any other mod's, survive byte for byte
    as far as the JSON encoder can express them.
    """
    mine = set()
    for box in boxes or ():
        mine.update(int(t) for t in (box.get("techs") or ()))
    if not mine:
        return 0, 0
    keep, removed = [], 0
    for g in groups(doc):
        held = set()
        for t in (g.get("Techs") or ()):
            try:
                held.add(int(t))
            except (TypeError, ValueError):
                continue
        if held & mine:
            removed += 1
            continue
        keep.append(g)
    doc["LinkedTechs"] = keep
    added = 0
    for box in boxes or ():
        techs = [int(t) for t in (box.get("techs") or ())]
        if len(techs) < 2:
            continue
        label = comment or ("%s 第 %d 格" % (box.get("building"), box.get("button")))
        add_group(doc, techs, comment=label, kind="Cycle",
                  starting_tech=box.get("starting"))
        added += 1
    return added, removed


def emit_cycles(game_root, boxes, comment=""):
    """``{mod relative path: bytes}`` for the file with our cycles added.

    ``None`` when there is nothing to write, so a save that never touched a
    flip button does not ship a copy of a 3.9 KB file the player already has
    (a mod file REPLACES the player's, so copying it also freezes every other
    mod's groups at this moment in time).
    """
    boxes = [b for b in (boxes or ()) if len(b.get("techs") or ()) >= 2]
    if not boxes:
        return None
    doc, _note = load(game_root)
    style = detect_style(shipped_bytes(game_root))
    added, removed = sync_cycles(doc, boxes, comment=comment)
    if not added:
        return None
    return emit_files(doc, style)

def describe(tech_names, kind, comment=""):
    """The sentence the preview and the mod title both use."""
    names = "、".join(tech_names)
    if kind == "MutuallyExclusive":
        what = "只能研究其中一个"
    elif kind == "Toggleable":
        what = "可以互相开关"
    else:
        what = "按顺序循环"
    tail = ("（%s）" % comment) if comment else ""
    return "%s %s%s" % (names, what, tail)
