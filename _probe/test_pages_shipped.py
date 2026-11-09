# -*- coding: utf-8 -*-
"""A page-level gate: does every view actually have content?

Why this exists
---------------
Every endpoint probe in this project was green while the screen was blank. The
console had the answer the whole time:

    TypeError: META.intents is not iterable
      at renderIntentList
      at boot

`boot()` threw, so the editor never initialised and sat on "读取中…" -- and no
per-endpoint test could see it, because `/api/browse` was fine. The owner's
complaint ("你这是做了个壳给我") was about the screen, and the screen is the user.

So this gate drives the real page and asserts, per view:
  * no uncaught exception during boot;
  * the container holds MORE than its placeholder text;
  * a specific, counted fact per view (rows, cards, counts).

Run against the running app (it starts one itself on a spare port).
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

BUNDLE = P.BUNDLE
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7809

# Assertion per view: element id -> (minimum children, human name)
VIEWS = [
    ("view-home", "intents", 5, "能做的事：意图卡片"),
    ("view-editor", "edlist", 50, "编辑器：单位列表"),
    ("view-mods", "mods", 5, "模组：行"),
    ("view-card", "cardgrid", 15, "命令面板：格子"),
]

SCRIPT = r"""
async (args) => {
  const [views] = args;
  const out = { errors: [], checks: [] };
  // Collect uncaught errors from the boot sequence.
  window.addEventListener('error', e => out.errors.push(String(e.message)));
  for (const [viewId, elId, minChildren, label] of views) {
    const view = document.getElementById(viewId);
    const el = document.getElementById(elId);
    if (!view || !el) { out.checks.push({ label, ok: false, why: 'element missing' }); continue; }
    // Switch to the view the way the nav does.
    const hash = viewId.replace('view-', '');
    location.hash = hash;
    await new Promise(r => setTimeout(r, 1200));
    const kids = el.children.length;
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    const placeholders = ['读取中', '没有匹配', 'NO '];
    const onlyPlaceholder = placeholders.some(p => text === p || text.startsWith(p)) && text.length < 24;
    out.checks.push({
      label,
      ok: kids >= minChildren && !onlyPlaceholder,
      children: kids,
      sample: text.slice(0, 80),
    });
  }
  // Rail counts, which are separate numbers the screen shows.
  out.rail = {
    mods: (document.getElementById('rail-mods') || {}).textContent,
    recipes: (document.getElementById('rail-recipes') || {}).textContent,
  };
  out.status = (document.getElementById('datinfo') || {}).textContent;
  return out;
}
"""


def main():
    if not os.path.isfile(EXE):
        print("REFUSING: no bundle at", BUNDLE)
        return 1
    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)
    time.sleep(1)
    p = subprocess.Popen([EXE, "--port", str(PORT)], cwd=BUNDLE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            time.sleep(0.5)
            try:
                j = json.loads(urllib.request.urlopen(
                    "http://127.0.0.1:%d/api/progress" % PORT, timeout=5).read())
                if (j.get("progress") or {}).get("ready"):
                    break
            except Exception:
                pass

        # Drive the page through Playwright (the same engine the render gate uses).
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1237, "height": 880})
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            # NOT `networkidle`.  On a COLD start `boot()` opens the first unit
            # anyway (the editor is the default view), that builds the field
            # index over 136,861 records -- 14.52 s measured 2026-11-02 -- and
            # `watchJob` polls `/api/job?key=unit` every 200 ms while
            # `job.running` is true.  A 200 ms poll cycle can never leave a
            # 500 ms quiet window, so `networkidle` is unreachable *by design*
            # for the whole first build.  Measured 2026-11-04: 67 job polls,
            # cold open done at 24.6 s, `goto(networkidle)` dead at 30.01 s with
            # 68 polls logged; the same goto on a WARM start passes because the
            # index costs 0.003 s and no poll is ever issued.
            #
            # So wait for the STATE this gate is about, not for a quiet network.
            # The timeout is generous because it covers the cold index build --
            # and the elapsed time is printed, since "how long until the screen
            # is usable" is a product fact, not just a test detail.
            t_boot = time.time()
            pg.goto("http://127.0.0.1:%d/" % PORT, wait_until="domcontentloaded",
                    timeout=30000)
            pg.wait_for_function(
                "document.querySelectorAll('#edlist .edrow').length >= 50",
                timeout=180000)
            print("  cold boot to a usable unit list: %.1f s" % (time.time() - t_boot))
            time.sleep(2.0)
            result = pg.evaluate(
                """async (views) => {
                    const out = { checks: [] };
                    for (const [viewId, elId, minChildren, label] of views) {
                        const view = document.getElementById(viewId);
                        const el = document.getElementById(elId);
                        if (!view || !el) {
                            out.checks.push({ label, ok: false, why: 'element missing' });
                            continue;
                        }
                        location.hash = viewId.replace('view-', '');
                        await new Promise(r => setTimeout(r, 1400));
                        const kids = el.children.length;
                        const text = (el.textContent || '').replace(/\\s+/g, ' ').trim();
                        out.checks.push({
                            label, ok: kids >= minChildren, children: kids,
                            sample: text.slice(0, 90),
                        });
                    }
                    out.rail = {
                        mods: (document.getElementById('rail-mods') || {}).textContent,
                        recipes: (document.getElementById('rail-recipes') || {}).textContent,
                    };
                    out.status = (document.getElementById('datinfo') || {}).textContent;
                    // `META` is a `let` in module scope, NOT on window, so
                    // `window.META` is undefined no matter how healthy the app
                    // is. Asserting on it made this gate fail on a working
                    // build -- the gate was wrong, not the product. Read what
                    // the page RENDERS instead: the intents box already proves
                    // the list arrived, and the version line proves meta parsed.
                    out.meta_ver = (document.getElementById('ver') || {}).textContent;
                    out.intent_cards = (document.getElementById('intents') || {}).children.length;
                    out.civ_status = (document.getElementById('datinfo') || {}).textContent;
                    // The card grid, counted as BOXES with numbers, not just
                    // children. The panel drew 25 boxes for three weeks because
                    // the number came from `max(button_id)` in the .dat instead
                    // of from `widgetui/commandpanel.json`; counting children
                    // alone would have passed for both 15 and 25, so this reads
                    // the box labels back and checks the set is exactly 0..N-1
                    // with N taken from the page, not from this file.
                    const grid = document.getElementById('cardgrid');
                    const boxes = grid
                        ? Array.from(grid.children).map(c => c.dataset.box)
                                .filter(v => v !== undefined).map(Number)
                        : [];
                    boxes.sort((a, b) => a - b);
                    out.card = {
                        boxes,
                        contiguous: boxes.length > 0 &&
                            boxes.every((v, i) => v === i),
                        offgrid_note: (document.getElementById('card-offgrid') || {}).textContent,
                    };
                    return out;
                }""",
                [[v[0], v[1], v[2], v[3]] for v in VIEWS],
            )
            b.close()

        ok = True
        print("page errors:", errors if errors else "none")
        if errors:
            ok = False
        for c in result["checks"]:
            good = c.get("ok")
            print("  %-28s %s  children=%s  %r"
                  % (c["label"], "ok" if good else "FAIL",
                     c.get("children"), c.get("sample", "")[:50]))
            if not good:
                ok = False
        print("  rail: mods=%s recipes=%s" % (result["rail"]["mods"],
                                              result["rail"]["recipes"]))
        print("  status line: %r" % (result.get("status"),))
        print("  version line: %r | intent cards: %s" % (result.get("meta_ver"),
                                                         result.get("intent_cards")))
        if not result["rail"]["mods"] or result["rail"]["mods"].strip() in ("", "—"):
            print("  FAIL: rail mod count is empty")
            ok = False
        # \"已就绪\" carries a civ count, which only renders when meta parsed.
        if not (result.get("civ_status") or "").strip():
            print("  FAIL: status line is empty")
            ok = False
        if result.get("intent_cards", 0) < 5:
            print("  FAIL: intents box is empty")
            ok = False
        # The grid must be 0..N-1 with no gap and no box past the layout. The
        # specific N is asserted too: 15 is what the game's own commandpanel.json
        # holds, and the panel must not invent a 16th.
        card = result.get("card") or {}
        boxes = card.get("boxes") or []
        print("  card boxes: n=%d contiguous=%s" % (len(boxes), card.get("contiguous")))
        if not card.get("contiguous"):
            print("  FAIL: card boxes are not 0..%d-1" % len(boxes))
            ok = False
        if len(boxes) != 15:
            print("  FAIL: card grid drew %d boxes; widgetui/commandpanel.json has 15"
                  % len(boxes))
            ok = False
        if card.get("offgrid_note"):
            print("  off-grid: %s" % card["offgrid_note"][:120])

        print()
        print("PAGE GATE: %s" % ("ALL PASSED" if ok else "FAILURES ABOVE"))
        return 0 if ok else 1
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


if __name__ == "__main__":
    sys.exit(main())
