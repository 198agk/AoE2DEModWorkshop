# -*- coding: utf-8 -*-
"""Screenshot the page the shipped exe is actually serving.

Port 7814 is the bundled runtime's own server (spawned by aoe2-mod-workshop.exe),
so this is the same bytes the WebView2 window renders -- unlike 7811, which is
the dev server reading the repo.
"""
import sys

from playwright.sync_api import sync_playwright

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7814
VIEWS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["home", "settings"]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1255, "height": 897},
                    device_scale_factor=1.5)
    errors = []
    pg.on("console", lambda m: errors.append("console:" + m.text)
          if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append("pageerror:" + str(e)))

    # `networkidle` never fires here: /api/mods reads every installed mod and the
    # bundled runtime answers it in ~11 s, so the load event is the honest signal
    # and the renders that follow are allowed to arrive on their own time.
    pg.goto("http://127.0.0.1:%d/" % PORT, wait_until="load", timeout=90000)
    pg.wait_for_timeout(16000)

    # The authenticity notice is a first-run modal; every shot below wants the
    # page under it, not the modal itself.
    pg.evaluate("""() => {
        const n = document.getElementById('notice');
        if (n) n.classList.remove('on');
    }""")

    for v in VIEWS:
        pg.evaluate("(v) => showView(v)", v)
        pg.wait_for_timeout(900)
        out = "_shots/now/ship_%s.png" % v
        pg.screenshot(path=out)
        print("shot", v, out)

    info = pg.evaluate("""() => ({
        views: VIEWS.length,
        view: VIEW,
        prefs: localStorage.getItem('aoe2mod.prefs'),
        tauri: document.body.classList.contains('tauri'),
        winbtns: getComputedStyle(document.querySelector('.winbtns')).display,
        toasts: [...document.querySelectorAll('.toast')].map(t => t.textContent),
        fs: getComputedStyle(document.body).getPropertyValue('--fs-body').trim(),
        setRows: document.querySelectorAll('#view-settings .setrow').length,
        setVer: (document.getElementById('set-ver') || {}).textContent,
        setMods: (document.getElementById('set-mods') || {}).textContent,
        setDat: (document.getElementById('set-dat') || {}).textContent,
    })""")
    for k in sorted(info):
        print("%-9s %r" % (k, info[k]))
    print("errors   ", errors if errors else "none")
    b.close()
