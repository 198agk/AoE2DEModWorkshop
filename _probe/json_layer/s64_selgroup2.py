import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, re
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
low = exe.lower()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=== CASE-INSENSITIVE search for selection-group / radial naming ===")
for n in ("selection_group", "selectiongroup", "radial_data", "radialdata", "group_def", "groupdef",
          "rgid", "is_building", "isbuilding", "chronicles", "paphosfuture", "paphos_campaign", "futureavailable"):
    w("  %-22s count=%d" % (n, low.count(n.lower().encode())))
w("")
w("=== where does '%s.json' occur (standalone) ? ===")
for m in re.finditer(rb"%s\.json", exe):
    lo, hi = max(0, m.start() - 300), min(len(exe), m.start() + 300)
    w("  @%d" % m.start())
    for mm in re.finditer(rb"[\x20-\x7e]{4,}", exe[lo:hi]):
        w("      %8d  %s" % (lo + mm.start(), mm.group(0).decode("latin-1")))
w("")
w("=== where does 'chronicles' occur? ===")
for m in list(re.finditer(b"hronicles", exe))[:20]:
    lo, hi = max(0, m.start() - 120), min(len(exe), m.start() + 160)
    w("  @%d  %r" % (m.start(), exe[lo:hi]))
open(os.path.join(OUT, "s64_selgroup2.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:9000])
