# -*- coding: utf-8 -*-
"""What the backend is doing right now, in a form the screen can draw.

Why this exists
---------------
Measured 2026-10-26 on this machine: from the server binding its socket to the
first answer on `/api/meta` is **10.7 seconds** -- `load_dat` 0.12, `Parser.parse`
5.20, `locate` 5.31, semantic index 0.03.  For those ten seconds the window showed
one static sentence ("正在读取游戏数据…") and the player's words were "加载得也太慢了，
而且没有加载进度条".

The load cannot get much faster (that time is spent walking 93 MB of records), so
the honest fix is to say where it is.  This module is the only place that knows,
because the work happens inside `Toolkit._ensure()`, which is called lazily from a
request thread.

Design notes that are load bearing
----------------------------------
* Weights are **measured**, not guessed: they are the seconds in the paragraph
  above, rounded.  A bar that jumps 2 % -> 90 % teaches the player not to trust it.
* `snapshot()` never blocks and never raises: it is called by an HTTP handler while
  the parser holds the GIL between bytecode instructions.  Worst case it reports a
  slightly stale stage, which is what a progress bar is.
* A stage that never ran stays 0 % instead of being skipped, so a run that dies in
  `locate` still shows why: the bar stops and the label names the stage.
"""

import threading
import time

_LOCK = threading.Lock()

# Seconds spent per stage, measured 2026-10-26 (see the docstring).  The numbers
# are relative weights, so a slower machine keeps the same shape.
STAGES = (
    ("inflate", "解压游戏数据", 2),
    # Added 2026-10-31 with `aoe2mod/dat/parsecache.py`.  A warm start reads the
    # parse back from disk in 1.6 s instead of computing it in 8.6 s, and this
    # stage is how the screen says so -- without it a warm start would jump from
    # "解压游戏数据 完成" straight to 100 % and look like it skipped two steps.
    # Weight 6 is the measured 0.04 s of hashing plus ~1.5 s of load, scaled to
    # the same unit as its neighbours: the bar moves at the speed the work does.
    ("cache", "读取上次的解析结果", 6),
    ("parse", "读取单位与建筑", 47),
    ("locate", "建立文明索引", 48),
    ("index", "整理中文名字", 2),
    ("ready", "可以开始了", 1),
)

_TOTAL = float(sum(w for _k, _l, w in STAGES))
_LABEL = dict((k, l) for k, l, _w in STAGES)

_state = {
    "stage": "starting",       # STAGES key, or "starting" before any work
    "done": [],                # stages finished, in order
    "reused": [],              # of those, the ones the parse cache supplied
    "started": None,           # wall clock of the first begin()
    "finished": None,          # wall clock of ready
    "error": None,             # a sentence, if the load failed
}


def begin(stage):
    """Mark `stage` as the one being worked on.  Safe to call twice."""
    with _LOCK:
        if _state["started"] is None:
            _state["started"] = time.time()
        if stage in _state["done"]:
            return
        _state["stage"] = stage


def done(stage):
    """Mark `stage` finished.  Order is not enforced; a repeat is a no-op."""
    with _LOCK:
        if stage not in _state["done"]:
            _state["done"].append(stage)
        if stage == "ready":
            _state["finished"] = time.time()
        # Leave `stage` pointing at what just finished, so a caller that polls
        # between two stages sees the one that produced the current number rather
        # than a stage that has not started.
        _state["stage"] = stage


def reused(stage):
    """Mark `stage` as served from the parse cache instead of being computed.

    A warm start never runs `parse` or `locate`, so without this the bar would
    sit at 8 % and then jump to 100 % when the file is read back -- the exact
    "the bar lied" failure this module was written to avoid.  The stages still
    count as finished (the data IS ready), but they are named as reused so the
    screen can say 「上次的结果还是最新的」 instead of claiming to have parsed.
    """
    with _LOCK:
        if stage not in _state["done"]:
            _state["done"].append(stage)
        if stage not in _state["reused"]:
            _state["reused"].append(stage)
        _state["stage"] = stage


def fail(message):
    """Record why the load stopped.  The bar keeps the percent it reached."""
    with _LOCK:
        _state["error"] = str(message)


def _percent(done_list):
    got = sum(w for k, _l, w in STAGES if k in done_list)
    return int(round(100.0 * got / _TOTAL))


def snapshot():
    """`{stage, label, percent, elapsed, ready, error, stages, cached}`.

    Never raises.
    """
    with _LOCK:
        stage = _state["stage"]
        done_list = list(_state["done"])
        reused_list = list(_state["reused"])
        started = _state["started"]
        finished = _state["finished"]
        error = _state["error"]
    percent = 100 if finished else _percent(done_list)
    elapsed = 0.0
    if started:
        elapsed = round((finished or time.time()) - started, 2)
    label = _LABEL.get(stage, "正在准备")
    # Say when a stage is being served from the parse cache.  Without this the
    # screen claims "读取单位与建筑" for work that did not happen -- the same lie
    # the cache stage exists to avoid, one line higher up.  `cache` itself is
    # exempt: its own label already says where the data came from.
    if stage in reused_list and stage != "cache":
        label = label + "（用上次的结果）"
    return {
        "stage": stage,
        "label": label,
        "percent": percent,
        "elapsed": elapsed,
        "ready": finished is not None,
        "error": error,
        "cached": bool(reused_list),
        "stages": [{"key": k, "label": l, "done": k in done_list,
                    "reused": k in reused_list}
                   for k, l, _w in STAGES],
    }


def reset():
    """Back to the starting state.  For tests and for a game-data re-read."""
    with _LOCK:
        _state.update({"stage": "starting", "done": [], "reused": [],
                       "started": None, "finished": None, "error": None})
