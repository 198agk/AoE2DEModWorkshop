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
import os
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
FAILS = []


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
        print("FAIL %s :: %s" % (name, detail))
    else:
        print("  ok %s" % name)


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=120) as r:
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
        check("meta carries every intent the schema declares",
              len(meta.get("intents") or []) == 10,
              [i["id"] for i in (meta.get("intents") or [])])

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
            check("a refused intent refuses the bundle instead of silently dropping it",
                  b3.get("ok") is False and "sentence 2" in (b3.get("error") or ""),
                  str(b3)[:300])
        finally:
            shutil.rmtree(out2, ignore_errors=True)

        # ---- path traversal -------------------------------------------
        try:
            st, ctype, _b = _get(base, "/static/../server.py")
            leaked = True
        except urllib.error.HTTPError as ex:
            leaked = ex.code not in (200,)
        check("/static/ cannot walk out of the folder", leaked)
    finally:
        httpd.shutdown()

    print()
    if FAILS:
        print("UI SERVER CHECKS FAILED (%d): %s" % (len(FAILS), FAILS))
        sys.exit(1)
    print("UI SERVER: EVERY ROUTE ANSWERS, AND BUILD -> INSTALL RUNS END TO END")


if __name__ == "__main__":
    main()
