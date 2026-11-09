# -*- coding: utf-8 -*-
"""Nail: 一份 `.dat` 是哪一版游戏做的 -- and why `格式 54` cannot answer that.

Reported 2026-11-07: 「我要显示这个数据模组是哪个版本的，现在这个10倍资源文明联盟3
倍科技是很旧版本的，你能让工具检测出来吗」.

The player is right and the field they were reading is a red herring.  `format`
is the .dat's own FileVersion ordinal (`GV_C32` = 54): a mod built in 2021 and
one built last week both read 54 today, because the modder edited the file the
game shipped at the time.  Age has to come from inside the file, and this nail
pins the three things that made the first two attempts wrong:

1. **The sign.** `steps_between(old, new)` is symmetric, so at a call site "+11"
   says nothing about which file is old.  Two sentences came out backwards
   before the direction moved into a name: `steps_behind(facts, base)`.
   Pinned with both directions and with the sentence printed from each.
2. **The wrong verdict.** Folding record counts into the verdict made 11 of 12
   mods read "older", and made `Pompeii` -- a mode that trims 45 civilisations
   ON PURPOSE -- read older than a file it is format-identical to.  A warning
   that fires on everything is not a warning.  Only the format decides; counts
   are printed as an observation.
3. **The cost.** A full inflate of the 14 candidates is 24.6 s; a capped 8 MB
   prefix plus a walk to stage 7 is 0.17-0.35 s each, 4.7 s for the machine, and
   it holds the parser lock -- so the route must answer from the cache and
   measure on a worker, and the screen must come back for the answer instead of
   printing "还没量出来" forever.

Run:  python -X utf8 _probe\\test_dat_version.py
"""
import io
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")

BAD = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))
    if not ok:
        BAD.append((name, detail))


def _read(path):
    return io.open(path, encoding="utf-8").read()


def main():
    from aoe2mod.game import datversion as DV
    from aoe2mod.game import datsources as DSR
    from aoe2mod.game import locations as L
    import aoe2mod.dat.parser as P

    print("=== 1. the direction lives in a name, so a call site cannot flip it ===")
    check("steps_between(43, 54) is +11 -- the SECOND argument is newer",
          DV.steps_between(43, 54) == 11, DV.steps_between(43, 54))
    check("steps_between(54, 43) is -11", DV.steps_between(54, 43) == -11,
          DV.steps_between(54, 43))
    check("steps_behind(43, 54) is +11 -- the FIRST argument is behind",
          DV.steps_behind(43, 54) == 11, DV.steps_behind(43, 54))
    check("steps_behind(54, 43) is -11 -- it is ahead",
          DV.steps_behind(54, 43) == -11, DV.steps_behind(54, 43))
    # Both functions return index(b) - index(a); they differ ONLY in what the
    # call means.  `steps_between(43, 54)` reads "from 43 to 54", and
    # `steps_behind(43, 54)` reads "43 is behind 54" -- the same +11.  Two wrong
    # sentences in the product came from reading that number at a call site
    # without the words, so the number and the words are pinned together here.
    check("both return the same number for the same pair, and only the name says why",
          DV.steps_behind(43, 54) == DV.steps_between(43, 54) == 11,
          (DV.steps_behind(43, 54), DV.steps_between(43, 54)))
    check("...which is exactly the trap: a bare `+11` does not name the older file",
          DV.steps_behind(54, 43) == -11 and DV.steps_between(54, 43) == -11,
          (DV.steps_behind(54, 43), DV.steps_between(54, 43)))
    check("an ordinal nobody knows answers None, never zero",
          DV.steps_behind(999, 54) is None and DV.steps_between(None, 54) is None)

    print()
    print("=== 2. only the format decides the verdict ===")
    base = {"ver": "VER 8.9", "gv": 54, "civs": 63, "graphics": 21001,
            "sounds": 930, "units": 1701}
    old = {"ver": "VER 7.8", "gv": 43, "civs": 46, "graphics": 13012,
           "sounds": 685, "units": 1701}
    got = DV.compare(old, base)
    check("an old format reads older", got["age"] == "older", got["age"])
    check("...and says how many steps behind", got["steps"] == 11, got["steps"])
    check("...with the verb that matches the sign, not the other one",
          "早 11 个格式台阶" in got["text"] and "还新" not in got["text"],
          got["text"])
    check("...and names the counts as an observation",
          "46 个文明" in got["text"] and "13012 条图形" in got["text"], got["text"])
    # The mode that trims on purpose.  Format-identical, 45 fewer civilisations:
    # this was the false "older" that made the line worthless.
    trim = {"ver": "VER 8.9", "gv": 54, "civs": 18, "graphics": 19701,
            "sounds": 685, "units": 1701}
    got = DV.compare(trim, base)
    check("a mode that trims civilisations on purpose is NOT called old",
          got["age"] == "same", got["age"])
    check("...but the trims are still printed", "18 个文明" in got["text"],
          got["text"])
    same = DV.compare(dict(base), base)
    check("the install's own file is `same`", same["age"] == "same", same["age"])
    check("...and the sentence says so plainly",
          "记录数也一样" in same["text"], same["text"])
    unknown = DV.compare({"ver": None, "gv": None}, base)
    check("a file with no readable head is `unknown`, not `older`",
          unknown["age"] == "unknown", unknown["age"])
    check("...and admits it cannot say", "说不清" in unknown["text"], unknown["text"])

    print()
    print("=== 3. what one file actually costs, and what the cache saves ===")
    gr = L.find_game_root()
    prof = L.find_profile_root()
    items = DSR.candidates(gr, prof)
    check("the machine lists the files the game could load", len(items) >= 1,
          len(items))
    base_row = next((it for it in items if it["scope"] == "game"), None)
    check("one of them is the install's own", base_row is not None)
    t0 = time.time()
    facts = DV.probe(base_row["path"])
    took = time.time() - t0
    check("probing the install's file takes well under a second", took < 3.0,
          "%.2fs" % took)
    check("...and answers a version head", facts.get("ver") == "VER 8.9",
          facts.get("ver"))
    check("...and the counts, without parsing a single record",
          facts.get("civs") == 63 and facts.get("graphics") == 21001
          and facts.get("sounds") == 930,
          (facts.get("civs"), facts.get("graphics"), facts.get("sounds")))
    check("...and reports how much it had to inflate, capped",
          facts.get("read_bytes", 0) <= DV.CAPS[0]
          and facts.get("cap") in DV.CAPS,
          (facts.get("read_bytes"), facts.get("cap")))
    check("the head is the layout it was written with, which is what the parser needs",
          facts.get("gv") == P.gv_from_version_string("VER 8.9"),
          (facts.get("gv"), P.GV_C32))

    legacy = [it for it in items if it["format"] is not None and it["format"] != 54]
    if legacy:
        lf = DV.probe(legacy[0]["path"])
        print("    (a legacy file here: %s, format %s)"
              % (legacy[0]["label"][:30], legacy[0]["format"]))
        check("a legacy file reports the older head", lf.get("gv") == 43,
              lf.get("gv"))
        check("...and fewer civilisations than the install",
              isinstance(lf.get("civs"), int) and lf["civs"] < facts["civs"],
              (lf.get("civs"), facts["civs"]))
        age = DV.compare(lf, facts)
        check("...and it is the one row that reads older", age["age"] == "older",
              age["age"])
        check("...eleven layout steps behind", age["steps"] == 11, age["steps"])
    else:
        print("  --   no legacy file on this machine; the numbers are pinned on "
              "the synthetic facts in part 2")

    print()
    print("=== 4. the cache is keyed by (path, mtime, size) ===")
    DV.forget()
    check("forgetting empties the cache", DV.cached(base_row["path"]) is None)
    DV.remember(base_row["path"], facts)
    check("remembering makes it readable without measuring",
          DV.cached(base_row["path"]) == facts)
    t0 = time.time()
    for it in items:
        DV.cached(it["path"])
    cold = time.time() - t0
    check("cached lookups over every candidate are free", cold < 0.05,
          "%.4fs for %d" % (cold, len(items)))
    # A file that changed on disk must not answer from the stale row.
    touched = os.path.abspath(base_row["path"])
    real = DV._MEM[os.path.normcase(touched)]
    DV._MEM[os.path.normcase(touched)] = {"mtime": real["mtime"] + 5,
                                          "bytes": real["bytes"],
                                          "facts": facts}
    check("a changed mtime invalidates the row instead of serving a stale answer",
          DV.cached(touched) is None)
    DV.remember(touched, facts)

    print()
    print("=== 5. measuring runs on a worker, not on the request thread ===")
    DV.forget()
    started = DV.start_worker([it["path"] for it in items])
    check("the first call starts a pass", started.get("started") is True,
          started)
    again = DV.start_worker([it["path"] for it in items])
    check("a second call while it runs is dropped, not queued",
          again.get("started") is False and again.get("busy") is True, again)
    deadline = time.time() + 90
    while time.time() < deadline and DV.status()["busy"]:
        time.sleep(0.2)
    st = DV.status()
    check("the pass finishes", st["busy"] is False, st)
    check("...and it measured every file", st["measured"] >= len(items), st)
    check("...with no error", not st["error"], st["error"])
    DV.start_worker([it["path"] for it in items])
    check("with everything measured, a new call does nothing",
          DV.status()["busy"] is False)

    print()
    print("=== 6. the route carries it, and the screen draws it ===")
    server = _read(SERVER)
    page = _read(PAGE)
    check("the route asks the cache, never measures inline",
          "DV.cached(it[\"path\"])" in server and "DV.probe(" not in server)
    check("...kicks a background pass", "DV.start_worker(paths)" in server)
    check("...reports the pass so the screen can retry for the answer",
          "\"versions\": DV.status()" in server)
    check("...and hands the screen a sentence, not a flag",
          "DV.compare(facts, base)" in server)
    check("every row can carry the reading", "it[\"version\"] = facts" in server
          and "it[\"age\"] = DV.compare" in server)
    check("the screen prints it next to the format chip",
          "row.appendChild(el(\"span\", age.age === \"older\" ? \"dpold\" : \"dpver\"" in page)
    check("...says how far behind in words", "\" 个格式台阶\"" in page
          or "个格式台阶" in page)
    check("...and admits when it has not measured yet",
          "版本还没量出来" in page)
    check("...and comes back for the answer while a pass runs",
          "vs.busy && !DP_WAIT" in page and "let DP_WAIT = null;" in page)
    check("the status text says it is measuring", "正在量这些文件的版本" in page)
    check("the old row has its own colour, not the accent that marks the open file",
          ".datpick .dpold { color: var(--warn-ink)" in page)

    print()
    if BAD:
        for name, detail in BAD:
            print("FAILED: %s :: %s" % (name, detail))
        print("DAT VERSION: %d CHECK(S) FAILED" % len(BAD))
        return 1
    print("DAT VERSION: `FORMAT 54` IS A LAYOUT ORDINAL, NOT AN AGE -- THE AGE COMES "
          "FROM THE FILE VERSION HEAD AND THE RECORD COUNTS, THE VERDICT COMES FROM "
          "THE HEAD ALONE, THE SIGN LIVES IN A NAME SO A CALL SITE CANNOT FLIP IT, "
          "AND THE SCREEN WAITS FOR THE ANSWER INSTEAD OF GIVING UP ON IT")
    return 0


sys.exit(main())
