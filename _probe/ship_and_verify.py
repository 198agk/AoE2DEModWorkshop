# -*- coding: utf-8 -*-
"""Ship the measured tables, and prove every route answers from the shipped copy.

The defect this fixes
--------------------
The bundle carried `app/aoe2mod/ui/static` and `app/aoe2mod/schema`, and nothing
else. So in the SHIPPED program:

  * `/api/parse` answered "名字表没有随程序发布，认不出这句话说的是哪个单位";
  * `/api/build` answered "读不到 _golden/stat_offsets.json";
  * `/api/ai-meta` produced an empty grammar.

All three are correct refusals of a missing file, and all three mean the product
does not work. They were invisible because every route had been verified against
the DEVELOPMENT binary, whose cwd happened to walk up into the repo.

What ships, and why each is data rather than code
-------------------------------------------------
  stat_offsets.json   19 MB, regenerable in ~40 s by make_stat_offsets.py, and
                      measured by `locate` rather than written by hand
  entity_names.json   135 KB, exported from the semantic index
  ai_grammar.json     3 KB, exported from the reader

They go to `app/` because that is the folder the exe treats as its root, and the
loader walks up from there. `stat_offsets.json` is 19 MB; shipping it keeps the
program correct without a Python step at first run, which is the point of this
whole exercise.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = P.BUNDLE
BUILT = P.EXE
#: Which tables travel is NOT a second opinion.  It used to be a hand list here,
#: and it drifted: `class_names.json` was named twice, `civ_names.json` (which
#: `desktop/aoe2mod-serve/src/sentences.rs:616` opens) was never named, and
#: `stat_offsets.json` could differ from the stamp sitting beside it.  A table the
#: stamp does not vouch for cannot be checked, so the stamp defines the set:
#: everything it names, minus the measurement scaffolding, minus anything the repo
#: does not have.
def _golden_names():
    # make_bundle is imported as a MODULE, not as _probe.make_bundle: this file
    # runs as a script, so sys.path[0] is _probe/ itself and the repository root
    # is not importable (there is no _probe/__init__.py, on purpose).
    import make_bundle as MB
    SCAFFOLDING = MB.SCAFFOLDING
    stamp = os.path.join(ROOT, "_golden", "dat_stamp.json")
    names = []
    if os.path.isfile(stamp):
        with io.open(stamp, encoding="utf-8") as fh:
            names = [n for n in sorted(json.load(fh).get("tables") or {})
                     if n not in SCAFFOLDING]
    # `ai_grammar`, `civ_trees` and `stat_mirrors` are measured by probes that
    # predate the stamp, so it does not name them; both engines still open them.
    for extra in ("ai_grammar.json", "civ_trees.json", "stat_mirrors.json"):
        if extra not in names:
            names.append(extra)
    return [n for n in names if os.path.isfile(os.path.join(ROOT, "_golden", n))]


GOLDEN = _golden_names()


def check_exe_is_the_built_one(out):
    """Refuse when the bundle holds a different binary from the one just built.

    This gate installs the TABLES and then launches whatever exe the folder
    already has. On 2026-10-27 21:22 that made it print ALL ROUTES OK while
    running a 20:34 binary -- every route passed because every route it asked
    about existed in the old build too. A suite that verifies a copy of the
    program instead of the program is the "all green, wrong artefact" failure
    this project has already paid for once.
    """
    exe = os.path.join(out, "aoe2-mod-workshop.exe")
    if not os.path.isfile(exe):
        print("REFUSING: no exe in the bundle at", exe)
        return None
    if not os.path.isfile(BUILT):
        print("REFUSING: the shell is not built at", BUILT)
        return None
    a, b = os.path.getsize(exe), os.path.getsize(BUILT)
    if a != b:
        print("REFUSING: the bundle's exe is not the built one.")
        print("  bundle %d bytes  %s" % (a, exe))
        print("  built  %d bytes  %s" % (b, BUILT))
        print("  run _probe/make_bundle_native.py to copy it in.")
        return None
    same = open(exe, "rb").read() == open(BUILT, "rb").read()
    if not same:
        print("REFUSING: same size, different bytes -- the bundle predates the build.")
        print("  run _probe/make_bundle_native.py to copy it in.")
        return None
    print("  exe %d bytes, byte-identical to the build" % a)
    return exe


def install_tables(app_dir):
    """Copy the offset tables in, and hash every one the stamp names against it.

    The stamp says which `.dat` the tables were measured from.  A table that
    disagrees with it is worse than a missing one: the guard sees a stamp, passes,
    and every write lands in the neighbouring field with ok:true (measured
    2026-11-12: bundle `59e9ba56…` vs stamp `237dbf7f…`, 1,268,964 offsets
    displaced by 27-36 bytes).  So the copy is verified here as well as in
    `_probe/make_bundle.copy_golden`, because this script is the other door into
    the same folder.
    """
    dst_dir = os.path.join(app_dir, "_golden")
    os.makedirs(dst_dir, exist_ok=True)
    stamp = {}
    stamp_path = os.path.join(ROOT, "_golden", "dat_stamp.json")
    if os.path.isfile(stamp_path):
        with io.open(stamp_path, encoding="utf-8") as fh:
            stamp = json.load(fh).get("tables") or {}
    total = 0
    for name in GOLDEN:
        src = os.path.join(ROOT, "_golden", name)
        if not os.path.isfile(src):
            print("REFUSING: missing %s (run the make_* probe)" % src)
            return None
        dst = os.path.join(dst_dir, name)
        shutil.copy2(src, dst)
        total += os.path.getsize(dst)
        print("  %-20s %8.1f KB" % (name, os.path.getsize(dst) / 1024.0))
        want = stamp.get(name)
        if want and _sha256_of(dst) != want:
            print("REFUSING: %s does not match the stamp (bundle %s… vs stamp %s…)"
                  % (name, _sha256_of(dst)[:12], want[:12]))
            print("  re-run the make_* probes, then _probe/make_dat_stamp.py")
            return None
    return total


def _sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# An 8x8 red square as base64 PNG.  A preview needs a decodable picture and
# nothing else; generating it here keeps the gate readable and file-free.
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAEklEQVR42mP4"
    "z8DwHx9mGBkKAMLXf4HVAzL9AAAAAElFTkSuQmCC")


def check_routes(port):
    base = "http://127.0.0.1:%d" % port
    def get(path):
        return urllib.request.urlopen(base + path, timeout=120).read()

    def post(path, obj):
        d = json.dumps(obj, ensure_ascii=False).encode()
        r = urllib.request.Request(base + path, data=d,
                                   headers={"Content-Type": "application/json"},
                                   method="POST")
        return json.loads(urllib.request.urlopen(r, timeout=300).read().decode())

    ok = True

    def note(name, good, detail=""):
        nonlocal ok
        print("  %-22s %s%s" % (name, "ok" if good else "FAIL", detail))
        if not good:
            ok = False

    m = json.loads(get("/api/meta"))
    note("/api/meta", m.get("ok") and len(m.get("civs") or []) == 63,
         " civs=%d" % len(m.get("civs") or []))
    p = json.loads(get("/api/progress"))
    note("/api/progress", (p.get("progress") or {}).get("ready") is True)

    pr = post("/api/parse", {"text": "村民血量改成1000"})
    got = (pr.get("intents") or [])
    note("/api/parse", bool(got) and got[0].get("stat") == "hit_points",
         " intents=%d" % len(got))
    if not got:
        print("      refusal:", pr.get("refusals"))

    f = json.loads(get("/api/forms"))
    note("/api/forms", len(f.get("forms") or []) == 23,
         " forms=%d" % len(f.get("forms") or []))
    # Counted against the file the bundle actually ships, not a number typed
    # here.  This line said 55 from 2026-10-27 until three keys were added and
    # it started reporting FAIL on a healthy program -- a hardcoded count is a
    # sentence that stops being true without anyone touching the route.
    l = json.loads(get("/api/locale?locale=zh"))
    zh_path = os.path.join(OUT, "app", "aoe2mod", "schema", "locales", "zh.json")
    shipped_keys = len((json.load(open(zh_path, encoding="utf-8"))
                        .get("strings") or {}))
    got_keys = len(l.get("strings") or {})
    note("/api/locale", got_keys == shipped_keys and got_keys > 0,
         " keys=%d (bundle zh.json has %d)" % (got_keys, shipped_keys))

    try:
        mods = json.loads(get("/api/mods"))
    except Exception as exc:
        print("      /api/mods raised:", exc)
        mods = {}
        ok = False
    note("/api/mods", mods.get("ok") is True,
         " rows=%d" % len(mods.get("mods") or []))

    # `size=` is the key the route reads (`max_side=q.get("size", [0])[0]`); a
    # `max=` spelling is ignored without complaint and answers a 256x256 picture,
    # which made this line pass while measuring nothing about resizing.
    ic = get("/api/icon?kind=unit&id=15&section=Units&size=64")
    note("/api/icon", ic[:4] == b"\x89PNG", " %d bytes" % len(ic))

    # ONE FOLDER FOR A PICTURE.  The question the player asked on 2026-11-11 --
    # 「为什么我换个图标非得要两个一起才能用」 -- is answered by the shape of
    # this preview: a record that already names a slot that resolves to a file
    # keeps that number, so no .dat byte moves and the build is one folder.
    # Checked against the shipped route, not against the source.
    ip = post("/api/icon-set", {"kind": "unit", "record": 74,
                                "civ": "British", "dry": True,
                                "filename": "gate.png",
                                "data_b64": _TINY_PNG_B64})
    note("/api/icon-set inplace", ip.get("ok") is True
         and ip.get("mode") == "inplace"
         and ip.get("becomes") == ip.get("was"),
         " 民兵 槽 %s 原地换，共用它的单位 %s 个"
         % (ip.get("slot"), len(ip.get("shares") or [])))

    # The other answer, asked for on purpose: a fresh slot rewrites IconID, and
    # that is the shape that costs a .dat and two folders.
    nw = post("/api/icon-set", {"kind": "unit", "record": 74, "civ": "British",
                                "dry": True, "inplace": False,
                                "filename": "gate.png",
                                "data_b64": _TINY_PNG_B64})
    note("/api/icon-set newslot", nw.get("ok") is True
         and nw.get("mode") == "newslot"
         and nw.get("slot") != nw.get("was"),
         " 民兵 槽 %s -> %s（要带 .dat，拆两个文件夹）"
         % (nw.get("was"), nw.get("slot")))

    br = json.loads(get("/api/browse?kind=unit&limit=5"))
    note("/api/browse", (br.get("browse") or {}).get("total") == 1651,
         " total=%s" % (br.get("browse") or {}).get("total"))

    # The Barracks fills 11 of the panel's 15 boxes on the first screen
    # (buttons 1,2,3,4,6,7,9,11,12,13,15 -- five are empty in the .dat).  This
    # line demanded 4 from 2026-10-27 until the card began reading the game's
    # own build-panel file, and then reported FAIL on a correct answer.
    # `unit_count` stays the .dat total (49) so a narrowed card is still
    # distinguishable from a small one.
    cd = json.loads(get("/api/card?building=12"))
    note("/api/card", cd.get("box_count") == 11 and cd.get("unit_count") == 49
         and cd.get("slots") == 15 and cd.get("page_boxes") == 15
         and cd.get("page_count") == 2,
         " 兵营 %s 槽 %s 格 %s 单位 %s 研究（每屏 %s 格 / %s 屏）"
         % (cd.get("slots"), cd.get("box_count"), cd.get("unit_count"),
            cd.get("tech_count"), cd.get("page_boxes"), cd.get("page_count")))

    # /api/civ answers what the .dat cannot: per-civilisation availability.
    # Asserted on the split that motivated the route -- 23 civilisations can
    # research Hand Cannoneer, 38 cannot -- because "the route returned JSON" is
    # not evidence that it returned the right answer.
    c1 = json.loads(get("/api/civ?civ=BRITONS&units=5,4"))
    ans = {a.get("id"): a.get("status") for a in (c1.get("answers") or [])}
    note("/api/civ hand cannoneer", c1.get("ok") is True and ans.get(5) == "unavailable",
         " BRITONS 手炮=%s 步弓=%s" % (ans.get(5), ans.get(4)))
    c2 = json.loads(get("/api/civ?civ=FRANKS&units=5"))
    note("/api/civ gated", (c2.get("answers") or [{}])[0].get("status") == "gated",
         " FRANKS 手炮=%s" % (c2.get("answers") or [{}])[0].get("status"))
    c3 = json.loads(get("/api/civ?civ=NOSUCH&units=5"))
    note("/api/civ unknown civ", c3.get("ok") is False and len(c3.get("known") or []) == 62,
         " known=%d" % len(c3.get("known") or []))
    c4 = json.loads(get("/api/civ?civ=BRITONS"))
    tree = c4.get("tree") or {}
    note("/api/civ whole tree", c4.get("asked") == "everything"
         and sum(len(v) for v in (tree.get("u") or {}).values()) > 0,
         " units=%d" % len(tree.get("u") or {}))

    # The card must narrow, and `unit_count` must stay the .dat total so the
    # caller can tell a small card from a filtered one. A narrowed card that
    # reported 8 units with no trace of 49 would be indistinguishable from a
    # building that only has 8.
    # `civ` is the .dat spelling the server echoes (`British`), not the tree
    # stem the caller typed; the page prints that spelling, so this asserts
    # the same string the page would.
    cb = json.loads(get("/api/card?building=12&civ=BRITONS"))
    note("/api/card?civ", cb.get("civ") == "British"
         and cb.get("shown_count") == 8 and cb.get("unit_count") == 49
         and cb.get("box_count") == 5,
         " 兵营 .dat 49 -> 英文明 %s（隐藏 %s）"
         % (cb.get("shown_count"), cb.get("hidden_count")))
    unlisted = cb.get("unlisted") or []
    excluded = cb.get("excluded") or []
    # The Eagle line is a regional unit 2 of 62 civs have; Britons is not one.
    # It disappears because the tree does not mention it, so it must land in
    # `unlisted`, not `excluded` -- the game did not write "NotAvailable" for it.
    note("/api/card?civ unlisted", 751 in unlisted and 753 in unlisted,
         " 鹰勇士 751/753 unlisted=%s excluded=%s"
         % (751 in unlisted, 751 in excluded))
    # A not-listed-anywhere chronicle unit must be reported too, not dropped
    # silently: 361 北欧剑士 is in no tree at all.
    note("/api/card?civ unlisted chronicle", 361 in unlisted,
         " 北欧剑士 361 unlisted=%s" % (361 in unlisted))
    note("/api/card?civ reasons sum", len(unlisted) + len(excluded) == cb.get("hidden_count"),
         " unlisted %d + excluded %d = %s"
         % (len(unlisted), len(excluded), cb.get("hidden_count")))

    # The other reason, on a real case: ACHAEMENIDS cannot train the Crossbowman
    # and its tree says so in writing (NotAvailable). Asserting `excluded` is
    # non-empty somewhere is not enough -- Britons has no such row at all, so a
    # broken `excluded` path would never show up on the card above.
    ca = json.loads(get("/api/card?building=87&civ=ACHAEMENIDS"))
    note("/api/card?civ excluded", 492 in (ca.get("excluded") or [])
         and 492 not in (ca.get("unlisted") or []),
         " 靶场 劲弩手 492 excluded（明写 NotAvailable）")
    cbad = json.loads(get("/api/card?building=12&civ=NOSUCH"))
    note("/api/card?civ unknown", cbad.get("ok") is False,
         " 未知文明不出未过滤的卡")

    # The page posts an intent ARRAY. Posting a flat {stat,unit,value} body -- which
    # is what the earlier probes did -- passes while the button is broken, because
    # the flat shape IS what the single-intent fallback reads.
    pa = post("/api/parse", {"text": "村民血量改成1000"})
    bt = post("/api/build", {"intents": pa.get("intents") or [], "title": "gate-page-build"})
    note("/api/build (page shape, 1)", bt.get("ok") is True, " %s" % (bt.get("error") or ""))
    # TWO sentences in one build.  This used to assert a REFUSAL, because the
    # engine could only carry one intent and answering "ok" would have meant
    # silently dropping the second.  `build_bundle` carries both now, so the
    # question changed: not "does it refuse" but "did BOTH land" -- a bundle
    # that reports ok while `per_intent_edits` has one entry is the failure
    # this line exists to catch, and a refusal is now the wrong answer.
    pa2 = post("/api/parse", {"text": "村民血量改成1000。把织布机和铸币术做成只能选一个"})
    intents2 = pa2.get("intents") or []
    bt2 = post("/api/build", {"intents": intents2, "title": "gate-page-two"})
    # Every sentence must be ACCOUNTED FOR, and the two kinds land in
    # different buckets: a .dat sentence reports its own count in
    # `per_intent_edits`, while a toggle-group sentence reports the group rule
    # it wrote in `linked_groups`.  Demanding one entry per sentence in
    # `per_intent_edits` was wrong -- measured 2026-11-10, a correct two-
    # sentence build answers `[1701]` plus one group, and that reading failed
    # a healthy program.  A sentence that landed in neither bucket is the
    # silent drop this line is here to catch.
    man2 = bt2.get("manifest") or {}
    pie = man2.get("per_intent_edits") or []
    groups2 = man2.get("linked_groups") or []
    landed = len([n for n in pie if n > 0]) + len([g for g in groups2
                                                    if g.get("ok")])
    note("/api/build (page shape, 2)", bt2.get("ok") is True
         and landed == len(intents2) and len(groups2) >= 1
         and (bt2.get("edit_count") or 0) > 0,
         " %d 句 -> .dat %s + 组 %d 条，共 %d 处改动"
         % (len(intents2), pie, len(groups2), bt2.get("edit_count") or 0))

    tg = post("/api/toggle-group", {"techs": [22, 23], "title": "gate-toggle"})
    note("/api/toggle-group", tg.get("ok") is True and tg.get("entries") == 21,
         " %s 条" % tg.get("entries"))

    # A REAL swap, with a donor.  This posted only `{"title": ...}` from
    # 2026-10-27 and expected 244 records: the route refuses a missing donor
    # on purpose (a swap with no donor is "swap with what?"), so the line was
    # asking for a number the correct answer cannot produce.  Villager 83 ->
    # Longbowman 8 in `rename` mode is 10 graphics records; the count is
    # compared with the plan's own promise rather than typed here.
    sp_plan = post("/api/plan", {"intent": {"intent": "unit.sprite", "unit": 83,
                                               "donor": 8, "mode": "rename"}})
    sp_promise = (sp_plan.get("plan") or {}).get("edit_count")
    sp = post("/api/sprite", {"title": "gate-sprite", "unit": 83, "donor": 8})
    note("/api/sprite", sp.get("ok") is True and sp.get("records") == sp_promise
         and (sp.get("records") or 0) > 0,
         " %s 条（计划也答应 %s 条），dry=%s"
         % (sp.get("records"), sp_promise, sp.get("dry")))

    # A dry run, and asserted on `moved`, which is the shape the route actually
    # answers.  `before`/`after` were never keys here, so the detail printed
    # "None->None" and the line told a reader nothing about where the unit went.
    mv = post("/api/card-move", {"unit": 74, "building": 12, "box": 5,
                                  "title": "gate-card-move", "dry": True})
    moved1 = (mv.get("moved") or [{}])[0]
    note("/api/card-move", mv.get("ok") is True and mv.get("bytes_changed") == 1
         and moved1.get("from") == 1 and moved1.get("to") == 5
         and mv.get("dry") is True,
         " 民兵 第 %s 格 -> 第 %s 格（dry）"
         % (moved1.get("from"), moved1.get("to")))

    # A PSEUDO PAGE, END TO END, THROUGH THE SHIPPED SERVER.  The panel's answer
    # to 「怎么用」 is 「先建一个空页，再往页里点图标」 (2026-11-10), and that
    # sentence is only true if three writes exist in the bundle: the page, the
    # unit on the page, and the page gone again.  A dry run would prove none of
    # them, because the effect record is what is being rewritten.
    pg = post("/api/pseudo-pages", {"building": 12, "box": 19, "on": [],
                                    "seconds": 0, "title": "gate-page"})
    note("/api/pseudo-pages", pg.get("ok") is True and pg.get("grew") == 87,
         " 空页 tech=%s effect=%s grew=%s"
         % (pg.get("tech"), pg.get("effect"), pg.get("grew")))
    # TWO WRITES, TWO SIZES.  The page half always grows by one 11-byte
    # command; the cell half adds a 9-byte training entry only when the unit
    # has none on this building (村民 has no Barracks entry, 民兵 does).
    # Measured 2026-11-11 on the shipped file: 11 + 9 = 20.
    pgu = post("/api/pseudo-page-put", {"building": 12, "box": 19, "unit": 83,
                                        "page": 1})
    note("/api/pseudo-page-put", pgu.get("ok") is True
         and pgu.get("on") == [83] and pgu.get("grew") in (11, 20),
         " 村民 进第 1 页 on=%s grew=%s 格=%s how=%s"
         % (pgu.get("on"), pgu.get("grew"), pgu.get("slot"), pgu.get("how")))
    pgr = json.loads(get("/api/pseudo-pages?building=12&box=19"))
    names = [(one.get("on_list") or [{}])[0].get("name")
             for one in (pgr.get("page_list") or [])]
    note("/api/pseudo-pages read", pgr.get("pages") == 1 and names == ["村民 (男性)"],
         " 读回 %s 页 %s" % (pgr.get("pages"), names))
    pgd = post("/api/pseudo-page-drop", {"building": 12, "box": 19, "page": 1})
    note("/api/pseudo-page-drop", pgd.get("ok") is True,
         " %s" % (pgd.get("label") or pgd.get("error")))
    gone = json.loads(get("/api/pseudo-pages?building=12&box=19"))
    note("/api/pseudo-pages empty", gone.get("pages") == 0,
         " 删完 %s 页" % gone.get("pages"))
    # THE PAGE IS TOLD, NOT ASKED.  「这个页面依旧是不能实时更新的」
    # (2026-11-11) was answered with a long poll plus page verbs that hand back
    # their own answer, and neither is worth anything if the bundle only got
    # the repository's Python for one of the two halves: `_live_v` lives in
    # `server.py`, the loop that reads it lives in `index.html`.  So the shipped
    # exe is asked the same question a parked screen asks.
    live = json.loads(get("/api/live?wait=1"))
    note("/api/live", live.get("ok") is True and isinstance(live.get("v"), int)
         and isinstance(live.get("pending"), int),
         " v=%s pending=%s undo=%s bytes=%s"
         % (live.get("v"), live.get("pending"), live.get("undo"),
            live.get("bytes")))
    # AND THE ANSWER A PAGE WRITE CARRIES.  The panel used to call `loadCard`
    # after every tile; it now paints from `page_list`, so a bundle whose
    # verbs answer without it would draw nothing and look like a dead button.
    note("/api/pseudo-page-put answers", (pgu.get("page_list") or [{}])[0]
         .get("on_list", [None])[0].get("name") == "村民 (男性)",
         " the write names the unit it placed, so no re-read is owed")
    # 放弃 puts the game's own bytes back, so the checks below run on a clean
    # session -- a build or a save after this point must not carry a probe page.
    post("/api/session-reset", {})

    d = json.loads(get("/api/describe?kind=unit&id=1810"))
    note("/api/describe", (d.get("entity") or {}).get("name") == "村民")

    ai = json.loads(get("/api/ai-meta"))
    note("/api/ai-meta", len(ai.get("grammar") or "") > 500,
         " grammar=%d chars" % len(ai.get("grammar") or ""))

    tp = post("/api/parse", {"text": "织布机研究时间改成5"})
    ti = (tp.get("intents") or [])
    note("/api/parse (tech)", bool(ti) and ti[0].get("intent") == "tech.research_time",
         " %r" % (ti[0] if ti else tp.get("refusals")))

    u = json.loads(get("/api/update-check"))
    note("/api/update-check", u.get("ok") is True,
         " rows=%d" % len(u.get("rows") or []))

    # 这一条问的是「这一份工具自己有没有新版」，和上面那条（游戏数据动过吗）
    # 是两回事。 判据故意用 `behind is not None` 而不是 reachable：门禁可能
    # 跑在没有外网的机器上，那时答案必须是「不知道」而不是一条不存在的错误；
    # 有网时它才去读 raw.githubusercontent 上的 appversion.py。
    vc = json.loads(get("/api/version-check?force=1"))
    note("/api/version-check", vc.get("ok") is True
         and "behind" in vc and "current" in vc,
         " current=%r remote=%r behind=%r" % (vc.get("current"),
                                                vc.get("remote"),
                                                vc.get("behind")))

    return ok


def kill_exe():
    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)


def kill_engine_child():
    """Kill the shipped runtime python this exe started, if it outlived it.

    `taskkill /IM aoe2-mod-workshop.exe` kills the shell; the child python it
    spawned keeps the listening socket for a few more seconds and, because
    Windows lets two sockets share a port without SO_EXCLUSIVEADDRUSE, a new
    child can bind the same port while the dying one still accepts.  Then a
    request lands on the corpse and the probe reads `ConnectionResetError
    [WinError 10054]` -- which is what happened at 02:47 on a bundle that then
    passed every route twice.  The child is the bundle's own runtime python,
    so it is identified by its executable path, never by image name.
    """
    exe_dir = os.path.dirname(os.path.abspath(os.path.join(OUT, "x")))
    script = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
              "Where-Object { $_.ExecutablePath -like '" + exe_dir + "*' } | "
              "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   capture_output=True)


def _listening(port):
    """True when something holds a LISTEN socket on `port` right now."""
    cmd = ("(Get-NetTCPConnection -LocalPort %d -State Listen " % port
           + "-ErrorAction SilentlyContinue | Measure-Object).Count")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                         capture_output=True, text=True)
    try:
        return int(out.stdout.strip().split()[0]) > 0
    except Exception:
        return False


def port_free(port, secs=60):
    """Block until nothing listens on `port`, or give up.  See main()."""
    t0 = time.time()
    while time.time() - t0 < secs:
        if not _listening(port):
            return True
        time.sleep(1)
    return not _listening(port)


def wait_ready(port, secs=240):
    """Poll /api/meta until it answers JSON.  Returns seconds waited, or None.

    /api/meta answering proves the socket belongs to THIS process: `_warm` has
    already filled `version` by the time the first request is served.
    """
    url = "http://127.0.0.1:%d/api/meta" % port
    t0 = time.time()
    last = None
    while time.time() - t0 < secs:
        try:
            if urllib.request.urlopen(url, timeout=20).read()[:1] == b"{":
                return time.time() - t0
        except Exception as exc:
            last = exc
        time.sleep(2)
    print("  /api/meta never answered; last error:", last)
    return None


def engine_log_tail(lines=25):
    """Last lines of the engine log, when this run left one."""
    path = os.path.join(os.environ.get("TEMP", ""), "aoe2-mod-workshop.log")
    try:
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return [ln.rstrip("\n") for ln in fh.readlines()[-lines:]]
    except Exception:
        return []


def main():
    app = os.path.join(OUT, "app")
    if not os.path.isdir(app):
        print("REFUSING: no bundle at", OUT)
        return 1
    print("installing tables into", os.path.join(app, "_golden"))
    total = install_tables(app)
    if total is None:
        return 1
    print("  total %.1f MB" % (total / (1024.0 * 1024.0)))
    # Every table the engine reads must be present: a missing one does not crash,
    # it silently changes behaviour -- "步弓手对骑兵攻击加2" fell through to
    # unit.stat when class_names.json was absent from the bundle.
    golden_dir = os.path.join(app, "_golden")
    have = set(os.listdir(golden_dir)) if os.path.isdir(golden_dir) else set()
    missing = [g for g in GOLDEN if g not in have]
    if missing:
        print("  FAIL missing tables: %s" % missing)
        return 1
    print("  all %d tables present" % len(GOLDEN))

    exe = check_exe_is_the_built_one(OUT)
    if not exe:
        return 1
    kill_exe()
    kill_engine_child()
    # WAIT FOR THE PORT, NOT FOR A CLOCK.  `time.sleep(1)` after taskkill was a
    # guess: the exe dies at once but its child python keeps the listening
    # socket for a few more seconds, and a new exe that cannot bind leaves the
    # old child answering -- so the probe paid a full connect on a socket that
    # was being torn down and read `ConnectionResetError [WinError 10054]` as
    # "the shipped program is broken" (2026-11-11 02:37, twice, on a bundle
    # that then passed every route).  Waiting for the listener to disappear,
    # then polling /api/meta instead of sleeping 10 s, is the same evidence
    # without the race.
    if not port_free(7799, secs=60):
        print("REFUSING: port 7799 is still held after the old exe was killed")
        return 1
    # KEEP THE CHILD'S OUTPUT.  `DEVNULL` cost an hour on 2026-11-11: the exe
    # answered 26 routes, then died on the 27th and the probe saw only
    # `ConnectionResetError [WinError 10054]`, with the reason already printed
    # to a stream nobody kept.  A crash you cannot read is a crash you will
    # meet again.
    exe_log = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "_tmp", "ship_exe.log")
    fh = open(exe_log, "wb")
    p = subprocess.Popen([exe, "--port", "7799"], cwd=OUT,
                         stdout=fh, stderr=fh)
    ok = False  # bound before `try`, so the finally block can report on it
    try:
        took = wait_ready(7799, secs=240)
        if took is None:
            print("REFUSING: the shipped program never answered on /api/meta")
            return 1
        print("  ready after %.1f s" % took)
        print()
        print("checking the SHIPPED program on port 7799")
        ok = check_routes(7799)
    finally:
        p.terminate()
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
        fh.close()
        if not ok:
            # The engine writes its own log to %TEMP%; a route that stops
            # answering usually left the reason there.  Printing it here is the
            # difference between "the bundle is broken" and "line 12 of the log".
            tail = engine_log_tail()
            if tail:
                print()
                print("  last lines of the engine log:")
                for line in tail:
                    print("    " + line[:200])
    print()
    print("SHIPPED BUNDLE: %s" % ("ALL ROUTES OK" if ok else "FAILURES ABOVE"))
    print("  exe output kept at %s" % exe_log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
