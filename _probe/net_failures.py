# -*- coding: utf-8 -*-
"""List every request the shipped page makes that does not come back 2xx.

A console "Failed to fetch" toast tells you something broke but not what, so
this records the URL and the failure text for each one.
"""
import sys

from playwright.sync_api import sync_playwright

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7814


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1255, "height": 897})
        bad = []
        pg.on("requestfailed",
              lambda r: bad.append(("failed", r.url, r.failure)))
        pg.on("response", lambda r: bad.append(("status", r.url, r.status))
              if r.status >= 400 else None)
        pg.on("pageerror", lambda e: bad.append(("pageerror", str(e), "")))

        pg.goto("http://127.0.0.1:%d/" % PORT, wait_until="load", timeout=90000)
        pg.wait_for_timeout(16000)

        toasts = pg.evaluate("""() => [...document.querySelectorAll('.toast')]
            .map(t => t.textContent).filter(Boolean)""")
        print("toasts:", toasts)
        seen = set()
        for kind, url, extra in bad:
            key = (kind, url.split("?")[0])
            if key in seen:
                continue
            seen.add(key)
            print("%-9s %-60s %s" % (kind, url[:120], extra))
        if not bad:
            print("no failed request")
        b.close()


main()
