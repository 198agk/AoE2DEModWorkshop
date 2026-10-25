# -*- coding: utf-8 -*-
"""Make one unit stand in for another when the map is generated.

``resources/_common/dat/objreplacement.json`` is the engine's own table for "on this
map, place B where A would have gone".  It is read at **map generation**, which was
measured on 2026-10-25: a match whose only data mod was this file (plus a ``.dat``
canary in the same folder) started with every villager standing on the ground as
scout 448, and the rule named villager 83.

What the layer can and cannot say (measured, not assumed)
---------------------------------------------------------
* **It has no per-civilization key.**  ``_probe/tmp_objrepl_intent_probe.py`` walked
  every key in every shipped row: ``object_id`` / ``object_override`` /
  ``replacement_object`` / ``chance`` / ``replacement_attribute`` /
  ``required_attribute`` / ``excluded_computer_players`` / ``technology`` /
  ``technology_state`` / ``attribute_name`` / ``name`` -- none of them selects a
  civilization.  A row applies wherever the source record exists, so an intent may
  not accept ``civs``: promising per-civ scope here would promise something the file
  cannot express.
* **It acts at map generation, not on existing units.**  Units trained after the
  match starts are ordinary units.  Anything else would be a different mechanism
  (``effect command type 3`` replaces a unit by id at runtime; that is a ``.dat``
  edit and a separate intent).
* **``chance`` is a percentage and lives inside ``object_override``.**  The shipped
  file uses it exactly twice, both ``50``, both on the villager sex swap.  A
  replacement written as ``50`` reads to a player as "sometimes it does not work",
  so this module always writes ``100``.
* **The replacement is silent when the record is absent.**  A row naming a unit that
  a civilization does not have simply does nothing there, with no log line.  The
  preview therefore prints both ids and both display names.

This file round-trips byte for byte through ``json.dumps(indent=4)``, unlike
``linkedTechs.json`` (which carries hand-typed whitespace like ``"StartingTech" :  1215``
and can only be *followed*, not reproduced).  So this module can make a stronger
promise than that one: every previous row survives key for key, and the unchanged
file serialises back to the shipped bytes.
"""

import io
import json
import os

OBJREPLACEMENT_REL = os.path.join("resources", "_common", "dat",
                                  "objreplacement.json")

# The shipped file uses exactly this shape; measured on the 2,533-byte file.
DEFAULT_CHANCE = 100


class ObjReplaceError(Exception):
    """A replacement that cannot be written, with a sentence a player can act on."""


def path_for(game_root):
    return os.path.join(game_root, OBJREPLACEMENT_REL)


def shipped_bytes(game_root):
    """The file as shipped, or ``None`` when this install does not have one."""
    path = path_for(game_root)
    try:
        with io.open(path, "rb") as fh:
            return fh.read()
    except (IOError, OSError):
        return None


def load(game_root):
    """The document, or ``{"objects": []}`` when the install has no file."""
    raw = shipped_bytes(game_root)
    if raw is None:
        return {"objects": []}
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except ValueError as exc:
        raise ObjReplaceError("这个版本的 %s 读不出来（%s）" % (OBJREPLACEMENT_REL, exc))
    if not isinstance(doc, dict):
        raise ObjReplaceError("%s 的顶层不是一个对象" % OBJREPLACEMENT_REL)
    doc.setdefault("objects", [])
    return doc


def detect_style(raw):
    """Indentation, line ending and trailing-newline of a real file.

    Read off the bytes instead of assumed: a mod that changes the line endings of a
    2.5 kB file is a 2.5 kB diff for no reason.
    """
    text = raw.decode("utf-8-sig")
    indent = None
    for line in text.splitlines():
        trimmed = line.lstrip(" ")
        if trimmed.startswith('"') and len(trimmed) != len(line):
            indent = len(line) - len(trimmed)
            break
    return {"indent": 4 if indent is None else indent,
            "newline": "\r\n" if b"\r\n" in raw else "\n",
            "trailing_newline": text.endswith("\n")}


def serialize(doc, style=None):
    style = style or {"indent": 4, "newline": "\r\n", "trailing_newline": True}
    text = json.dumps(doc, ensure_ascii=False, indent=style["indent"])
    if style["trailing_newline"]:
        text += "\n"
    if style["newline"] != "\n":
        text = text.replace("\n", style["newline"])
    return text.encode("utf-8")


def emit_files(doc, style=None):
    """``{relative path: bytes}`` for the mod emitter."""
    return {OBJREPLACEMENT_REL.replace(os.sep, "/"): serialize(doc, style)}


def rows(doc):
    """Every full replacement row, flattened into what a reader needs to see.

    Attribute-only rows (``Scout`` -> "Scout ID" 263) are reported as
    ``replacement_object is None`` rather than dropped: a reader asking "what does
    this file do to scouts" deserves to see that row too.
    """
    out = []
    for row in doc.get("objects") or ():
        override = row.get("object_override") or {}
        out.append({
            "source": row.get("object_id"),
            "source_name": row.get("name"),
            "target": override.get("replacement_object"),
            "target_name": override.get("name"),
            "chance": override.get("chance"),
            "attribute": override.get("replacement_attribute"),
            "technology": override.get("technology"),
        })
    return out


def source_ids(doc):
    """Which unit ids already have a row (they would conflict with a new one)."""
    return tuple(r["source"] for r in rows(doc) if r["source"] is not None)


def add_replacement(doc, source_id, target_id, source_name=None, target_name=None,
                    chance=DEFAULT_CHANCE, replace_existing=False, name_for=None):
    """Append one replacement row, or refuse with a sentence.

    Refusing when the source already has a row is deliberate: the shipped file
    already replaces villager 83 with villager 293 at ``chance 50``, so "villager
    becomes a scout" is not a new row, it is a **replacement of that row**.  Doing
    that silently would delete behaviour the player never looked at.

    ``name_for`` is an optional ``unit_id -> display name`` callable.  The shipped
    rows carry the game's English internal names, and the refusal sentence goes on
    screen, so a caller that has the Chinese names must pass them in rather than
    let 「Villager (Female)」 reach the player.
    """
    if source_id is None or target_id is None:
        raise ObjReplaceError("这句话要说清「把哪个换成哪个」，两个单位都得点名")
    if int(source_id) == int(target_id):
        raise ObjReplaceError("「%s」换成它自己没有意义" % (source_name or source_id))
    try:
        chance = int(chance)
    except (TypeError, ValueError):
        raise ObjReplaceError("「替换概率」得是一个整数百分数")
    if not 1 <= chance <= 100:
        raise ObjReplaceError("「替换概率」只能是 1 到 100，收到 %r" % chance)

    def _name(uid, fallback):
        if name_for is not None:
            try:
                got = name_for(uid)
            except Exception:                                   # noqa: BLE001
                got = None
            if got:
                return got
        return fallback

    existing = [r for r in rows(doc) if r["source"] == int(source_id)]
    if existing and not replace_existing:
        old = existing[0]
        # the shipped rows carry the game's *English* internal names ("Villager"),
        # so prefer the caller's Chinese name when it gave one -- this sentence goes
        # on screen, and 「Villager」 is not what the player typed.
        whose = source_name or _name(old["source"], old["source_name"] or str(old["source"]))
        what = _name(old["target"], old["target_name"] or str(old["target"]))
        raise ObjReplaceError(
            "「%s」已经有一条替换规则：%s%% 换成「%s」。要改它就说「替换现有的」"
            % (whose, old["chance"] if old["chance"] is not None else "?", what))

    row = {"name": source_name or str(source_id), "object_id": int(source_id),
           "object_override": {}}
    if target_name:
        row["object_override"]["name"] = target_name
    row["object_override"]["replacement_object"] = int(target_id)
    row["object_override"]["chance"] = chance

    kept = []
    replaced = 0
    for old_row in doc.get("objects") or ():
        if old_row.get("object_id") == int(source_id):
            replaced += 1
            continue
        kept.append(old_row)
    kept.append(row)
    doc["objects"] = kept
    return row, replaced


def describe(source_name, target_name):
    return "地图开局时，把「%s」换成「%s」" % (source_name, target_name)


def canonical(doc):
    """A comparable form, so a caller can say "every previous row survived"."""
    return json.dumps(doc.get("objects") or [], ensure_ascii=False, sort_keys=True)
