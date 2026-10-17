import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, re, io, json
LOGROOT = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
OUT = _HERE_PATH("_probe", "json_layer")
NAMES = ["AIConsts","AIResourceTypes","airesourcetypes","buttons.json","civTechTrees","CivTechTrees",
         "civilizations.json","dropsites.json","eras.json","futuravailableunits","history.json","hotkeys.json",
         "linkedTechs.json","linkedUnits.json","maps.json","objreplacement.json","sharedbuildings.json",
         "sounds.json","unitcategories.json","unitlines.json","selection_group_def","adapterblacklist",
         "adapter_blacklist","morematerials","materials.json","paphosfutureavailableunits","paphos_campaign",
         "peru_campaign","providence_campaign","widgetui"]
rep = io.StringIO()
def w(s=""):
    rep.write(str(s)+"\n")

files = []
for root, dirs, fs in os.walk(LOGROOT):
    if "SlowLog" in root:
        continue
    for f in fs:
        if f.lower().endswith(".txt"):
            files.append(os.path.join(root, f))
files.sort()
w("log files scanned: %d" % len(files))

hits = {}   # name -> list of (file, lineno, text)
totlines = 0
for p in files:
    try:
        raw = open(p, "rb").read()
    except OSError as e:
        w("SKIP %s :: %s" % (p, e)); continue
    txt = raw.decode("utf-8", "replace")
    lines = txt.splitlines()
    totlines += len(lines)
    for i, ln in enumerate(lines, 1):
        low = ln.lower()
        for n in NAMES:
            if n.lower() in low:
                hits.setdefault(n, []).append((os.path.relpath(p, LOGROOT), i, ln.strip()[:400]))
w("total log lines: %d" % totlines)
w()
w("=== HITS PER NAME")
for n in NAMES:
    h = hits.get(n, [])
    w("\n--- %-28s %d hit(s)" % (n, len(h)))
    for (f, i, t) in h[:25]:
        w("    %s:%d  %s" % (f, i, t))
    if len(h) > 25:
        w("    ... +%d more" % (len(h)-25))

w("\n\n=== FULL grep of .json / dataset / loading lines")
pat = re.compile(r"(json|dataset|data set|CivTech|\.dat\b|loaded|loading|failed|missing|mod)", re.I)
shown = 0
for p in files:
    try:
        txt = open(p, "rb").read().decode("utf-8", "replace")
    except OSError:
        continue
    for i, ln in enumerate(txt.splitlines(), 1):
        s = ln.strip()
        if not s:
            continue
        if pat.search(s) and ("json" in s.lower() or "dat" in s.lower() or "civtech" in s.lower()):
            w("  %s:%d  %s" % (os.path.relpath(p, LOGROOT), i, s[:400]))
            shown += 1
w("\nmatched lines: %d" % shown)
open(os.path.join(OUT, "s18_logscan.txt"), "w", encoding="utf-8").write(rep.getvalue())
print("written; bytes=%d" % len(rep.getvalue()))
