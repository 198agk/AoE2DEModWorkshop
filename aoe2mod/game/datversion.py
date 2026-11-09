# -*- coding: utf-8 -*-
"""Which GAME VERSION a ``.dat`` was built for -- read off the file, not guessed.

Reported 2026-11-07, verbatim: 「我要显示这个数据模组是哪个版本的，现在这个10
倍资源文明联盟3倍科技是很旧版本的，你能让工具检测出来吗」.

The player is right on both halves.  ``format 54`` is not a game version: it is
the .dat's internal FileVersion ordinal (``GV_C32``), it exists so the parser
knows which field widths to use, and it says nothing about how old the content
is.  A mod built in 2021 and one built last week both read ``VER 8.9`` today,
because the modder edited the file the game shipped at the time.  So "which
version" has to be answered from evidence inside the file, and there are three
independent kinds of it:

* **The FileVersion head** (``VER 7.8`` vs ``VER 8.9``).  This is the layout the
  file was written with.  ``VER_TO_GV`` orders the layout steps, so the distance
  between two heads is a count of format steps -- not years, but a real measure
  of how far behind the file is.
* **The record counts.**  Every game update that added civilisations, graphics
  or sounds grew these.  Measured 2026-11-07 on this machine, the install's own
  file is ``civs 63 / units 1701 / graphics 21001 / effects 1500 / sounds 930``;
  ``10 倍资源文明联盟3倍科技`` is ``civs 46 / graphics 13012 / sounds 685`` with
  a ``VER 7.8`` head.  Forty-six civilisations is the shape of a base from
  before the 2023 and 2025 expansions; no amount of editing turns it into 63.
* **The file's own timestamp** -- weak, and deliberately not used as a verdict,
  because a mod folder re-copied yesterday keeps its old content.

Why counts and not a hash of the whole file: a modder changes unit stats by the
hundred, so a content hash never matches anything and answers "different", not
"older".  Counts are what a game update changes and a stat edit does not.

The cost, and why it is cached
------------------------------
Only stages 1..7 are needed, and they live in the first ~4 MB of an inflated
file.  Inflating a capped prefix (8 MB, retried at 24 and 64 MB if stage 7 is
cut off) and walking the stage table costs **0.17-0.35 s per file**, measured on
the 14 candidates here: 3.6 s for the whole machine.  That is too slow for the
chooser's first paint, and the walk holds the parser lock, so this module never
runs on a request thread: ``App.dat_versions`` starts one background worker,
answers whatever is already known, and the screen asks again.  Results are
cached in ``provenance.state_dir()/dat_versions.json`` keyed by real path with
(mtime, size) as the freshness check, so the second visit costs a dict lookup.
"""

import contextlib
import io
import json
import os
import threading
import time
import zlib

from ..dat import parser as P
from ..dat import tablefields as TF
from ..mod import provenance as PV

#: Inflated prefixes tried in order.  Stage 7 ended by 3.9 MB on every file
#: measured here, but a mod with 9 998 graphics is 30 MB into stage 3 alone, so
#: the prefix is a retry ladder rather than a constant.
CAPS = (8 << 20, 24 << 20, 64 << 20)

CACHE_NAME = "dat_versions.json"
CACHE_VERSION = 1

_LOCK = threading.Lock()
_MEM = {}            # normcase path -> {"mtime", "bytes", "facts"}
_MEM_LOADED = False
_WORKER = {"thread": None, "busy": False, "error": None, "asked": 0}

#: The stage names this module needs.  `TF.stage_offsets` returns
#: ``{name: (start, end)}``; the counted record families all put their count
#: first, which is why no record is ever decoded here.
STAGE_SOUNDS = "2 Sounds"
STAGE_GRAPHICS = "3 Graphics"
STAGE_EFFECTS = "5 Effects"
STAGE_UNITS = "7 UnitHeaders"


def _state_file():
    return os.path.join(PV.state_dir(), CACHE_NAME)


def _load_mem():
    global _MEM_LOADED
    with _LOCK:
        if _MEM_LOADED:
            return
        _MEM_LOADED = True
        try:
            with io.open(_state_file(), "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if doc.get("version") == CACHE_VERSION:
                for path, row in (doc.get("items") or {}).items():
                    if isinstance(row, dict) and row.get("facts"):
                        _MEM[path] = row
        except (IOError, OSError, ValueError):
            pass


def _save_mem():
    path = _state_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"version": CACHE_VERSION, "items": _MEM}, fh,
                      ensure_ascii=False, sort_keys=True)
        os.replace(tmp, path)
    except (IOError, OSError, ValueError):
        # A cache that cannot be written is not an error the player must hear
        # about: every answer can be recomputed in a third of a second.
        pass


def _stamp(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return {"mtime": int(st.st_mtime), "bytes": int(st.st_size)}


def _inflate_prefix(path, cap):
    """Inflate at most ``cap`` bytes of the gzip stream; report if it stopped.

    Reading 64 KB at a time rather than the whole compressed file matters: the
    base install's container is 12 MB for 93 MB of stream, so a full inflate
    would read work nobody uses.
    """
    out = bytearray()
    try:
        with open(path, "rb") as fh:
            d = zlib.decompressobj(-15)
            while len(out) < cap:
                chunk = fh.read(1 << 16)
                if not chunk:
                    break
                out += d.decompress(chunk, cap - len(out))
                if d.eof:
                    break
    except (IOError, OSError, zlib.error):
        return None, True
    return out, len(out) < cap


def _counts(raw, offs):
    def i16(at):
        return int.from_bytes(raw[at:at + 2], "little", signed=True)

    def i32(at):
        return int.from_bytes(raw[at:at + 4], "little", signed=True)

    out = {}
    if STAGE_SOUNDS in offs:
        out["sounds"] = i16(offs[STAGE_SOUNDS][0])
    if STAGE_GRAPHICS in offs:
        out["graphics"] = i16(offs[STAGE_GRAPHICS][0])
    if STAGE_EFFECTS in offs:
        out["effects"] = i32(offs[STAGE_EFFECTS][0])
    if STAGE_UNITS in offs:
        out["units"] = i32(offs[STAGE_UNITS][0])
        # Stage 7 ends where stage 8's `i16 civ_count` begins -- the civ records
        # themselves are the expensive part of a parse and are never touched.
        out["civs"] = i16(offs[STAGE_UNITS][1])
    return out


def probe(path, caps=CAPS):
    """The facts a chooser can print about one file.  Never raises.

    Returns ``{"ver","gv","bytes","truncated","sounds","graphics","effects",
    "units","civs","cap","seconds"}``, with the counts absent when the stage
    table could not be reached -- an unreadable file still gets a row, because
    hiding it would make the chooser disagree with Explorer.
    """
    t0 = time.time()
    head = None
    gv = None
    try:
        head = PV.head_version(path)
        if head:
            gv = P.gv_from_version_string(head)
    except Exception:
        gv = None
    out = {"ver": head, "gv": gv, "read_bytes": 0, "truncated": True, "cap": 0}
    for cap in caps:
        raw, complete = _inflate_prefix(path, cap)
        out["cap"] = cap
        if raw is None:
            break
        out["read_bytes"] = len(raw)
        out["truncated"] = not complete
        loud = io.StringIO()
        offs = {}
        try:
            # `Parser._stage` prints one line per stage unconditionally; that is
            # right for the CLI and wrong 14 times per screen.
            with contextlib.redirect_stdout(loud):
                offs, _stats = TF.stage_offsets(raw, "7 ")
        except Exception:
            offs = {}
        if STAGE_UNITS in offs and STAGE_UNITS in [k for k in offs]:
            out.update(_counts(raw, offs))
            break
        if complete:
            break
    out["seconds"] = round(time.time() - t0, 3)
    return out


def _order():
    """GameVersion ordinals in the order the game grew them."""
    return sorted(set(P.VER_TO_GV.values()))


def steps_between(old_gv, new_gv):
    """Layout steps from ``old`` to ``new``; positive when ``new`` is newer.

    Symmetric, and therefore dangerous to read at a call site: "+11" out of this
    function says nothing about which file is old.  Use `steps_behind` when the
    question is "how far behind".
    """
    if old_gv is None or new_gv is None:
        return None
    order = _order()
    if old_gv not in order or new_gv not in order:
        return None
    return order.index(new_gv) - order.index(old_gv)


def steps_behind(facts_gv, base_gv):
    """How many format steps ``facts_gv`` is behind ``base_gv``; negative = ahead.

    Two wrong sentences came out of reading `steps_between` at a call site ("early"
    and "newer" swapped twice, measured 2026-11-07), so the direction lives in
    this name instead.
    """
    got = steps_between(base_gv, facts_gv)
    return None if got is None else -got


def compare(facts, base, base_label="游戏本体"):
    """Say whether ``facts`` was built on an older game than the baseline.

    The verdict comes from the FORMAT HEAD alone.  ``VER 7.8`` vs ``VER 8.9`` is
    eleven layout steps, and that is the only reading that can make a parser
    disagree with the game.  Record counts are printed as an observation, not
    folded into the verdict, because they cannot answer this question:

    * a mode may trim civilisations on purpose -- ``Pompeii`` says 18 and is
      exactly as new as the install; calling it old teaches the player to
      ignore the line (measured 2026-11-07: it was a false "older");
    * a mod built on an older but compatible base has fewer sounds than today's
      install (769 vs 930) while changing nothing that matters -- that was the
      other false "older", and it fired on 11 of the 12 mods here;
    * an old file re-copied yesterday keeps its old content, so timestamps are
      no evidence at all.

    ``steps`` is positive when ``facts`` is BEHIND ``base`` (how many layout
    steps older), which is the direction of the sentence printed from it.
    """
    if not facts or not facts.get("gv"):
        return {"age": "unknown", "steps": None,
                "text": "这一份的版本头读不出来，说不清它是哪一版游戏做的。"}
    base = base or {}
    steps = steps_behind(facts.get("gv"), base.get("gv"))
    bits = []
    if steps is not None and steps > 0:
        bits.append("%s 比%s早 %d 个格式台阶"
                    % (facts.get("ver") or "?", base_label, steps))
    elif steps is not None and steps < 0:
        bits.append("%s 比%s还新 %d 个格式台阶"
                    % (facts.get("ver") or "?", base_label, -steps))
    for key, name in (("civs", "个文明"), ("graphics", "条图形"),
                      ("sounds", "条音效")):
        mine, theirs = facts.get(key), base.get(key)
        if not isinstance(mine, int) or not isinstance(theirs, int):
            continue
        if mine != theirs:
            bits.append("%d %s（%s %d）" % (mine, name, base_label, theirs))
    if steps is None:
        age = "unknown"
    elif steps > 0:
        age = "older"          # positive = behind the install
    elif steps < 0:
        age = "newer"
    else:
        age = "same"
    if not bits:
        bits.append("和%s同一个格式，记录数也一样" % base_label)
    elif age == "same":
        bits.insert(0, "和%s同一个格式" % base_label)
    return {"age": age, "steps": steps, "text": "；".join(bits) + "。"}


def cached(path):
    """The facts already known for ``path``, or None.  Never computes."""
    _load_mem()
    key = os.path.normcase(os.path.abspath(path))
    row = _MEM.get(key)
    if not row:
        return None
    st = _stamp(path)
    if not st or st["mtime"] != row.get("mtime") or st["bytes"] != row.get("bytes"):
        return None
    return row.get("facts")


def remember(path, facts):
    key = os.path.normcase(os.path.abspath(path))
    st = _stamp(path) or {"mtime": 0, "bytes": 0}
    with _LOCK:
        _MEM[key] = {"mtime": st["mtime"], "bytes": st["bytes"], "facts": facts}
    _save_mem()


def forget(path=None):
    """Drop one file's cached facts, or all of them."""
    _load_mem()
    with _LOCK:
        if path is None:
            _MEM.clear()
        else:
            _MEM.pop(os.path.normcase(os.path.abspath(path)), None)
    _save_mem()


def known(paths):
    """``{path: facts}`` for the ones already measured.  No I/O beyond stat."""
    out = {}
    for path in paths:
        got = cached(path)
        if got:
            out[path] = got
    return out


def _work(paths):
    """Measure the files nobody has measured yet.  Runs on the worker thread."""
    try:
        for path in paths:
            if cached(path):
                continue
            facts = probe(path)
            remember(path, facts)
    except Exception as exc:                      # never kill the worker thread
        _WORKER["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        _WORKER["busy"] = False


def start_worker(paths):
    """Measure ``paths`` in the background, one pass at a time.

    A second call while a pass is running is dropped rather than queued: the
    next screen refresh asks again, and a queue of 14-file passes would hold the
    parser lock for longer than the answer is worth.
    """
    todo = [p for p in paths if p and not cached(p)]
    if not todo:
        return {"started": False, "todo": 0}
    with _LOCK:
        if _WORKER["busy"]:
            return {"started": False, "todo": len(todo), "busy": True}
        _WORKER["busy"] = True
        _WORKER["error"] = None
        _WORKER["asked"] += 1
        th = threading.Thread(target=_work, args=(todo,), name="dat-version",
                              daemon=True)
        _WORKER["thread"] = th
    th.start()
    return {"started": True, "todo": len(todo)}


def status():
    return {"busy": bool(_WORKER["busy"]), "error": _WORKER["error"],
            "measured": len(_MEM), "asked": _WORKER["asked"]}
