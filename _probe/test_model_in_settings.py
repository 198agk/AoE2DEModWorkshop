# -*- coding: utf-8 -*-
"""The model connector has one home, and it is Settings.

Three separate things are being asserted, because each one has already been
wrong in a way that looked fine on screen:

1. The five model controls live inside `#setgroup-model` and nowhere else.  A
   second copy on the scripting page would keep working, which is why a
   duplicate is more likely to ship than a breakage.
2. `#setgroup-model` is reachable: its tab exists, carries `data-setgroup`, and
   the tab-switching code in the page is written against `data-setgroup` rather
   than a hard-coded list.  A panel nobody can open is a panel that does not
   exist.
3. The three sentences that tell a player *where* to configure the model agree
   with where the panel actually is.  These are the only instructions a stuck
   player gets, and they were pointing at environment variables only, which
   nobody sets before double-clicking an exe.

Run with the workspace python:
    C:/Users/26913/AppData/Local/Python/bin/python.exe -X utf8 _probe/test_model_in_settings.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HTML = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")

FAILS = []


def check(label, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label + ("" if ok else "  ::  " + str(detail)))
    if not ok:
        FAILS.append(label)


def section(html, start, end):
    """Text between two literal anchors, or "" when either is missing.

    The end anchor has to be searched *after* the start one: the model panel is
    written last, so `setgroup-look` sits before it and a plain `in` test would
    find it and then slice backwards.
    """
    if start not in html:
        return ""
    a = html.index(start)
    b = html.find(end, a + len(start))
    return html[a:] if b < 0 else html[a:b]


def main():
    html = io.open(HTML, "rb").read().decode("utf-8")

    print("=== A. the panel exists and holds all five controls")
    panel = section(html, '<div class="setgroup" id="setgroup-model">',
                    '<div class="setgroup" id="setgroup-look">')
    if not panel:
        # The model panel is written after 高级, so the closing order differs.
        panel = section(html, '<div class="setgroup" id="setgroup-model">', "</section>")
    check("the model panel is a settings group", 'id="setgroup-model"' in html, panel[:80])
    for cid in ("ai-model-base", "ai-model-name", "ai-model-key",
                "ai-model-save", "ai-model-clear", "ai-model-verdict"):
        check("  %s is inside it" % cid, ('id="%s"' % cid) in panel,
              "found elsewhere" if ('id="%s"' % cid) in html else "missing entirely")

    print("=== B. exactly one copy on the page")
    for cid in ("ai-model-base", "ai-model-name", "ai-model-key"):
        check("  %s appears once" % cid, html.count('id="%s"' % cid) == 1,
              html.count('id="%s"' % cid))

    print("=== C. the scripting page no longer owns it")
    lang = section(html, '<section class="view" id="view-lang">', '<section class="view" id="view-settings">')
    check("the scripting page was found", lang != "", len(lang))
    check("  no model heading there", "<h2>大模型接口</h2>" not in lang)
    check("  no model input there", 'id="ai-model-base"' not in lang)
    check("  it still says where to go",
          "设置" in lang and "模型" in lang, "a player who looked there yesterday needs one line")

    print("=== D. the tab can be opened")
    check("a tab names the panel", 'data-setgroup="model"' in html)
    check("the tab is in the settings nav",
          'id="settab-model"' in section(html, '<nav class="setnav"', "</nav>"))
    switch = section(html, 'document.querySelectorAll("[data-setgroup]").forEach',
                     "// ---- the title bar")
    check("the switcher reads data-setgroup, not a list",
          'getAttribute("data-setgroup")' in switch and 'id === "setgroup-" + want' in switch,
          switch[:200])
    check("opening Settings re-reads the file", 'if (name === "settings") aiModelLoad();' in html,
          "the panel would otherwise report the state it had at boot")

    print("=== E. the sentences point at the panel, not only at env vars")
    for path, name in ((os.path.join(ROOT, "aoe2mod", "ai.py"), "ai.py"),
                       (os.path.join(ROOT, "aoe2mod", "game", "aiwriter.py"), "aiwriter.py")):
        src = io.open(path, "rb").read().decode("utf-8")
        blob = src[src.find("这个版本没有配"):][:400]
        check("  %s points at 设置 → 模型" % name, "设置" in blob and "模型" in blob, blob[:120])
        # `ai.py` builds the variable names from its own constants, so the literal
        # string is not in the sentence on purpose (one place to rename them).
        names_it = ("AOE2MOD_AI_KEY" in blob) or ("KEY_ENV" in blob)
        check("  %s still names the key variable" % name, names_it, blob[:120])

    print()
    if FAILS:
        print("MODEL IN SETTINGS: %d FAILED" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print("MODEL IN SETTINGS: ONE PANEL, OPENED FROM THE SIDEBAR, AND THE INSTRUCTIONS AGREE WITH IT")


main()
