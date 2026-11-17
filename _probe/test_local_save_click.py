"""Click 放进本地模组 in the SHIPPED program, in a sandbox profile.

Reported 2026-11-10: 「这个生成的东西应该放local去」.  The HTTP probe proves the
route; this one proves the BUTTON -- that the three boxes on the script screen are
wired to it, that the toast says where the file went, and that the chooser on the
same screen lists the file it just wrote, without a reload.

The profile is a temp fixture declared through AOE2MOD_PROFILE (the shipped
engine honours it; see locations.find_profile_root), so the player's own mod list
is never touched.  A fixture, not a copy: the variable is refused unless
mods/mod-status.json exists, which is the shape the game itself writes.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _paths as P
from playwright.sync_api import sync_playwright

PORT = 7857
FAILS = []


def check(ok, what, detail=""):
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", what,
                           "" if ok or not detail else " :: %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def main():
    tmp = tempfile.mkdtemp(prefix="aoe2_click_")
    acct = os.path.join(tmp, "76561198406248391")
    os.makedirs(os.path.join(acct, "mods", "local"))
    os.makedirs(os.path.join(acct, "mods", "subscribed"))
    for sub in ("ai", "xs"):
        os.makedirs(os.path.join(acct, "resources", "_common", sub))
    # The game's own shape, so find_profile_root accepts the override.
    fh = open(os.path.join(acct, "mods", "mod-status.json"), "w",
              encoding="utf-8", newline="\n")
    fh.write('{"Mods":[],"Unsub":[]}')
    fh.close()

    exe = os.path.join(P.BUNDLE, "aoe2-mod-workshop.exe")
    subprocess.run(["taskkill", "/IM", "aoe2-mod-workshop.exe", "/F"],
                   capture_output=True)
    env = dict(os.environ)
    env["AOE2MOD_PROFILE"] = acct
    # Keep the log out of the real tool folder too.
    env["AOE2MOD_LOG_DIR"] = os.path.join(tmp, "log")
    p = subprocess.Popen([exe, "--port", str(PORT)], cwd=P.BUNDLE, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(240):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/api/meta" % PORT,
                                       timeout=3).read()
                break
            except Exception:
                time.sleep(0.5)
        print("checking the SHIPPED program on port %d (sandbox profile)" % PORT)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1237, "height": 1000})
            pg.goto("http://127.0.0.1:%d/" % PORT, wait_until="networkidle")
            pg.wait_for_timeout(2500)
            pg.click("#nav-lang")
            pg.wait_for_timeout(1200)

            # A toast is how this screen reports every other outcome; capture the
            # text so the check is on what the player actually reads.
            pg.evaluate("""() => {
              window.__toasts = [];
              const old = window.toast;
              window.toast = function (msg, kind) {
                window.__toasts.push([String(msg), String(kind || "")]);
                if (old) return old.apply(this, arguments);
              };
            }""")

            print("\n1  the AI box writes what it generated into a local mod")
            pg.fill("#lang-ai-text", "造20个骑士")
            pg.click("#lang-ai-run")
            # Wait for the box, not for a stopwatch: the first edit on a cold
            # start reads the exe's own name tables and is the slow one.
            try:
                pg.wait_for_function(
                    "() => (document.querySelector('#lang-ai-code').value || '')"
                    ".indexOf('defrule') >= 0", timeout=30000)
            except Exception:
                pass
            code = pg.input_value("#lang-ai-code")
            check("defrule" in code, "the box produced a rule", code[:60])
            mod_name = pg.input_value("#lang-ai-mod")
            check(mod_name == "", "the mod box starts empty (default folder)")
            pg.fill("#lang-ai-mod", "点击测试模组")
            pg.click("#lang-ai-local")
            try:
                pg.wait_for_function(
                    "() => (window.__toasts || []).some(t => t[0].indexOf('放进本地模组了') >= 0)",
                    timeout=30000)
            except Exception:
                pass
            toasts = pg.evaluate("() => window.__toasts")
            said = " | ".join(t[0] for t in toasts)
            check(any("放进本地模组了" in t[0] for t in toasts),
                  "the toast says it landed", said)
            check("点击测试模组" in said, "and names the mod folder", said)
            want = os.path.join(acct, "mods", "local", "点击测试模组",
                                "resources", "_common", "ai")
            files = os.listdir(want) if os.path.isdir(want) else []
            check(bool(files), "a .per is on disk under mods/local", files)
            body = ""
            if files:
                body = open(os.path.join(want, files[0]), encoding="utf-8").read()
            check("defrule" in body, "and it is the generated script", body[:60])
            doc = json.loads(open(os.path.join(acct, "mods",
                                              "mod-status.json"),
                                  encoding="utf-8").read())
            paths = [m.get("Path") for m in doc.get("Mods") or []]
            check("local//点击测试模组" in paths,
                  "the mod is registered and enabled", paths)

            print("\n2  the chooser on the same screen lists it, no reload")
            # The list is refilled AFTER the toast (saveLocalScript awaits
            # loadScriptFiles right after reporting), so an immediate read can
            # catch the gap between the old list and the new one -- measured
            # 2026-11-12, when this line read an EMPTY chooser while the file was
            # demonstrably written, registered and selected.  Wait for the
            # refresh, not for a stopwatch, then judge the content.
            try:
                pg.wait_for_function(
                    "() => Array.from(document.querySelectorAll('#lang-ai-file option'))"
                    ".some(o => (o.textContent || '').indexOf('本地模组') >= 0)",
                    timeout=30000)
            except Exception:
                pass
            opts = pg.eval_on_selector_all(
                "#lang-ai-file option", "els => els.map(e => [e.textContent, e.value])")
            check(any("本地模组" in t for t, _ in opts),
                  "the new file is in the picker, labelled 本地模组",
                  [t for t, _ in opts[:4]])
            picked = pg.input_value("#lang-ai-file")
            check(os.path.isfile(picked), "and it is selected", picked)
            # Empty the box first: leaving the generated code in it would make
            # "读进来 read it back" pass on leftovers alone.
            pg.fill("#lang-ai-code", "")
            pg.click("#lang-ai-load")
            try:
                pg.wait_for_function(
                    "() => (document.querySelector('#lang-ai-code').value || '')"
                    ".indexOf('defrule') >= 0", timeout=30000)
            except Exception:
                pass
            check("defrule" in pg.input_value("#lang-ai-code"),
                  "读进来 reads that very file back")

            print("\n3  the whole-script box does the same with its own name")
            pg.fill("#lang-plan-name", "整份测试")
            pg.fill("#lang-plan-army", "knight:15")
            pg.click("#lang-plan-run")
            try:
                pg.wait_for_function(
                    "() => (document.querySelector('#lang-plan-code').value || '')"
                    ".indexOf('defrule') >= 0", timeout=30000)
            except Exception:
                pass
            check("defrule" in pg.input_value("#lang-plan-code"),
                  "the whole script was generated")
            pg.evaluate("() => { window.__toasts = []; }")
            pg.click("#lang-plan-local")
            try:
                pg.wait_for_function(
                    "() => (window.__toasts || []).some(t => t[0].indexOf('放进本地模组了') >= 0)",
                    timeout=30000)
            except Exception:
                pass
            toasts = pg.evaluate("() => window.__toasts")
            said = " | ".join(t[0] for t in toasts)
            check(any("放进本地模组了" in t[0] for t in toasts),
                  "the whole script lands too", said)
            check("整份测试.per" in said, "under its own file name", said)

            print("\n4  the XS box writes .xs into its own folder")
            pg.fill("#lang-xs-text", "把 goal 0 设成 1")
            pg.click("#lang-xs-run")
            try:
                pg.wait_for_function(
                    "() => (document.querySelector('#lang-xs-code').value || '')"
                    ".indexOf('goal') >= 0", timeout=30000)
            except Exception:
                pass
            pg.evaluate("() => { window.__toasts = []; }")
            pg.click("#lang-xs-local")
            try:
                pg.wait_for_function(
                    "() => (window.__toasts || []).some(t => t[0].indexOf('放进本地模组了') >= 0)",
                    timeout=30000)
            except Exception:
                pass
            toasts = pg.evaluate("() => window.__toasts")
            said = " | ".join(t[0] for t in toasts)
            check(any("放进本地模组了" in t[0] for t in toasts), "the XS box saves",
                  said)
            xs_dir = os.path.join(acct, "mods", "local", "模组工坊脚本",
                                  "resources", "_common", "xs")
            check(os.path.isdir(xs_dir) and os.listdir(xs_dir),
                  "under resources/_common/xs", os.listdir(xs_dir)
                  if os.path.isdir(xs_dir) else None)

            print("\n5  a second press overwrites the same file, not a new one")
            # Asked 2026-11-10: 「默认放 local/mods 里自建一个，后续改动也按原文件名
            # 一样就覆盖」.  The AI box wrote 点击测试模组 already in section 1.
            check(pg.input_value("#lang-ai-mod") == "点击测试模组",
                  "the mod box now shows the folder it wrote",
                  pg.input_value("#lang-ai-mod"))
            before = sorted(os.listdir(want))
            # This box has no name field (the AI block names its file after the
            # remembered target), so the press alone must be an update.
            pg.fill("#lang-ai-code",
                    "(defrule\n\t(true)\n=>\n\t(chat-to-all \"second press\")\n)\n")
            pg.evaluate("() => { window.__toasts = []; }")
            pg.click("#lang-ai-local")
            try:
                pg.wait_for_function(
                    "() => (window.__toasts || []).some(t => t[0].indexOf('覆盖了') >= 0)",
                    timeout=30000)
            except Exception:
                pass
            toasts = pg.evaluate("() => window.__toasts")
            said = " | ".join(t[0] for t in toasts)
            check(any("覆盖了" in t[0] for t in toasts),
                  "the toast says it overwrote rather than added", said)
            after = sorted(os.listdir(want))
            check(after == before, "no second copy appeared in the folder",
                  (before, after))
            bodies = "".join(open(os.path.join(want, n), encoding="utf-8").read()
                             for n in after)
            check("second press" in bodies, "and the file holds the new text")
            doc = json.loads(open(os.path.join(acct, "mods",
                                              "mod-status.json"),
                                  encoding="utf-8").read())
            # Section 4's XS box wrote into the default folder, so two mods is
            # correct; what must not happen is the same one twice.
            listed = [m.get("Path") for m in doc.get("Mods") or []]
            check(listed.count("local//点击测试模组") == 1,
                  "the mod is listed once, not twice", listed)

            shot = os.path.join(HERE, "_tmp", "shot", "lang_after.png")
            os.makedirs(os.path.dirname(shot), exist_ok=True)
            pg.screenshot(path=shot, full_page=True)
            print("wrote", shot)
            b.close()
        print("\nSCRIPT BUTTONS (SHIPPED): %s"
              % ("ALL OK" if not FAILS else "FAILURES ABOVE"))
        return 1 if FAILS else 0
    finally:
        try:
            p.kill()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
