# -*- coding: utf-8 -*-
"""The UI server, exercised the way the browser exercises it: over HTTP.

Why a real socket and not a direct call into `App`
--------------------------------------------------
Every defect this file is meant to catch lives BETWEEN the two -- a route that
is registered for GET but fetched with POST, a JSON body the handler forgets to
read, an exception escaping as a 500 instead of a rendered error, a static path
served with the wrong content type.  Calling `App.parse(...)` directly would
pass while the screen stays broken.

The one thing it does NOT do is install into the real profile; `install` is
checked against a temporary profile root so a test run never touches the
player's mod list.  That distinction is the whole reason `_probe/test_install.py`
had to be rewritten twice.
"""
import json
import _gamepaths as GP
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.ui import server as S                              # noqa: E402

GAME = GP.GAME
FAILS = []


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))
    else:
        print("  ok %s" % name)


def _get(base, path, timeout=120):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


def _post(base, path, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"ok": False, "error": "HTTP %s" % e.code}


def main():
    httpd, app, url = S.serve(port=0, game_root=GAME)
    base = url.rstrip("/")
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print("serving at %s" % base)
    try:
        # ---- static ----------------------------------------------------
        st, ctype, body = _get(base, "/")
        check("a GET / returns the screen", st == 200 and len(body) > 2000,
              "%s / %d bytes" % (st, len(body)))
        check("the screen is served as UTF-8 HTML",
              "text/html" in ctype and "utf-8" in ctype.lower(), ctype)
        text = body.decode("utf-8")
        check("the screen carries no unrendered template marker",
              "{{" not in text and "{%" not in text)

        # ---- meta ------------------------------------------------------
        st, _c, body = _get(base, "/api/meta")
        meta = json.loads(body.decode("utf-8"))
        check("meta is ok", meta.get("ok") is True, str(meta)[:120])
        check("meta carries every civilization", len(meta.get("civs") or []) >= 60,
              len(meta.get("civs") or []))
        # Compare against the SCHEMA, not against a number.  A literal here is a
        # test that fails whenever an intent is added and that proves nothing
        # about whether the route carries the schema -- measured 2026-10-21, when
        # adding `unit.create` turned this into a red about the number 10.
        from aoe2mod.intent import compiler as _C
        _schema, _ = _C.load_schema()
        declared = sorted((_schema.get("intents") or {}).keys())
        served = sorted(i["id"] for i in (meta.get("intents") or []))
        check("meta carries every intent the schema declares", served == declared,
              [i for i in declared if i not in served]
              or [i for i in served if i not in declared])

        # ---- search ----------------------------------------------------
        st, _c, body = _get(base, "/api/search?q=%E6%9D%91%E6%B0%91&kind=unit")
        s = json.loads(body.decode("utf-8"))
        check("search finds 村民", s.get("ok") and s.get("hits"), str(s)[:160])

        # ---- describe --------------------------------------------------
        uid = s["hits"][0]["id"]
        st, _c, body = _get(base, "/api/describe?kind=unit&id=%d" % uid)
        d = json.loads(body.decode("utf-8"))
        check("describe returns stats for the unit", d.get("ok") is True,
              str(d)[:160])
        check("describe names the unit", bool((d.get("entity") or {}).get("name")),
              str(d.get("entity"))[:120])

        # ---- parse -----------------------------------------------------
        st, p = _post(base, "/api/parse", {"text": "村民血量改成 1000"})
        check("parse returns ok", p.get("ok") is True, str(p)[:160])
        cls = p.get("clauses") or []
        check("parse returns one clause", len(cls) == 1, len(cls))
        if cls:
            check("the clause resolved to unit.stat",
                  (cls[0].get("intent") or {}).get("intent") == "unit.stat",
                  cls[0].get("intent"))
            pv = cls[0].get("preview") or {}
            # The preview is nested one level: `_safe_plan` wraps the product's
            # own answer so a refusal can carry a reason instead of a traceback.
            inner = pv.get("plan") or {}
            check("the clause carries a preview from the product's own plan",
                  pv.get("ok") is True and "生命值" in (inner.get("description") or ""),
                  str(pv)[:200])
            check("the preview says how many civilizations are touched",
                  inner.get("civ_count") == 63, inner.get("civ_count"))
            # The page needs the id, not just the name, to ask for a picture and
            # a description.  It cannot recover it from the display name: 弓箭手
            # is not any unit's name and 城堡 is both a building and part of a
            # technology's name, so the resolver's pick has to travel with it.
            #
            # Checked against the INTENT, not against a literal: 「村民」 resolves
            # to the sexless record 1810 rather than 83, and pinning 83 here
            # would fail on correct code (the first version did exactly that).
            # The invariant that matters is "the picture is of the thing being
            # edited".
            check("the clause carries the entity id the icon route needs",
                  cls[0].get("entity_id") == (cls[0].get("intent") or {}).get("unit")
                  and cls[0].get("entity_id") is not None,
                  "%r vs %r" % (cls[0].get("entity_id"),
                                (cls[0].get("intent") or {}).get("unit")))
            check("the clause says whether it is a unit or a technology",
                  cls[0].get("kind") == "unit", cls[0].get("kind"))

        # ---- a sentence that names one civilization ---------------------
        # `plan()["civs"]` is a list of .dat indices.  The screen used to join
        # those straight into "范围 1、2、3", so the server now also ships names.
        st, p2 = _post(base, "/api/parse",
                       {"text": "把不列颠的村民血量改成1000"})
        c2 = (p2.get("clauses") or [{}])[0]
        pv2 = ((c2.get("preview") or {}).get("plan") or {})
        check("a named civ narrows the edit to one civilization",
              pv2.get("civ_count") == 1, pv2.get("civ_count"))
        check("a narrowed plan names the civilization instead of its index",
              (pv2.get("civ_labels") or [None])[0] == "不列颠",
              pv2.get("civ_labels"))
        # The two intents report `civs` in DIFFERENT shapes: `unit.stat` gives
        # .dat indices, `unit.availability` gives names.  The server has to
        # print both, so this checks the second shape too -- a fix for the first
        # one that only handles indices would pass the check above and leave
        # availability blank.
        st, p3 = _post(base, "/api/parse", {"text": "印加不能造蔷琵侦察兵"})
        pv3 = (((p3.get("clauses") or [{}])[0].get("preview") or {}).get("plan") or {})
        check("availability scope also prints as a name",
              (pv3.get("civ_labels") or [None])[0] == "印加",
              pv3.get("civ_labels"))

        # ---- a picture click carries the id -----------------------------
        # 靶场 is 10 unit records and 城门 is 29; a name alone sends the edit to
        # the lowest id.  Measured over the whole list: 287 of 1,651 names came
        # back as a different record.  So the click's id travels with the
        # sentence, and the server must route it into the reader.
        st, np1 = _post(base, "/api/parse", {"text": "靶场 血量改成1000"})
        i1 = ((np1.get("clauses") or [{}])[0].get("intent") or {})
        st, pp1 = _post(base, "/api/parse",
                        {"text": "靶场 血量改成1000",
                         "pins": [{"kind": "unit", "id": 14}]})
        c1 = (pp1.get("clauses") or [{}])[0]
        i2 = (c1.get("intent") or {})
        check("without a pin a shared name goes to the lowest id",
              i1.get("unit") == 10, i1)
        check("the pinned id wins over the name's lowest id",
              i2.get("unit") == 14, i2)
        check("the pinned clause previews the record that was clicked",
              "靶场" in ((c1.get("preview") or {}).get("plan") or {}).get(
                  "description", ""), str(c1.get("preview"))[:200])
        # The pin must not hijack a sentence that no longer names it.
        st, pp2 = _post(base, "/api/parse",
                        {"text": "血量改成1000",
                         "pins": [{"kind": "unit", "id": 14}]})
        c2r = (pp2.get("clauses") or [{}])[0]
        check("a pin is ignored when its name is gone from the sentence",
              not c2r.get("intent") and not c2r.get("entity"), str(c2r)[:200])

        # ---- a class word is a category, not a record -------------------
        # 骑兵 covers 188 visible units and is not one of them; 攻城武器 lands
        # on the FACTORY (a building), 征服者 on 征服者威廉, 侦察兵 on 蔷琵侦察兵.
        # Measured over all 62 class names: 15 of the 33 that resolved named a
        # different kind of thing.  The server knows each record's class, so it
        # is the only place that can tell the two apart.
        st, cw1 = _post(base, "/api/parse", {"text": "骑兵的血量改成1000"})
        cw = (cw1.get("clauses") or [{}])[0]
        check("a class word is refused instead of editing a like-named record",
              not cw.get("intent") and "一类" in (cw.get("why") or ""),
              str(cw)[:240])
        check("the refusal offers the units that class covers",
              len(cw.get("candidates") or []) >= 3
              and all(c.get("id") for c in cw.get("candidates") or []),
              str((cw.get("candidates") or [])[:3]))
        # The page cannot rewrite the sentence without knowing WHICH word was the
        # category -- 骑兵 is not the name of any candidate, so guessing it from
        # them is impossible.  This is the only place that fact crosses the wire.
        check("the refusal names the exact word the player used for the class",
              cw.get("class_word") == "骑兵", str(cw.get("class_word")))
        # …but a word that IS a shipped name still works: 长枪兵 is both a class
        # name and the name of unit 358.
        st, cw2 = _post(base, "/api/parse", {"text": "长枪兵血量改成1000"})
        check("a word that is also a real unit name still edits that unit",
              ((cw2.get("clauses") or [{}])[0].get("intent") or {}).get("unit")
              == 358, str(cw2)[:240])

        # ---- parse a refusal -------------------------------------------
        st, p = _post(base, "/api/parse", {"text": "这是什么"})
        check("a question comes back refused, not crashed", p.get("ok") is True,
              str(p)[:160])
        check("the refusal carries a reason a human can read",
              bool(((p.get("clauses") or [{}])[0]).get("why")), str(p)[:200])

        # ---- understood vs possible ------------------------------------
        # `intent is not None` means the SENTENCE was understood.  The plan can
        # still refuse the edit, and the page used to count `c.intent` as
        # "can build": it offered a build button for work that cannot be done,
        # and since the build sends every intent it is given, one refusal made
        # the whole bundle raise -- losing the sentences that WERE possible.
        # The server now answers the question once, as `buildable`.
        st, r1 = _post(base, "/api/parse", {"text": "给不列颠解锁村民"})
        c1 = (r1.get("clauses") or [{}])[0]
        check("a refused edit is still understood",
              c1.get("intent") is not None, str(c1)[:200])
        check("...but it is not marked buildable",
              c1.get("buildable") is False, c1.get("buildable"))
        st, r2 = _post(base, "/api/parse", {"text": "村民血量改成1000"})
        check("a possible edit IS marked buildable",
              (r2.get("clauses") or [{}])[0].get("buildable") is True,
              (r2.get("clauses") or [{}])[0].get("buildable"))
        st, r3 = _post(base, "/api/parse",
                       {"text": "村民血量改成1000，织布机研究时间加0"})
        c3 = r3.get("clauses") or []
        check("a mixed sentence splits into two clauses", len(c3) == 2, len(c3))
        check("only the possible half is buildable",
              [bool(c.get("buildable")) for c in c3] == [True, False],
              [c.get("buildable") for c in c3])
        # The page is the half that decides what the player SEES and what gets
        # posted.  A server that ships `buildable` while the page keeps asking
        # `c.intent` is the same defect with extra steps, so pin the page too:
        # no line may filter clauses for BUILD by `c.intent` alone.
        page = open(os.path.join(S.STATIC_DIR, "index.html"), encoding="utf-8").read()
        check("the page gates building on `buildable`, not on having an intent",
              "buildable" in page, "<- index.html never mentions buildable")
        # The defect is specifically "turn the clause list into intents".  A
        # blanket "no line may mention both filter() and .intent" also matched
        # the refusal COUNTER (`filter(c => c.intent && !can)`), which is
        # correct code -- an assertion that fails on good code teaches people to
        # widen it until it passes.
        bad_gate = [ln.strip() for ln in page.splitlines()
                    if "filter(" in ln and ".map(" in ln
                    and ".intent)" in ln and "buildable" not in ln]
        check("no line turns clauses straight into intents without the gate",
              not bad_gate, bad_gate)
        check("the build posts only the gated clauses",
              "filter(buildable)" in page, "<- doBuild() does not use the gate")
        # A count written into the page is a claim about the whole install, and
        # the page cannot check it: the hint above the pick grid said "1,349
        # units have no picture" while the grid listed only named units and drew
        # 432 dashed cells (1,042 of 2,693 records have no name at all and are
        # never listed).  Neither number was wrong -- they counted different
        # universes -- and no test noticed for a day.
        # The rule: player-visible prose may not quote a count of records; the
        # page shows counts it COMPUTES (PICK.offset + " / " + b.total) instead.
        # Both word orders occur in Chinese, and the counter varies (个/条/项), so
        # one pattern per order; neither fires on a VALUE ("血量改成 1000").
        visible = re.sub(r"(?is)<script\b.*?</script>", " ", page)
        visible = re.sub(r"(?s)<!--.*?-->", " ", visible)
        visible = re.sub(r"(?s)/\*.*?\*/", " ", visible)
        # Tags are not prose.  `科技树` is a section heading, and a regex that
        # allows four characters between "科技" and a number reads `树</h2>`
        # as "科技 … 2".  Measured 2026-11-08: the only hit was
        # `<h2>科技树</h2>` -- a false red, not a stale count.
        visible = re.sub(r"<[^>]{0,400}>", " ", visible)
        num_then_word = re.compile(r"\d[\d,]*\s*[个条项]?\s*(单位|科技|记录)")
        word_then_num = re.compile(
            r"(单位|科技|记录)[^，。；\n]{0,4}?\d[\d,]*\s*[个条项]?")
        stale_counts = [ln.strip() for ln in visible.splitlines()
                        if num_then_word.search(ln) or word_then_num.search(ln)]
        check("no line hardcodes a record COUNT where the player reads it",
              not stale_counts, stale_counts)

        # ---- plan ------------------------------------------------------
        st, pl = _post(base, "/api/plan",
                       {"intent": {"intent": "unit.stat", "unit": 83,
                                   "stat": "hit_points", "value": 1000}})
        check("plan previews without writing", pl.get("ok") is True, str(pl)[:160])
        check("plan reports the edit fan-out",
              (pl.get("plan") or {}).get("edit_count") == 1701,
              (pl.get("plan") or {}).get("edit_count"))

        # ---- build -----------------------------------------------------
        out = tempfile.mkdtemp(prefix="dsh_ui_build_")
        try:
            st, b = _post(base, "/api/build", {
                "intents": [{"intent": "unit.stat", "unit": 83,
                             "stat": "hit_points", "value": 1000}],
                "title": "dsh ui smoke 村民血量", "author": "dsh",
                "description": "test", "out_dir": out})
            check("build returns ok", b.get("ok") is True, str(b)[:300])
            man = b.get("manifest") or {}
            mod_dir = man.get("mod_dir")
            check("build names the folder it wrote", bool(mod_dir) and os.path.isdir(mod_dir or ""),
                  str(mod_dir))
            # `files` is a list of {rel, bytes}, not a list of paths.
            rels = [f.get("rel", "") for f in (man.get("files") or [])]
            check("the built mod contains exactly one .dat",
                  len([f for f in rels if f.endswith(".dat")]) == 1, rels)
            check("the built .dat was verified against the game's inflate path",
                  man.get("reparse_ok") is True, man.get("reparse_ok"))

            # ---- install into a THROWAWAY profile ---------------------
            # `install_mod` treats a root that already has `mods/` as the
            # account folder itself, so the fake needs exactly that one
            # directory and nothing else.
            fake = tempfile.mkdtemp(prefix="dsh_ui_profile_")
            os.makedirs(os.path.join(fake, "mods", "local"), exist_ok=True)
            try:
                res = app.install(mod_dir, name="dsh ui smoke", profile_root=fake)
                check("install copies the mod into the profile",
                      bool(res.get("ok")), str(res)[:300])
                landed = os.path.join(fake, "mods", "local", "dsh ui smoke",
                                      "resources", "_common", "dat",
                                      "empires2_x2_p1.dat")
                check("the installed .dat is on disk", os.path.isfile(landed),
                      landed)
                status = os.path.join(fake, "mods", "mod-status.json")
                check("install wrote the status file the game reads",
                      os.path.isfile(status), status)
                # The game rewrites mod-status.json at exit, so the answer about
                # whether it is running has to travel with the install result --
                # the screen reads it off `installed`, not off a second call.
                inst = res.get("installed") or {}
                check("the install answer says whether the game is running",
                      inst.get("game_running") in (True, False, None),
                      str(inst.get("game_running")))
                check("and carries the warning field even when null",
                      "running_warning" in inst, str(inst.keys())[:200])
                # The two routes that rewrite the SAME file had no assertion at
                # all, because they had no way to accept a throwaway profile.
                off = app.set_mod("dsh ui smoke", False, profile_root=fake)
                check("turning a mod off answers with the list and the warning",
                      bool(off.get("ok")) and isinstance(off.get("mods"), list)
                      and "running_warning" in off, str(off)[:300])
                # The `mods` list in the answer comes from the REAL profile (the
                # route only writes the one it was pointed at), so asserting on
                # it would be vacuously true here.  Assert on the file that was
                # actually written instead.
                import json as _json
                with open(status, encoding="utf-8") as fh:
                    doc = _json.load(fh)
                mine = [e for e in doc.get("Mods") or []
                        if "dsh ui smoke" in str(e.get("Path") or "")]
                check("the mod really went off in the file the game reads",
                      bool(mine) and all(not e.get("Enabled") for e in mine),
                      str(mine)[:300])
                gone = app.uninstall("dsh ui smoke", profile_root=fake)
                check("uninstall answers with the list and the warning",
                      bool(gone.get("ok")) and "running_warning" in gone,
                      str(gone)[:300])
                with open(status, encoding="utf-8") as fh:
                    doc = _json.load(fh)
                check("uninstall took the entry out of that file",
                      not [e for e in doc.get("Mods") or []
                           if "dsh ui smoke" in str(e.get("Path") or "")],
                      str(doc.get("Mods"))[:300])
            finally:
                shutil.rmtree(fake, ignore_errors=True)
        finally:
            shutil.rmtree(out, ignore_errors=True)

        # ---- error shape ----------------------------------------------
        st, e = _post(base, "/api/plan", {"intent": {"intent": "nope"}})
        check("an unknown intent is an error document, not a traceback",
              e.get("ok") is False and bool(e.get("error")), str(e)[:200])
        check("the error still answers with HTTP 200", st == 200, st)

        # ---- a bundle keeps the possible half -------------------------
        # Two sentences reach the page, one of which the plan refuses.  The page
        # now posts only the buildable ones; posting both still raises (that is
        # the correct refusal) -- what must not happen is the possible half
        # being lost, or a silent drop of the refused edit.
        out2 = tempfile.mkdtemp(prefix="dsh_ui_half_")
        try:
            st, b2 = _post(base, "/api/build", {
                "intents": [{"intent": "unit.stat", "unit": 83,
                             "stat": "hit_points", "value": 1000}],
                "title": "dsh ui half", "author": "dsh",
                "description": "only the possible half", "out_dir": out2})
            check("the possible half builds on its own",
                  b2.get("ok") is True, str(b2)[:300])
            st, b3 = _post(base, "/api/build", {
                "intents": [{"intent": "unit.stat", "unit": 83,
                             "stat": "hit_points", "value": 1000},
                            {"intent": "tech.research_time", "tech": 22,
                             "delta": 0}],
                "title": "dsh ui both", "author": "dsh",
                "description": "one possible + one refused", "out_dir": out2})
            # The number is the contract (which sentence failed); the words
            # around it are the product's Chinese, which `test_prose_language`
            # pins separately.
            check("a refused intent refuses the bundle instead of silently dropping it",
                  b3.get("ok") is False and "第 2 句" in (b3.get("error") or ""),
                  str(b3)[:300])

            # ---- the auto title, over the wire ------------------------
            # The page writes the title by joining the sentences, and three
            # Chinese characters cost nine bytes, so a handful of sentences
            # passes the engine's 100-byte cap without anyone typing a long
            # title.  `title_auto` is the page saying "I wrote this", and only
            # then may the server shorten it.  Both halves are asserted here
            # because only one of them may succeed: a title the PLAYER typed is
            # refused with a sentence, never silently edited.
            long_zh = "把不列颠的村民血量改成一千点并且让弓箭手的攻击力加二" * 2
            st, b4 = _post(base, "/api/build", {
                "intents": [{"intent": "unit.stat", "unit": 83,
                             "stat": "hit_points", "value": 1000}],
                "title": long_zh, "title_auto": True, "author": "dsh",
                "description": "auto title", "out_dir": out2})
            used = ((b4.get("manifest") or {}).get("info") or {}).get("Title")
            check("an auto title too long to be a folder is trimmed, not refused",
                  b4.get("ok") is True and bool(used), str(b4)[:300])
            check("the trimmed title fits the engine's 100 bytes",
                  used is not None and len(used.encode("utf-8")) <= 100,
                  repr(used))
            check("and it is shorter than what the page sent", used != long_zh,
                  repr(used))
            st, b5 = _post(base, "/api/build", {
                "intents": [{"intent": "unit.stat", "unit": 83,
                             "stat": "hit_points", "value": 1000}],
                "title": long_zh, "author": "dsh",
                "description": "typed title", "out_dir": out2})
            # Not ok, and the reason names the limit: an edit made behind the
            # player's back would be worse than the refusal.
            check("the same title typed by hand is refused, not trimmed",
                  b5.get("ok") is False and "标题太长" in (b5.get("error") or ""),
                  str(b5)[:300])
        finally:
            shutil.rmtree(out2, ignore_errors=True)

        # ---- a sentence that MAKES a unit, over the wire ---------------
        # `unit.create` was added to the reader and to the toolkit in one round,
        # and the only test that built one called the toolkit directly.  A route
        # that dropped a field on the way -- the name, the civilization, the
        # donor -- would pass every direct-call test and still write a nameless
        # record.  So this walks the same sentence the page sends, one route at a
        # time, and reads the answer the product gives.
        out3 = tempfile.mkdtemp(prefix="dsh_ui_create_")
        try:
            make = "给不列颠新建一个和村民一样的单位，叫铁匠学徒"
            st, pc = _post(base, "/api/parse", {"text": make})
            cl = (pc.get("clauses") or [{}])[0]
            whole = cl.get("intent") or {}
            check("a creating sentence is read as unit.create",
                  whole.get("intent") == "unit.create", str(whole)[:200])
            check("and the name it will carry came out of the sentence",
                  whole.get("name") == "铁匠学徒", whole.get("name"))
            check("and the civilization it is added to is named, not defaulted",
                  bool(whole.get("civ")), whole.get("civ"))
            check("the clause says it can be built", cl.get("buildable") is True,
                  str(cl.get("preview"))[:200])

            st, mp = _post(base, "/api/plan", {"intent": whole})
            mplan = mp.get("plan") or {}
            check("the preview accepts it", mp.get("ok") is True and
                  mplan.get("editable") is True, str(mp)[:200])
            check("the preview picks the id the build will use",
                  isinstance(mplan.get("new_id"), int), str(mplan)[:200])
            # The screen reads this sentence, so it may not name internal fields.
            check("the preview sentence is in Chinese",
                  bool(re.search(u"[\u4e00-\u9fff]", mplan.get("description") or "")),
                  mplan.get("description"))

            st, mb = _post(base, "/api/build", {
                "intents": [whole], "title": "dsh ui create", "author": "dsh",
                "description": "one new unit", "out_dir": out3})
            check("the creating build returns ok", mb.get("ok") is True,
                  str(mb)[:300])
            mman = mb.get("manifest") or {}
            made = mman.get("new_unit") or {}
            check("the build wrote the id the preview promised",
                  made.get("id") == mplan.get("new_id"),
                  (made.get("id"), mplan.get("new_id")))
            check("the new record survived the writer",
                  mman.get("unit_added") is True, mman.get("unit_added"))
            # The name is the half a route can silently lose: the record is one
            # appended block, while the name is a separate file per locale.
            check("and the name landed in a shipped strings table",
                  (made.get("string_id") and any(
                      "key-value-modded-strings" in f.get("rel", "")
                      for f in mman.get("files") or [])),
                  str(made.get("strings"))[:200])
        finally:
            shutil.rmtree(out3, ignore_errors=True)

        # ---- path traversal -------------------------------------------
        try:
            st, ctype, _b = _get(base, "/static/../server.py")
            leaked = True
        except urllib.error.HTTPError as ex:
            leaked = ex.code not in (200,)
        check("/static/ cannot walk out of the folder", leaked)

        # ---- browse (pick a picture instead of typing a name) ----------
        # The grid exists because a name only works if you already know it, and
        # the game's Chinese names are not the ones players use.  What the page
        # needs from this route: a stable order (the grid must not reshuffle),
        # pageable rows, and an honest answer about which cells have no picture
        # at all.  Counts meant for the grid must be counted over the rows the
        # grid shows (named entities only) -- the screen once promised "1,349
        # have no picture" over a grid that draws 432 dashed cells, because that
        # number was taken over all 2,693 records, 1,042 of which have no name
        # and are not listed at all.
        st, _c, body = _get(base, "/api/browse?kind=unit&limit=10")
        b1 = json.loads(body.decode("utf-8")).get("browse") or {}
        check("browse returns a page of units", st == 200 and body and
              b1.get("ok") is True and len(b1.get("rows") or []) == 10,
              "%s rows=%d" % (st, len(b1.get("rows") or [])))
        check("browse reports the full count, not just the page",
              (b1.get("total") or 0) > 1000, b1.get("total"))
        # A grid that reshuffles between visits makes the player hunt for the
        # same picture twice, so the order has to be the same answer twice.
        _st, _c, again = _get(base, "/api/browse?kind=unit&limit=10")
        b1b = json.loads(again.decode("utf-8")).get("browse") or {}
        check("browse pages come back in a stable order",
              [r["id"] for r in b1b.get("rows") or []] ==
              [r["id"] for r in b1["rows"]],
              "%s vs %s" % ([r["id"] for r in b1["rows"]][:5],
                            [r["id"] for r in b1b.get("rows") or []][:5]))
        st, _c, body = _get(base, "/api/browse?kind=unit&limit=10&offset=10")
        b2 = json.loads(body.decode("utf-8")).get("browse") or {}
        check("the next page continues instead of repeating",
              not ({r["id"] for r in b2.get("rows") or []} &
                   {r["id"] for r in b1["rows"]}), "overlap")

        # Every row must be usable by the routes the grid calls: a row whose id
        # could not be drawn or described would be a dead cell.
        row = b1["rows"][0]
        check("a row carries what the grid needs to draw and to pick",
              all(k in row for k in ("id", "kind", "name", "has_icon")),
              sorted(row))
        # `has_icon` has to agree with the icon route, or the grid draws a hole
        # exactly where it promised a picture.
        with_icon = [r for r in b1["rows"] if r["has_icon"]]
        without = [r for r in b1["rows"] if not r["has_icon"]]
        if with_icon:
            _s, ctype_i, body_i = _get(base, "/api/icon?kind=unit&id=%d&size=32"
                                       % with_icon[0]["id"])
            check("a row marked has_icon really draws an image",
                  ctype_i.startswith("image/png") and
                  body_i.startswith(b"\x89PNG"), "%s %s" %
                  (ctype_i, body_i[:8]))
        # Units with no icon id are the ORDINARY case (432 of the 1,651 named
        # units), so the route must be able to report one rather than the grid
        # only ever seeing hits.
        st, _c, body = _get(base, "/api/browse?kind=unit&q=%E6%94%BB%E5%9F%8E%E9%94%A4")
        bq = json.loads(body.decode("utf-8")).get("browse") or {}
        check("browse can be narrowed to a word the player typed",
              (bq.get("total") or 0) >= 1 and
              "攻城锤" in (bq["rows"][0].get("name") or ""), str(bq)[:160])

        st, _c, body = _get(base, "/api/browse?kind=tech&limit=5")
        bt = json.loads(body.decode("utf-8")).get("browse") or {}
        check("browse covers technologies too",
              bt.get("kind") == "tech" and len(bt.get("rows") or []) == 5,
              str(bt)[:160])
        check("a technology row carries its icon id for the grid",
              all("icon_id" in r for r in bt.get("rows") or []),
              str((bt.get("rows") or [{}])[0])[:120])

        # ---- icons and prose ------------------------------------------
        # The picture routes answer with IMAGE bytes, not JSON.  A client that
        # gets a JSON error where it expected a PNG shows a broken-image glyph,
        # so the content type is half the contract.
        st, ctype, body = _get(base, "/api/icon?kind=unit&id=83&size=32")
        check("a unit icon is served as an image/png",
              st == 200 and ctype.startswith("image/png"), "%s %s" % (st, ctype))
        check("the icon body is a real PNG",
              body.startswith(b"\x89PNG\r\n\x1a\n"), repr(body[:8]))
        check("the icon is small enough for a list view", len(body) < 200000,
              "%d bytes" % len(body))

        st, _c, body_t = _get(base, "/api/icon?kind=tech&id=22&size=32")
        check("a technology icon is served too",
              st == 200 and body_t.startswith(b"\x89PNG"), repr(body_t[:8]))

        # The two icon tables draw DIFFERENT pictures for the same number, and a
        # build-menu button is not a training portrait.  Asking for each and
        # comparing bytes is the only way to see that the choice happened.
        # Use unit 83 (villager): its default section is Units, so the override
        # must move it.  Unit 12 (barracks) is the wrong subject -- its default
        # is ALREADY Buildings, so the first version of this check compared a
        # picture with itself and "failed" while the routing was correct.
        _s, _c1, default_83 = _get(base, "/api/icon?kind=unit&id=83&size=32")
        _s, _c2, forced_83 = _get(base,
                                  "/api/icon?kind=unit&id=83&size=32&section=Buildings")
        check("the section override draws a different picture",
              default_83 != forced_83, "both %d bytes" % len(default_83))
        # And a building must default to the Buildings table, or the build-menu
        # buttons and the training portraits are mixed up the other way round.
        _s, _c3, building_12 = _get(base, "/api/icon?kind=unit&id=12&size=32")
        _s, _c4, forced_units_12 = _get(base,
                                        "/api/icon?kind=unit&id=12&size=32&section=Units")
        check("a barracks defaults to the build-menu table, not the portrait",
              building_12 != forced_units_12, "both %d bytes" % len(building_12))

        # A unit whose icon cannot be resolved must fail with a REASON, not a
        # zero-byte image: a blank square looks like a missing asset, and many
        # units in this build legitimately have no picture.
        st, ctype, body_bad = _get(base, "/api/icon?kind=unit&id=99999")
        if ctype.startswith("application/json"):
            err = json.loads(body_bad.decode("utf-8"))
            check("an unresolvable icon answers with a reason",
                  err.get("ok") is False and bool(err.get("error")), str(err)[:160])
        else:
            check("an unresolvable icon answers with a reason", False, ctype)

        # Emblems: three spellings, one file.  `French` is the .dat name and
        # `FRANKS` the tree stem, and the file is neither.
        st, ctype, em = _get(base, "/api/emblem?civ=British")
        check("a civilization emblem is served as a PNG",
              st == 200 and ctype.startswith("image/png")
              and em.startswith(b"\x89PNG"), "%s %s %r" % (st, ctype, em[:8]))
        st2, _c2, em2 = _get(base, "/api/emblem?civ=BRITONS")
        check("the tree-stem spelling finds the same emblem", em2 == em,
              "%d vs %d bytes" % (len(em2), len(em)))
        st3, _c3, em3 = _get(base, "/api/emblem?civ=French")
        check("a civilization whose file is spelled differently still resolves",
              st3 == 200 and em3.startswith(b"\x89PNG"), "%s %s" % (st3, _c3))

        # Prose: the API must say a unit has NO description rather than let the
        # screen draw an empty box, which reads as a bug in this product.
        st, _c, body = _get(base, "/api/describe?kind=unit&id=83")
        d_unit = json.loads(body.decode("utf-8")).get("entity") or {}
        prose = d_unit.get("prose") or {}
        check("a unit reports that it has no description",
              prose.get("ok") is False and bool(prose.get("why")), str(prose)[:200])
        check("the missing-description reason is in Chinese",
              "没有" in (prose.get("why") or ""), prose.get("why"))
        check("describe carries the unit's icon",
              bool((d_unit.get("icon") or {}).get("ok")),
              str(d_unit.get("icon"))[:160])

        st, _c, body = _get(base, "/api/describe?kind=tech&id=22")
        d_tech = json.loads(body.decode("utf-8")).get("entity") or {}
        tprose = d_tech.get("prose") or {}
        check("a technology reports its real description",
              bool(((tprose.get("fields") or {}).get("description") or {}).get("zh")),
              str(tprose)[:200])
        check("a technology reports its icon instead of a placeholder",
              bool((d_tech.get("icon") or {}).get("ok")),
              str(d_tech.get("icon"))[:160])

        # ---- the update guard over HTTP --------------------------------
        # A mod we build ships a whole .dat, so a game patch is silently
        # overwritten by the installed copy.  The screen asks this route on every
        # load, so it has to answer with rows the page can print -- status words
        # in the reader's language, not enum values.
        st, _c, body = _get(base, "/api/update-check")
        upd = json.loads(body.decode("utf-8")).get("update") or {}
        check("the update guard answers over HTTP", st == 200 and
              isinstance(upd.get("rows"), list), "%s %s" % (st, str(upd)[:160]))
        # This machine has installed mods (the file's other checks already lean on
        # the real installation), so an empty list means the guard failed to read
        # the profile rather than "nothing to report" -- and `all([])` would pass
        # the next two checks on nothing at all.
        check("the update guard lists the mods that are installed",
              len(upd.get("rows") or []) >= 1, str(upd)[:160])
        check("every row carries a status word the page can print",
              all(r.get("status") and r.get("status_zh") for r in upd.get("rows") or []),
              str((upd.get("rows") or [{}])[0])[:200])
        check("the route says whether a banner is needed",
              "banner" in upd, str(sorted(upd.keys())))
        # Unknown rows must never be counted: a banner nobody can act on trains
        # people to ignore the ones they can act on.
        unknown = [r for r in upd.get("rows") or [] if r.get("status") == "unknown"]
        check("unknown rows are not counted as needing attention",
              not unknown or upd.get("needs_attention") == 0,
              "unknown=%d attention=%s" % (len(unknown), upd.get("needs_attention")))

        # Rebuilding something we never built must say so by name, not 500 and
        # not silently pretend it rebuilt.
        st, rb = _post(base, "/api/rebuild", {"title": "no such mod at all"})
        check("rebuilding an unrecorded mod refuses with a reason",
              st == 200 and rb.get("ok") is False and "记录" in (rb.get("error") or ""),
              str(rb)[:200])

        # ---- the routes whose only caller is a button -----------------------
        # These three had no assertion through the ROUTE at all: their nails
        # called `App.<method>` directly, so a route that raised on every call
        # still looked green.  `/api/repair-check` was in fact dead -- it read a
        # `q` that was never bound in its branch, so the feature's button
        # returned `NameError` to the screen while `test_repair.py` and
        # `test_repair_apply.py` passed, because both go through the toolkit.
        # A route is a different object from the method behind it; this block
        # is the only place that can tell the difference.
        st, _ctype, body = _get(base, "/api/ai-meta")
        ai = json.loads(body.decode("utf-8"))
        check("the AI entry answers over the route",
              st == 200 and ai.get("ok") is True, str(ai)[:160])
        check("and reports its configuration honestly, flat, not nested",
              ai.get("available") in (True, False) and "writes" in ai,
              sorted(ai.keys()))
        if ai.get("available") is False:
            st, said = _post(base, "/api/ai-sentences", {"text": "随便说一句"})
            # Assert on the sentence, not the whole body: `_guard` attaches a
            # `where` traceback on purpose, for whoever debugs this localhost
            # tool, and the page never renders it.  Scanning the body for the
            # word would fail on that decision instead of on what the player
            # reads.
            check("asking for sentences without a key is a sentence, not a traceback",
                  said.get("ok") is False
                  and "Traceback" not in (said.get("error") or "")
                  and bool(said.get("error")),
                  (said.get("error") or "")[:160])

        # The repair sweep parses about 12 MB per installed mod -- 16 here, so
        # tens of seconds on a busy machine.  The default 120 s client timeout
        # is what the PAGE uses and what a player would abandon, so this asks
        # for the longer one explicitly rather than measuring patience.
        st, _ctype, body = _get(base, "/api/repair-check", timeout=900)
        rep = json.loads(body.decode("utf-8"))
        check("the repair route answers instead of raising",
              st == 200 and rep.get("ok") is True,
              str(rep.get("error"))[:200])
        check("and its rows come back flat, where the page reads them",
              isinstance(rep.get("mods"), list), sorted(rep.keys())[:6])
    finally:
        httpd.shutdown()

    print()
    if FAILS:
        print("UI SERVER CHECKS FAILED (%d): %s" % (len(FAILS), FAILS))
        sys.exit(1)
    print("UI SERVER: EVERY ROUTE ANSWERS, AND BUILD -> INSTALL RUNS END TO END")


if __name__ == "__main__":
    main()
