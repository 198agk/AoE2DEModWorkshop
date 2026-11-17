# -*- coding: utf-8 -*-
"""首屏能不能改：打开编辑器第一眼就该看见输入框。

WHY THIS EXISTS
---------------
2026-11-11，用户原话：「我根本用不明白你这个工具」。查下去不是文案问题，
是几何问题：记录级的东西（复制/删除/改名字/批量新增、换图标、看动画、
-1 图例、哪些科技用它）一共 271px，全堆在标题和第一行字段之间，于是
1264x821 的窗口里第一个可编辑输入框落在 y=1029，而面板底边在 y=784 ——
打开编辑器看到的是零个输入框，整页看起来是只读的。要往下滚 700px 才发现
能改。一个「能编辑」的工具，玩家第一眼必须看见能编辑的东西。

这条探针量三件事，全部是几何，不是文案：
1. 第一条字段行（#fbody table.f 的第一个 tr）顶边在面板可视区内；
2. 第一条真正能输入的 input 也在可视区内；
3. 记录条（#edtools）收起时只占一行，且它里面的 details 默认都是关的
   （关着的盒子里没有任何输入框，谁也不会以为那里能改）。

量的是发布包里的 exe，不是 dev 服务。
"""
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _paths as P  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

PORT = int(os.environ.get("FOLDPORT", "7815"))
BASE = "http://127.0.0.1:%d" % PORT
UNIT = 74

fails = []


def check(ok, what, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", what,
                         "" if not detail else " :: " + str(detail)))
    if not ok:
        fails.append(what)


def wait_up(host, timeout=180):
    """The server answers /api/progress from the first second, but the record
    index is what the editor screen waits for, so readiness is asked there."""
    import json
    end = time.time() + timeout
    while time.time() < end:
        try:
            j = json.loads(urllib.request.urlopen(
                host + "/api/progress", timeout=5).read())
            if (j.get("progress") or {}).get("ready"):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
               capture_output=True)
time.sleep(1)
proc = subprocess.Popen(
    [P.BUNDLED_EXE, "--port", str(PORT)],
    cwd=P.BUNDLE,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

try:
    if not wait_up(BASE):
        print("FOLD PROBE: THE SHIPPED EXE DID NOT ANSWER ON %s" % PORT)
        sys.exit(1)

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1264, "height": 821})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=120000)
        pg.wait_for_function(
            "() => document.querySelectorAll('#edlist .edrow').length >= 50",
            timeout=300000)
        pg.evaluate("() => { location.hash = 'editor'; }")
        pg.wait_for_timeout(900)
        pg.evaluate('async () => { await openEditor({kind:"unit", id:%d}); }' % UNIT)
        pg.wait_for_function(
            "() => { const s = document.querySelector('#edpane .edhead .s');"
            " return s && s.textContent.indexOf('编号 %d') >= 0; }" % UNIT,
            timeout=180000)
        pg.wait_for_timeout(1200)

        st = pg.evaluate("""() => {
          const pane = document.querySelector('#edpane');
          const pr = pane.getBoundingClientRect();
          // No tbody: renderFieldRows builds the header and the body rows as
          // direct children of the table, so 'tbody tr' matches nothing.
          const rows = Array.from(
            document.querySelectorAll('#fbody table.f tr'));
          // rows[0] is the header (th cells); the first FIELD is the first
          // row that carries a td.
          const firstRow = rows.find(r => r.querySelector('td')) || null;
          const first = firstRow ? firstRow.getBoundingClientRect() : null;
          const inputs = Array.from(document.querySelectorAll(
            '#fbody table.f td.e input'));
          const seen = inputs
            .map(i => i.getBoundingClientRect())
            .filter(r => r.top >= pr.top && r.bottom <= pr.bottom);
          const tools = document.querySelector('#edtools');
          const tr = tools.getBoundingClientRect();
          const shut = Array.from(tools.querySelectorAll('details'))
            .filter(d => !d.open).length;
          return {
            paneTop: Math.round(pr.top), paneBottom: Math.round(pr.bottom),
            firstRowTop: first ? Math.round(first.top) : null,
            rows: rows.length, inputs: inputs.length,
            inputsInView: seen.length,
            stripH: Math.round(tr.height),
            stripOpen: Array.from(tools.querySelectorAll('details')).length,
            stripShut: shut,
            docH: Math.round(document.documentElement.scrollHeight),
          };
        }""")

        # 1. the first row of the table is inside the pane, not below its edge
        check(st["rows"] > 300, "the field table has its rows", st["rows"])
        check(st["firstRowTop"] is not None and
              st["firstRowTop"] < st["paneBottom"],
              "the FIRST field row is above the pane's bottom edge",
              "%s vs %s" % (st["firstRowTop"], st["paneBottom"]))

        # 2. and at least one input you can actually type into is visible
        check(st["inputsInView"] >= 1,
              "an input box you can type into is on screen without scrolling",
              "%d of %d inputs inside %s..%s"
              % (st["inputsInView"], st["inputs"], st["paneTop"], st["paneBottom"]))

        # 3. the record strip is one line and shut
        check(st["stripH"] <= 48,
              "the record strip costs one line, not 271px", st["stripH"])
        check(st["stripShut"] == st["stripOpen"],
              "every box in the strip starts shut",
              "%d of %d shut" % (st["stripShut"], st["stripOpen"]))
        check(not errs, "no console errors", errs[:3])

        pg.screenshot(path=os.path.join(HERE, "_shots", "first_fold.png"))
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except Exception:
        proc.kill()

print("")
if fails:
    print("FIRST FOLD PROBE: FAILURES ABOVE")
    sys.exit(1)
print("FIRST FOLD PROBE: THE FIRST EDITABLE ROW IS ON SCREEN WHEN THE EDITOR OPENS")
