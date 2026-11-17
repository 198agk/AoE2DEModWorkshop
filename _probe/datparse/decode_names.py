import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Decode mod-authored Chinese strings: what encoding does the .dat actually store?"""
import os, sys, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

MODS = GP.SUBSCRIBED
D10 = [os.path.join(MODS, n) for n in os.listdir(MODS) if n.startswith("550749")][0]
M10 = os.path.join(D10, "resources", "_common", "dat", "empires2_x2_p1.dat")

data, _ = P.load_dat(M10)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
em = p.stats["effects"]

samples = [em[i]["name"] for i in (4987, 5535, 5066, 5100, 5103, 5104, 4998, 4991)
           if i < len(em) and em[i]["name"]]

print("=== encoding probe on mod-authored names ===")
for s in samples:
    raw = s.encode("latin-1", errors="replace")
    out = []
    for enc in ("gbk", "gb18030", "utf-8", "big5"):
        try:
            out.append("%s=%s" % (enc, raw.decode(enc)))
        except Exception as e:
            out.append("%s=<fail>" % enc)
    print("  %-30r" % s)
    for o in out:
        print("       ", o)

print("\n=== decoded key mod effects (gb18030) ===")
def dec(s):
    try:
        return s.encode("latin-1").decode("gb18030")
    except Exception:
        return s
for i in (4987, 5535, 5066, 5100, 5103, 5104, 4998, 4991, 4992, 4999, 5534):
    if i < len(em):
        print("  eff[%d] %-12s %s" % (i, repr(em[i]["name"])[:12], dec(em[i]["name"])))
