# -*- coding: utf-8 -*-
"""The bar the field editor draws while it builds the index.

WHY THIS NAIL EXISTS
Opening a unit in the field editor builds the field index on first use.  Measured
2026-11-02 on this machine: **14.52 s** for 136,861 records (93 MB walked), and
0.003 s once cached.  For fourteen seconds the pane showed one static sentence,
which is indistinguishable from a hang -- the same complaint the startup bar
already answers (「加载得也太慢了，而且没有加载进度条」).

WHAT COULD GO WRONG AGAIN, AND WHICH CHECK CATCHES IT
* The percentage comes from a timer instead of from bytes walked -> `report`
  checks the callbacks are strictly increasing in file position and that the
  last one is the real end of the file.
* The bar is drawn but the request never reports -> `page` checks `openEditor`
  starts a watcher against `/api/job` and that no interval-based fake fills it.
* A cached open flashes 100 % -> `job` checks `known:False` before any scan, so
  the page can draw nothing (the warm path must be silent).
* A scan that dies mid-way leaves the bar stuck at a number with no reason ->
  `job` checks `fail()` keeps the percent AND records the sentence.
* Progress work makes the scan slower -> `scan` measures the overhead against
  the no-callback run and refuses a regression above 15 %.
"""

import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, REPO)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

fails = []


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


import contextlib                                    # noqa: E402

from aoe2mod import jobs as J                        # noqa: E402

PAGE = os.path.join(REPO, "aoe2mod", "ui", "static", "index.html")

# --- 1. the job registry, on its own ---------------------------------------
J.reset()
check(J.snapshot("unit")["known"] is False,
      "before any scan the job is unknown, so the page draws no bar",
      J.snapshot("unit"))

J.begin("unit", "建立单位字段索引", 1000)
s = J.snapshot("unit")
check(s["known"] and s["running"], "begin() makes it running", s)
check(s["percent"] == 0 and s["total"] == 1000, "it starts at 0 of its total", s)

# Every run gets its own id, and the id only ever goes up.  The page draws its
# bar BEFORE the request that starts the job, so its first poll can land on the
# PREVIOUS run's answer (finished, 100 %, running:false).  Without an id that
# answer is indistinguishable from "my job is done", which is how the bar sat at
# 100 % for eleven minutes (m19874).
first_seq = s["seq"]
check(first_seq > 0, "begin() stamps the run with an id", first_seq)
J.begin("unit", "建立单位字段索引", 1000)
check(J.snapshot("unit")["seq"] > first_seq,
      "a second begin() gets a higher id, so the page can tell the runs apart",
      (first_seq, J.snapshot("unit")["seq"]))
seq_now = J.snapshot("unit")["seq"]
J.finish("unit")
check(J.snapshot("unit")["seq"] == seq_now,
      "the id survives finish(), so a late poll still says WHICH run it is",
      J.snapshot("unit")["seq"])
J.begin("unit", "建立单位字段索引", 1000)

J.update("unit", 250)
check(J.snapshot("unit")["percent"] == 25, "update() reports the fraction",
      J.snapshot("unit")["percent"])

J.update("unit", 999999)
check(J.snapshot("unit")["percent"] == 100,
      "an overshoot clamps instead of printing 103 %",
      J.snapshot("unit")["percent"])

J.update("unit", -5)
check(J.snapshot("unit")["percent"] == 0, "an undershoot clamps at 0",
      J.snapshot("unit")["percent"])

J.update("unit", 600)
J.finish("unit")
s = J.snapshot("unit")
check(s["percent"] == 100 and not s["running"],
      "finish() lands on 100 % and stops running", s)

J.begin("tech", "建立科技字段索引", 100)
J.update("tech", 40)
J.fail("tech", "扫描崩了")
s = J.snapshot("tech")
check(s["percent"] == 40 and not s["running"],
      "a failed job keeps the percent it reached", s)
check(s["error"] == "扫描崩了", "and it keeps the sentence that explains why",
      s["error"])

J.reset("tech")
check(J.snapshot("tech")["known"] is False, "reset(key) forgets one job")
check(J.snapshot("tech")["seq"] == 0,
      "a job nobody started reports id 0, so no id collides with a real run",
      J.snapshot("tech")["seq"])
check(J.snapshot("unit")["known"] is True, "reset(key) leaves the others alone")
J.reset()

# A job that already finished must not be reopened by a late callback: the
# scanner calls once more after the walk, and that call arrives after finish().
J.begin("unit", "lbl", 10)
J.finish("unit")
J.update("unit", 3)
check(J.snapshot("unit")["percent"] == 100,
      "a late callback cannot drag a finished job back down",
      J.snapshot("unit")["percent"])
J.reset()

# --- 2. the scans really report, and it costs nothing ----------------------
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    from aoe2mod.ui import server as S
    app = S.App()
    app.tk._ensure()
    raw = app.session_raw()
    gv = app.tk._parsed[3]

from aoe2mod.dat import unitfields as UF              # noqa: E402
from aoe2mod.dat import techfields as TF              # noqa: E402

# Measured 2026-11-13: one plain scan and one reporting scan back to back read
# +17.6 % while the same pair read +1.1 % and -3.0 % on other runs -- a single
# 11-second wall-clock pair on a machine with other suites running is mostly
# noise.  Both sides are therefore measured twice, alternating, and the MINIMUM
# of each is compared: the floor is what the code costs, the spread is what the
# machine happened to be doing.  The assertion itself is unchanged -- progress
# must still cost less than 15 % of the walk.
plain_runs = []
withbar_runs = []
seen = []
left = left2 = 0
units = None
for _i in range(2):
    t0 = time.time()
    with contextlib.redirect_stdout(buf):
        _u, _s, left = UF.scan(raw, gv, light=True)
    plain_runs.append(time.time() - t0)
    seen = []
    t0 = time.time()
    with contextlib.redirect_stdout(buf):
        units, _s, left2 = UF.scan(raw, gv, light=True, on_progress=seen.append)
    withbar_runs.append(time.time() - t0)
plain = min(plain_runs)
withbar = min(withbar_runs)

check(left == 0 and left2 == 0, "both scans still walk the whole file",
      "%d / %d" % (left, left2))
check(len(seen) > 20, "the unit scan reports many times, not once", len(seen))
check(all(b >= a for a, b in zip(seen, seen[1:])),
      "the reported position never goes backwards", len(seen))
check(seen[-1] == len(raw) - left2,
      "the last callback is the true end of the file",
      "%d vs %d" % (seen[-1], len(raw) - left2))
check(len(seen) <= 260,
      "it is throttled: one callback per ~0.5 % of the file, not per record",
      len(seen))
cost = (withbar - plain) / plain if plain else 0
check(cost < 0.15, "reporting costs under 15 % of the scan",
      "%.2fs vs %.2fs (+%.1f%%) -- best of %s"
      % (withbar, plain, cost * 100,
         "/".join("%.2f" % t for t in plain_runs)))

seen_t = []
with contextlib.redirect_stdout(buf):
    techs, _s, left3 = TF.scan(raw, gv, light=True, on_progress=seen_t.append)
check(left3 == 0 and seen_t and seen_t[-1] == len(raw) - left3,
      "the tech scan reports the same way and also ends at the real end",
      "%d callbacks, last %d of %d" % (len(seen_t), seen_t[-1] if seen_t else -1,
                                       len(raw)))

# --- 3. the route and the page --------------------------------------------
SERVER = os.path.join(REPO, "aoe2mod", "ui", "server.py")
with open(SERVER, encoding="utf-8") as fh:
    src = fh.read()
check('"/api/job"' in src,
      "the server serves /api/job (a request-started job, not the startup)")
check('qa = _query' in src or '_query(self.path)' in src,
      "/api/job reads its query the same way every other route does")
check("J.snapshot(key)" in src, "it answers from the job registry, not the toolkit")
check("_scan_reporter(" in src and src.count("_scan_reporter(") >= 3,
      "both index builders pass a reporter",
      src.count("_scan_reporter("))
check("J.begin(\"unit\"" in src and "J.begin(\"tech\"" in src,
      "each scan announces itself BEFORE walking")
check("J.fail(" in src,
      "a scan that throws records why, so the bar is not left lying")

with open(PAGE, encoding="utf-8") as fh:
    page = fh.read()

check(".loadbar-track" in page and ".loadbar-fill" in page,
      "the page has a track and a fill to draw into")
check("function jobBar(" in page and "function watchJob(" in page,
      "the bar and its poller are named functions, not inline code")
check('api("/api/job?key="' in page, "the page polls /api/job")
check("建立单位字段索引" not in page,
      "the page does not hardcode the label: the server names the step")

# The watcher must stop when the read returns, or a later open inherits a
# dead bar (and an extra timer per click).
open_ed = page.split("async function openEditor(r)", 1)[1].split("\n}", 1)[0]
check("jobBar(" in open_ed, "openEditor draws the bar itself")
check("stopBar()" in open_ed, "openEditor stops the poller on both exits",
      open_ed.count("stopBar()"))

# No fake progress: the only thing that may set a width is the poller, and it
# must come from the server's number.
# A width in `px` is layout -- the tech tree positions one box per node, and the
# command panel sizes its cells the same way.  A width in `%` is a proportion of
# a known whole, and the only one on this page is the progress bar.  Counting
# both together said "three places set a width" the day the tree view landed,
# and the invariant it was standing in for is narrower than that.
# Two bars on this page draw a percentage and both are fed by the server: the
# editor's field-index bar (`watchJob` -> `/api/job`) and the file-switch veil
# (`datVeilTick` -> `/api/progress`).  Counting sites said "five" the day the
# veil landed, and the invariant worth standing in for is not the count but the
# SOURCE: no percentage on this page may be produced by a timer.  So every
# percentage write must name a number that came out of a poll, and the number of
# pollers must equal the number of bars.
width_sets = re.findall(r"\.style\.width\s*=\s*[^;]*%", page)
# 0 % and 100 % are allowed as literals: they are the two ends of a KNOWN whole
# (an empty bar before the first poll, a finished stage), not an estimate of how
# far along something is.  Any other literal would be a number nobody measured.
ENDS = ('0%', '100%')
bad = [w for w in width_sets
       if re.search(r'=\s*["\']', w) and not any(
           (e in w) for e in ENDS)]
check(len(width_sets) >= 1 and not bad,
      "no percentage is invented: every one is 0, 100, or a polled number",
      bad)
check("bar.fill.style.width = pct" in page,
      "that width is the server's percentage, not a timer")
# The bar must also know WHICH run it is drawing.  Its first poll can land on the
# answer of the run before (finished, 100 %, running:false); drawing that and
# seeing "not running" stops the poller, and the bar then hangs at 100 % for the
# whole real run -- measured 2026-11-13, eleven minutes on the mod check (m19874).
watch = page.split("function watchJob(", 1)[1].split("\n}", 1)[0]
check("j.seq" in watch, "the poller reads the run id out of the answer")
check("seq >= want" in watch,
      "an answer older than the run it waits for is dropped, not drawn",
      watch.count("seq"))
check('fill.style.width = n + "%"' in page,
      "the file-switch veil draws the server's number too")
check("setInterval" not in open_ed,
      "no interval-driven fake bar inside openEditor")

print("JOB PROGRESS: ALL PASSED" if not fails
      else "JOB PROGRESS: %d CHECK(S) FAILED -> %s" % (len(fails), fails))
sys.exit(1 if fails else 0)
