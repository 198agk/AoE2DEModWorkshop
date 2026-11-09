# -*- coding: utf-8 -*-
"""Refuse to load the game data when the shipped tables belong to another `.dat`.

Why this module exists at all
-----------------------------
On 2026-10-28 at 05:54 Steam replaced the game's `.dat`
(93,268,152 -> 93,272,287 bytes, 104 files touched, ``sounds`` 769 -> 930).
Both engines then kept using offset tables that had been measured from the old
file: every sampled ``hit_points`` offset was wrong by 4397 bytes for
civilisation 1 and 4357 for civilisation 6 -- and not by a constant, so no delta
could be subtracted.  ``/api/stat`` answered ``ok:true`` throughout.  A corrupting
write that reports success is worse than a refusal that explains, because
nothing downstream can tell the two apart.

The native engine grew the guard first (``desktop/aoe2mod-serve/src/lib.rs:228
pub fn stamp_mismatch``).  This is the same rule for the Python engine, and it
exists here for two reasons that are worth stating plainly:

* **A declared stamp is a sandbox declaration.**  ``AOE2MOD_DAT_STAMP`` is how
  every gate points the binary at a stamp it built itself.  Ignoring it would put
  this engine in exactly the position ``AOE2MOD_PROFILE`` was in -- measured
  2026-10-31, that one silently wrote into the player's real mod list because
  only the native side honoured it.
* **One behaviour, not two.**  The shipped exe now runs whichever engine the
  folder carries.  A guard that exists on one side and not the other makes the
  same folder behave differently depending on which engine happened to answer,
  which is the class of bug that produced ``/api/civ`` 404s in the first place.

A note on what is actually compared
-----------------------------------
The comparison is on the DECOMPRESSED stream, never on the file: the game
re-packs the container between builds without changing its content, so a
file-level hash would cry wolf on every re-install with identical data.  That
lesson is the native guard's too.

The Python engine measures its write offsets by parsing the live `.dat` on every
run, so a stale table cannot make *this* engine patch the wrong byte.  The check
is still worth its cost: the tables and the stamp travel together in a release,
so a stamp that disagrees with the installed `.dat` means the bundle is
inconsistent, and the one thing that must not happen is a player finding out
after a build.
"""
import hashlib
import json
import os

#: Where the stamp may be declared, highest priority first.
STAMP_ENV = "AOE2MOD_DAT_STAMP"
STAMP_NAME = "dat_stamp.json"


class StampError(Exception):
    """The tables do not belong to this game data.  The message says why."""


def candidates(app_hint=None):
    """Every place the stamp may live, in the order they are tried.

    Mirrors ``table_paths`` in the native engine
    (``desktop/aoe2mod-serve/src/sentences.rs:1299``) so a folder that works for
    one engine works for the other: an explicit declaration, then
    ``<app>/_golden/``, then a walk up from the working directory (which is what
    finds the repo during development -- a shipped folder has no repo above it).
    """
    out = []
    declared = os.environ.get(STAMP_ENV)
    if declared:
        out.append(declared)
    for key in ("AOE2MOD_ROOT", "AOE2MOD_APP"):
        root = os.environ.get(key)
        if root:
            out.append(os.path.join(root, "_golden", STAMP_NAME))
    if app_hint:
        out.append(os.path.join(app_hint, "_golden", STAMP_NAME))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out.append(os.path.join(os.path.dirname(here), "_golden", STAMP_NAME))
    out.append(os.path.join(here, "_golden", STAMP_NAME))
    walk = os.getcwd()
    while True:
        out.append(os.path.join(walk, "_golden", STAMP_NAME))
        parent = os.path.dirname(walk)
        if parent == walk:
            break
        walk = parent
    seen = set()
    uniq = []
    for p in out:
        key = os.path.normcase(os.path.abspath(p))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def stamp_path(app_hint=None):
    """The first candidate that exists, or ``None``."""
    for p in candidates(app_hint):
        if os.path.isfile(p):
            return p
    return None


def raw_sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_stamp(path):
    """The parsed stamp document.  A file that will not parse is a refusal."""
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8-sig")
    except (IOError, OSError) as exc:
        raise StampError("读不到偏移表清单 %s：%s" % (path, exc))
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise StampError("%s 不是合法 JSON：%s" % (path, exc))
    if not isinstance(doc, dict):
        raise StampError("%s 的内容不是一个对象" % path)
    want = (doc.get("dat") or {}).get("raw_sha256") or ""
    if not want:
        raise StampError("%s 里没有 dat.raw_sha256" % path)
    return doc


def mismatch(raw, stamp=None, dat_display=""):
    """``None`` when the tables belong to this data, else a sentence saying why.

    ``raw`` is the decompressed ``.dat`` stream.  Callers already have it in
    memory after ``Parser.load_dat``, so this costs one sha256 over 93 MB
    (~0.036 s, measured in ``mod/provenance.py``), not a second read.

    Where ``stamp`` is ``None`` the file is looked up; a missing stamp is only an
    error when one was DECLARED, because a development checkout legitimately has
    no ``_golden`` while the repo's own suites run.  ``stamp=""`` means "there is
    no stamp anywhere" and is reported as such.
    """
    declared = os.environ.get(STAMP_ENV)
    path = stamp if stamp is not None else stamp_path()
    if path is None or path == "":
        if declared:
            raise StampError(
                "%s=%s 指向的清单不存在。没有它就无法确定偏移表还属不属于"
                "这份游戏数据——而按过期表写字节会改到别的位置，还会返回"
                " ok:true。修复：py _probe/make_dat_stamp.py"
                % (STAMP_ENV, declared))
        return None
    doc = read_stamp(path)
    want = doc["dat"]["raw_sha256"].strip().lower()
    got = raw_sha256(raw)
    if got == want:
        return None
    was = (doc.get("dat") or {}).get("raw_bytes")
    was_text = "%s" % was if was is not None else "未知"
    return ("游戏数据更新了：偏移表是按另一份 .dat 量的（%s 字节，sha %s…），"
            "现在这份 %s 是 %d 字节（sha %s…）。按旧表写字节会改到别的位置，"
            "而且会返回 ok:true——所以这里先停下。"
            "修复：重新生成偏移表（py _probe/make_stat_offsets.py 等），"
            "再跑 py _probe/make_dat_stamp.py。"
            % (was_text, want[:12], dat_display or "游戏数据",
               len(raw), got[:12]))


def check(raw, dat_display=""):
    """Raise :class:`StampError` when the data disagrees with the stamp."""
    why = mismatch(raw, dat_display=dat_display)
    if why:
        raise StampError(why)
    return True
