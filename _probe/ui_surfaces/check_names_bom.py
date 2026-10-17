import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, json, io

M = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
out = io.StringIO()
w = out.write

w("=== folder name encoding (raw bytes -> decode) ===\n")
for n in sorted(os.listdir(M)):
    b = os.fsencode(n)
    try:
        u = b.decode("utf-8"); e = "utf-8"
    except Exception:
        u = b.decode("latin-1"); e = "NOT-UTF8"
    w("  %-9s %s\n" % (e, u))
    w("            raw=%r\n" % (b,))

w("\n=== info.json first 4 bytes (BOM check) ===\n")
for n in sorted(os.listdir(M)):
    p = os.path.join(M, n, "info.json")
    if os.path.isfile(p):
        r = open(p, "rb").read(4)
        w("  %-62s %r\n" % (n[:62], r))

w("\n=== loose json parse with strict=False ===\n")
for n in sorted(os.listdir(M)):
    p = os.path.join(M, n, "info.json")
    if not os.path.isfile(p):
        continue
    raw = open(p, "rb").read()
    try:
        txt = raw.decode("utf-8-sig")
    except UnicodeDecodeError as ex:
        w("  %-62s DECODE-FAIL %s\n" % (n[:62], ex))
        continue
    try:
        d = json.loads(txt)
        w("  %-62s strict-ok keys=%s\n" % (n[:62], sorted(d.keys())))
    except Exception as ex:
        try:
            d = json.loads(txt, strict=False)
            w("  %-62s need-strict-False but OK keys=%s\n" % (n[:62], sorted(d.keys())))
        except Exception as ex2:
            w("  %-62s FAIL even strict=False: %s\n" % (n[:62], ex2))

w("\n=== other json/txt inside mods that parse-fail ===\n")
for n in sorted(os.listdir(M)):
    root = os.path.join(M, n)
    if not os.path.isdir(root):
        continue
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if not f.lower().endswith(".json"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            raw = open(p, "rb").read()
            try:
                txt = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                w("  %s / %s : NOT-UTF8\n" % (n[:40], rel))
                continue
            try:
                json.loads(txt)
            except Exception as ex:
                w("  %s / %s : %s\n" % (n[:40], rel, ex))

txt = out.getvalue()
io.open(_HERE_PATH("_probe", "ui_surfaces", "names_bom_out.txt"), "w", encoding="utf-8").write(txt)
print(txt)
