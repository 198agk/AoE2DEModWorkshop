# -*- coding: utf-8 -*-
"""Progress for long jobs that a *request* starts, not the app's own startup.

Why this exists
---------------
`aoe2mod/progress.py` describes the ten-second startup (inflate -> parse ->
locate -> ready).  It cannot describe what happens when the player clicks a unit
in the field editor: opening the editor the first time builds the field index,
and that is **14.52 s measured 2026-11-02** (136,861 records, 93 MB walked) -- a
sentence saying 「读取「民兵」…」 for fourteen seconds, with no way to tell
"working" from "hung".  The player's words about the same problem at startup
were 「加载得也太慢了，而且没有加载进度条」.

What makes it honest
--------------------
* The number is **bytes already walked**, reported by the scanner itself, not a
  timer and not a guess.  Measured: stage 8 (Civs) is 10.04 of the 10.45 s a
  unit scan costs, and it advances from 4.2 % to 99.8 % of the file, so a bar
  driven by `pos / len(raw)` moves at the speed the work does.
* A job reports `running` explicitly.  A finished job keeps its last percent, so
  the page can tell "index ready, nothing to draw" from "still working" -- and
  it is why a *cached* open (0.003 s) shows no bar at all instead of flashing
  100 %.
* `snapshot()` never blocks and never raises: it is read by an HTTP thread while
  the scanning thread holds the GIL between bytecode instructions.  Same rule as
  `progress.py`, same reason.
* One slot per key.  Two scans of the same kind cannot overlap (they serialise
  on `parser._PARSE_LOCK`), so a key is a single job, not a queue.
"""

import threading
import time

_LOCK = threading.Lock()

# key -> state.  Keys are "unit" and "tech" today; the dict is generic so a new
# long job only needs a name.
_jobs = {}

# Bumped by every `begin()`, never rewound -- not even by `reset()`.  This is
# what lets a page tell "the job I am waiting for" from "the job that was in the
# slot a second ago": the bar is drawn BEFORE the request that starts the job,
# so the first poll can land on the PREVIOUS snapshot, which is finished and
# reads 100 %.  Measured 2026-11-13 on the mod-upgrade check: the bar sat at
# 100 % for the whole eleven minutes, because that stale answer also said
# `running: false` and the poller stopped.  A monotonic id makes the stale
# answer identifiable instead of merely plausible.
_SEQ = 0


def begin(key, label, total):
    """Start (or restart) the job `key`.  `total` is in the unit `update` gets."""
    global _SEQ
    with _LOCK:
        _SEQ += 1
        _jobs[key] = {
            "label": label,
            "total": max(1, int(total)),
            "done": 0,
            "started": time.time(),
            "finished": None,
            "error": None,
            "seq": _SEQ,
        }


def update(key, done):
    """Record absolute progress.  Cheap: one dict write under a short lock."""
    with _LOCK:
        job = _jobs.get(key)
        if job is None or job["finished"] is not None:
            return
        # Clamp: a scanner that overshoots its own estimate must not print 103 %.
        job["done"] = max(0, min(int(done), job["total"]))


def finish(key):
    with _LOCK:
        job = _jobs.get(key)
        if job is None:
            return
        job["done"] = job["total"]
        job["finished"] = time.time()


def fail(key, message):
    """Keep the percent reached: a bar that hits an error still says where."""
    with _LOCK:
        job = _jobs.get(key)
        if job is None:
            return
        job["error"] = str(message)
        job["finished"] = time.time()


def snapshot(key):
    """`{key,label,percent,done,total,elapsed,running,error,seq}`.  Never raises.

    `seq` is the id `begin()` handed this run.  A caller that knows which run it
    is waiting for (it can pass the id it saw, or compare against the id it saw
    before it made its request) can drop an answer that belongs to the run
    before -- which is the case that used to freeze a bar at 100 %.
    """
    with _LOCK:
        job = _jobs.get(key)
        if job is None:
            return {"key": key, "label": "", "percent": 0, "done": 0,
                    "total": 0, "elapsed": 0.0, "running": False,
                    "error": None, "known": False, "seq": 0}
        label = job["label"]
        total = job["total"]
        done = job["done"]
        started = job["started"]
        finished = job["finished"]
        error = job["error"]
        seq = job.get("seq", 0)
    end = finished or time.time()
    return {
        "key": key,
        "label": label,
        "percent": int(round(100.0 * done / total)) if total else 0,
        "done": done,
        "total": total,
        "elapsed": round(end - started, 2) if started else 0.0,
        "running": started is not None and finished is None and not error,
        "error": error,
        "known": True,
        "seq": seq,
    }


def reset(key=None):
    """Forget one job, or all.  For tests and for a game-data re-read."""
    with _LOCK:
        if key is None:
            _jobs.clear()
        else:
            _jobs.pop(key, None)
