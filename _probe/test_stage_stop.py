# -*- coding: utf-8 -*-
"""Three threads must not be able to kill each other's stage walk.

Reported 2026-11-06, verbatim (screenshot of the tech tab on a 125 MB mod .dat):

    读不到字段：_Stop: 没有说明

`tablefields.stage_offsets` patches the module-wide `Parser._stage` to stop the
parse early, then restores it.  Two things were wrong until that day:

  * `orig = P.Parser._stage` was read BEFORE `with P._PARSE_LOCK:`.  A thread that
    blocked on the lock had already snapshotted the CURRENT holder's wrapper as
    "the original", so when its turn came it called a wrapper that was installed
    by someone else and was already gone.
  * `class _Stop(Exception)` was defined inside the function, so every call made a
    NEW class.  A wrapper nested inside another raised a class the outer
    `except` could never match.

Either one alone turns a stopped walk into an uncaught exception; together they
made the tech tab unreadable whenever a second scan overlapped it.  On the
shipped 93 MB file the scans are short enough that the window rarely opens; on
the 125 MB mod with 5,874 techs it opened on the first tab switch.

This pin is written to catch a REGRESSION of both halves, so it asserts shape as
well as behaviour:

  1. behaviour: three threads scanning at once, repeatedly, none of them dies;
  2. shape: `_StageStop` is a module-level class (same object every call);
  3. shape: the `orig = P.Parser._stage` line sits INSIDE the lock;
  4. behaviour: a single-threaded walk still stops early and still returns the
     stage offsets it always did.

Run: python -X utf8 _probe/test_stage_stop.py
"""
import io
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A
from aoe2mod.dat import parser as P
from aoe2mod.dat import tablefields as TF

SRC = os.path.join(ROOT, "aoe2mod", "dat", "tablefields.py")

FAILED = []


def ck(what, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", what,
                         (" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILED.append(what)
    return ok


def section(title):
    print()
    print("=== %s ===" % title)


tk = A.open_toolkit()
_ = tk.version
raw = tk._raw
print("data: %d bytes, %d civs, %d techs" % (len(raw), len(tk._civs), len(tk._stats["techs"])))

# ---------------------------------------------------------------------------
section("1. the stopping class is one class for the whole module")
# ---------------------------------------------------------------------------
src = io.open(SRC, encoding="utf-8").read()
ck("`_StageStop` is defined at module level",
   re.search(r"^class _StageStop\(Exception\):", src, re.M) is not None)
ck("no `_Stop` class is defined inside the function",
   re.search(r"^\s+class _Stop\(", src, re.M) is None)
ck("the early stop raises the module-level class",
   re.search(r"raise _StageStop\(\)", src) is not None)
ck("the early stop is caught by the module-level class",
   re.search(r"except _StageStop:", src) is not None)

# ---------------------------------------------------------------------------
section("2. `orig` is read inside the lock")
# ---------------------------------------------------------------------------
i_lock = src.index("with P._PARSE_LOCK:")
i_orig = src.index("orig = P.Parser._stage")
i_stage = src.index("P.Parser._stage = stage")
ck("the lock comes before `orig = P.Parser._stage`", i_lock < i_orig, (i_lock, i_orig))
ck("`orig` is read before the patch is installed", i_orig < i_stage, (i_orig, i_stage))
# A waiter must not be able to snapshot a wrapper: everything from the lock to the
# `try:` has to be inside the `with`.
block = src[i_lock:i_stage]
ck("nothing between the lock and the patch reads the global",
   "P.Parser._stage" in block and block.count("P.Parser._stage") == 1, block[:200])

# ---------------------------------------------------------------------------
section("3. three threads scanning at once, for a while, all survive")
# ---------------------------------------------------------------------------
TABLES = ("graphic", "sound", "effect")
errors = []
rounds = {t: 0 for t in TABLES}
DEADLINE = time.time() + 12.0


def worker(table):
    name = threading.current_thread().name
    try:
        while time.time() < DEADLINE:
            TF.scan(raw, table)
            rounds[table] += 1
    except BaseException as exc:  # noqa: BLE001 -- that is the point
        errors.append((name, type(exc).__name__, str(exc)))


threads = [threading.Thread(target=worker, args=(t,), name=t, daemon=True)
           for t in TABLES]
for t in threads:
    t.start()
for t in threads:
    t.join()
print("  rounds:", rounds)
ck("no thread died", not errors, errors)
ck("every thread actually did work", all(v > 0 for v in rounds.values()), rounds)

# ---------------------------------------------------------------------------
section("4. one thread still stops early, and still returns the offsets")
# ---------------------------------------------------------------------------
t0 = time.time()
offs, stats = TF.stage_offsets(raw, "3 ")
dt = time.time() - t0
print("  stages: %d, %.2f s" % (len(offs), dt))
ck("stage 1..3 are reported", any(k.startswith("1 ") for k in offs)
   and any(k.startswith("3 ") for k in offs), sorted(offs))
ck("the stop happens before the civs stage", not any(k.startswith("8 ") for k in offs),
   sorted(offs))
first = sorted(offs.items())[0]
ck("the first stage starts at 0", first[1][0] == 0, first)
ck("it is far cheaper than a full parse", dt < 6.0, "%.2f s" % dt)
ck("the patch is uninstalled again", P.Parser._stage.__name__ == "_stage",
   P.Parser._stage)
ck("stats still carry the file version", (stats or {}).get("file_version") is not None,
   list((stats or {}).keys())[:6])

# ---------------------------------------------------------------------------
print()
if FAILED:
    print("STAGE STOP: %d FAILED -> %r" % (len(FAILED), FAILED[:6]))
    sys.exit(1)
print("STAGE STOP: A STOPPED WALK IS ONE CLASS AND ONE LOCK -- THREE THREADS CAN "
      "SCAN AT ONCE WITHOUT ANY OF THEM SEEING `_Stop: 没有说明`, AND A SINGLE "
      "WALK STILL STOPS WHERE IT ALWAYS DID")
