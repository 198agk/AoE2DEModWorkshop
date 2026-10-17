import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=" * 90)
w("S. maps.json neighbourhood in detail (the 'exported from phoenix' hint)")
w("=" * 90)
lo, hi = 53262400, 53263800
for m in re.finditer(rb"[ -~]{4,}", exe[lo:hi]):
    w("  %8d  %s" % (lo + m.start(), m.group(0).decode("latin-1")))

w("")
w("=" * 90)
w("T. is there a maps.txt on disk?  (the hinted export target)")
w("=" * 90)
for root, dirs, files in os.walk(GAME):
    for fn in files:
        if fn.lower() in ("maps.txt",):
            fp = os.path.join(root, fn)
            w("  %s  %d B" % (os.path.relpath(fp, GAME), os.path.getsize(fp)))
            w("     first 300: %r" % open(fp, "rb").read()[:300])

w("")
w("=" * 90)
w("U. Writer hints: 'phoenix' / WRITE_ / EXPORT command strings in exe")
w("=" * 90)
for pat in (b"WRITE_MAP_INFO", b"WRITE_", b"phoenix", b"Phoenix", b"EXPORT_", b"GENERATE_"):
    offs = [m.start() for m in re.finditer(re.escape(pat), exe)]
    w("  %-16s count=%d offsets=%s" % (pat.decode(), len(offs), offs[:10]))

w("")
w("=" * 90)
w("V. User-profile scratch: does the game ever WRITE a JSON that looks like ours?")
w("=" * 90)
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
cnt = 0
for root, dirs, files in os.walk(USER):
    for fn in files:
        if fn.endswith(".json"):
            fp = os.path.join(root, fn)
            cnt += 1
            if cnt <= 25:
                w("  %-100s %8d B" % (os.path.relpath(fp, USER), os.path.getsize(fp)))
w("  total .json in user tree = %d" % cnt)

w("")
w("=" * 90)
w("W. Do sounds.json 'name' values exist in the shipped .bnk audio banks?")
w("=" * 90)
banks = []
for root, dirs, files in os.walk(GAME):
    for fn in files:
        if fn.lower().endswith(".bnk"):
            banks.append(os.path.join(root, fn))
w("  .bnk files: %d" % len(banks))
sj = json.loads(open(os.path.join(BASE, "sounds.json"), "rb").read().decode("utf-8-sig"))["sound_list"]
names = [e["name"] for e in sj]
hit = 0
for b in banks[:12]:
    d = open(b, "rb").read()
    for n in names:
        if n.encode() in d:
            hit += 1
            w("     %s found in %s" % (n, os.path.relpath(b, GAME)))
            break
w("  names found in scanned banks: %d" % hit)

w("")
w("=" * 90)
w("X. Second-method cross-check summary table")
w("=" * 90)
fau = json.loads(open(os.path.join(BASE, "futuravailableunits.json"), "rb").read().decode("utf-8-sig"))
w("  futuravailableunits: widgetui pointer file says moved to resources/_common/dat/  [V]")
w("  CivTechTrees: exe parse site w/ bounds errors + 3-value Node Status absent from .dat  [V]")
w("  linkedTechs: real mod ships a modified copy -> override works  [V]")
w("  civilizations: real mod ships a modified copy (43,485 B, -1 field, swapped tech ids)  [V]")
open(os.path.join(OUT, "s48_final3.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
