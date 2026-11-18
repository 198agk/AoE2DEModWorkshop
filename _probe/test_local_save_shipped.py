"""Does the SHIPPED program really put a generated script into a local mod?

Reported 2026-11-10: 「这个生成的东西应该放local去」.  The three boxes on the script
screen could write a rule, and could save it back into a file that already
existed -- and every file they could reach was either one of the game's 53 shipped
`.per` files or a nearly empty profile copy, so what the screen generated had no
home.  It goes to `mods/local/<mod>/resources/_common/<ai|xs>/` now, with an
`info.json` and a `mod-status.json` entry so the game lists and loads it.

This probe starts the exe in the DELIVERY folder -- not the dev server -- and
drives the route over HTTP, because "the source does it" is not the thing the
player opens.  The profile it writes into is a temp fixture handed to the route
as `profile_root`: the real profile is never touched, and the fixture is built in
the game's own shape (`<profile>/<account>/mods/local`) because `pick_account`
only accepts an account that owns a `mods` folder.
"""
import json
import _gamepaths as GP
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _paths as P

FAILS = []


def check(ok, what, detail=""):
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", what,
                           "" if ok or not detail else " :: %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def free_port(start=7841):
    for port in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
        finally:
            s.close()
    raise SystemExit("no free port")


def call(port, path, payload=None, timeout=60):
    url = "http://127.0.0.1:%d%s" % (port, path)
    if payload is None:
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    exe = os.path.join(P.BUNDLE, "AoE2 DE Mod Workshop.exe")
    if not os.path.isfile(exe):
        print("REFUSING: no exe in the bundle at", exe)
        return 1
    port = free_port()
    subprocess.run(["taskkill", "/IM", "AoE2 DE Mod Workshop.exe", "/F"],
                   capture_output=True)
    p = subprocess.Popen([exe, "--port", str(port)], cwd=P.BUNDLE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tmp = tempfile.mkdtemp(prefix="aoe2_local_shipped_")
    try:
        ready = False
        for _ in range(240):
            if p.poll() is not None:
                break
            try:
                call(port, "/api/meta", timeout=3)
                ready = True
                break
            except Exception:
                time.sleep(0.5)
        if not ready:
            out = b""
            try:
                p.kill()
                out = p.stdout.read() or b""
            except Exception:
                pass
            print("REFUSING: the shipped program never answered on", port)
            print(out.decode("utf-8", "replace")[:2000])
            return 1
        print("checking the SHIPPED program on port %d" % port)

        root = os.path.join(tmp, "prof")
        acct = os.path.join(root, GP.STEAMID)
        os.makedirs(os.path.join(acct, "mods", "local"))
        os.makedirs(os.path.join(acct, "mods", "subscribed"))
        for sub in ("ai", "xs"):
            os.makedirs(os.path.join(acct, "resources", "_common", sub))

        print("\n1  the route puts the generated script into a local mod")
        r = call(port, "/api/script-local-save",
                 {"dept": "ai",
                  "text": "(defrule\n\t(true)\n=>\n\t(chat-to-all \"hi\")\n)\n",
                  "name": "我的AI", "profile_root": root})
        check(r.get("ok") is True, "the route says ok", r)
        want = os.path.join(acct, "mods", "local", "模组工坊脚本",
                            "resources", "_common", "ai", "我的AI.per")
        check(os.path.isfile(want), "the .per is on disk inside mods/local", r.get("path"))
        check(r.get("rel") == "resources/_common/ai/我的AI.per",
              "and the reply names the path inside the mod", r.get("rel"))
        body = ""
        if os.path.isfile(want):
            body = open(want, encoding="utf-8").read()
        check("chat-to-all" in body, "with the script that was sent", body[:40])
        check("\r" not in body, "written with \\n endings, not \\r\\n")
        info = os.path.join(acct, "mods", "local", "模组工坊脚本", "info.json")
        check(os.path.isfile(info), "the mod folder got an info.json")
        doc = {}
        st = os.path.join(acct, "mods", "mod-status.json")
        if os.path.isfile(st):
            doc = json.loads(open(st, encoding="utf-8").read())
        names = [m.get("Path") for m in doc.get("Mods") or []]
        check("local//模组工坊脚本" in names,
              "and an entry, so the game can enable it", names)
        check(all(m.get("Enabled") is True for m in doc.get("Mods") or []),
              "the entry is enabled without the player doing anything")

        print("\n2  the chooser offers it back, first")
        g = call(port, "/api/script-files?dept=ai&profile_root="
                 + urllib.parse.quote(root))
        files = g.get("files") or []
        check(bool(files) and files[0].get("scope") == "mod",
              "the local mod sorts first", [f.get("scope") for f in files[:3]])
        mine = [f for f in files if f.get("scope") == "mod"]
        check([f.get("rel") for f in mine] == ["我的AI.per"],
              "and it is the file just written", [f.get("rel") for f in mine])
        rd = call(port, "/api/script-read?path=" + urllib.parse.quote(want)
                  + "&profile_root=" + urllib.parse.quote(root))
        check(rd.get("ok") and "chat-to-all" in (rd.get("text") or ""),
              "reading it back goes through the same guard", rd.get("error"))

        print("\n3  the XS box writes .xs, the whole-script box writes .per")
        r2 = call(port, "/api/script-local-save",
                  {"dept": "xs", "text": "void main() {\n}\n", "name": "我的XS",
                   "profile_root": root})
        check(r2.get("ok") is True
              and r2.get("rel") == "resources/_common/xs/我的XS.xs",
              "an .xs lands in resources/_common/xs", r2.get("rel"))
        check(r2.get("info_created") is False,
              "the folder's existing info.json is left alone")
        r3 = call(port, "/api/script-local-save",
                  {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n)\n",
                   "name": "整份", "mod": "另一个模组", "profile_root": root})
        check(r3.get("ok") is True and r3.get("mod") == "另一个模组",
              "a mod name from the box is honoured", r3.get("mod"))
        check(r3.get("replaced") is False,
              "and a fresh mod folder is a create, not an overwrite",
              r3.get("replaced"))

        print("\n4  pressing it twice updates the same file")
        # Asked 2026-11-10: 「就像编辑器那些存的一样，默认放 local/mods 里自建一个，后续
        # 改动也按原文件名一样就覆盖」.  The editor remembers its Title; this screen
        # has to remember the file it wrote, or a second press stacks `我的AI (2)`.
        first = call(port, "/api/script-local-save",
                     {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n)\n",
                      "name": "覆盖测试", "profile_root": root, "screen": "ai"})
        check(first.get("ok") is True and first.get("replaced") is False,
              "the first press writes a new file", first.get("replaced"))
        second = call(port, "/api/script-local-save",
                      {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n\t(chat-to-all \"2\")\n)\n",
                       "profile_root": root, "screen": "ai"})
        check(second.get("ok") is True, "the second press (empty name box) is accepted",
              second.get("error"))
        check(second.get("replaced") is True, "and it reports an overwrite",
              second.get("replaced"))
        check(second.get("path") == first.get("path"),
              "onto the very same path", (first.get("path"), second.get("path")))
        folder = os.path.dirname(first.get("path") or "")
        # Section 1 already wrote 我的AI.per into this same folder, so "one file"
        # means "one file per name": pressing twice adds nothing new.
        check(sorted(os.listdir(folder)) == ["我的AI.per", "覆盖测试.per"],
              "so a second press adds no second copy", sorted(os.listdir(folder)))
        check("chat-to-all" in open(second.get("path"), encoding="utf-8").read(),
              "with the new text in it")
        # A different screen keeps its own memory: the whole-script box must not
        # inherit the name the AI box just used, and vice versa.
        plan = call(port, "/api/script-local-save",
                    {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n)\n",
                     "name": "整份脚本", "profile_root": root, "screen": "plan"})
        check(plan.get("path") != second.get("path"),
              "another screen writes its own file first", plan.get("path"))
        plan2 = call(port, "/api/script-local-save",
                     {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n)\n",
                      "profile_root": root, "screen": "plan"})
        check(plan2.get("replaced") is True and plan2.get("path") == plan.get("path"),
              "and then updates it, not the AI box's file", plan2.get("path"))
        # A path the screen hands back (the file it has open) is the target.
        named = call(port, "/api/script-local-save",
                     {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n)\n",
                      "path": first.get("path"), "profile_root": root,
                      "screen": "ai"})
        check(named.get("replaced") is True and named.get("path") == first.get("path"),
              "a path from the chooser steers the save onto that file",
              (named.get("path"), named.get("replaced")))

        print("\n5  nothing else became writable")
        loose = os.path.join(tmp, "loose.per")
        bad = call(port, "/api/script-write",
                   {"path": loose, "text": "(defrule\n\t(true)\n=>\n)\n"})
        check(bad.get("ok") is False and ("ai/" in (bad.get("error") or "")
                                          or "xs/" in (bad.get("error") or "")),
              "a path outside every script folder is still refused",
              bad.get("error"))
        check(not os.path.exists(loose), "and nothing was created there")
        ext = call(port, "/api/script-local-save",
                   {"dept": "txt", "text": "x", "profile_root": root})
        check(ext.get("ok") is False, "an unknown department is refused",
              ext.get("error"))
        empty = call(port, "/api/script-local-save",
                     {"dept": "ai", "text": "   ", "profile_root": root})
        check(empty.get("ok") is False and "空" in (empty.get("error") or ""),
              "an empty box is refused in Chinese", empty.get("error"))
        escape = call(port, "/api/script-local-save",
                      {"dept": "ai", "text": "(defrule\n\t(true)\n=>\n)\n",
                       "name": "../../x", "mod": "../../x",
                       "profile_root": root})
        base = os.path.normcase(os.path.join(acct, "mods", "local"))
        here = os.path.normcase(os.path.abspath(escape.get("mod_dir") or ""))
        check(escape.get("ok") is True and here.startswith(base + os.sep),
              "a name with .. in it cannot leave mods/local", escape.get("mod_dir"))
        print("\nSCRIPT LOCAL SAVE (SHIPPED): %s"
              % ("ALL OK" if not FAILS else "FAILURES ABOVE"))
        return 1 if FAILS else 0
    finally:
        try:
            p.kill()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
