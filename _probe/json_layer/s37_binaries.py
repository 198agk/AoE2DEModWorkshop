import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, re, sys, json, collections

OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

NAMES = [b"AIConsts.json", b"AIResourceTypes.json", b"airesourcetypes.json", b"buttons.json",
         b"civTechTrees.json", b"civilizations.json", b"dropsites.json", b"eras.json",
         b"futuravailableunits.json", b"history.json", b"hotkeys.json", b"linkedTechs.json",
         b"linkedUnits.json", b"maps.json", b"objreplacement.json", b"sharedbuildings.json",
         b"sounds.json", b"unitcategories.json", b"unitlines.json", b"selection_group_def.json",
         b"chronicles_selection_group_def.json", b"adapterblacklist.json", b"adapter_blacklist.json",
         b"paphos_campaign.json", b"peru_campaign.json", b"providence_campaign.json",
         b"paphosfutureavailableunits.json"]

# ---- 1. scan every PE binary in the game tree for these filenames -------
w("=" * 78)
w("1. WHICH BINARY CONTAINS EACH DAT-DIR JSON FILENAME?")
w("=" * 78)
bins = []
for root, dirs, files in os.walk(GAME):
    dirs[:] = [d for d in dirs if d.lower() not in ("backup",)]
    for fn in files:
        if fn.lower().endswith((".exe", ".dll")):
            fp = os.path.join(root, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            if sz > 300000:
                bins.append((fp, sz))
bins.sort(key=lambda x: -x[1])
w("  candidate binaries >=300KB: %d" % len(bins))
for fp, sz in bins[:24]:
    w("     %10d  %s" % (sz, fp))
w("")
w("  MATRIX (X = filename present):")
read = {}
for fp, sz in bins:
    try:
        b = open(fp, "rb").read().lower()
    except Exception:
        continue
    read[fp] = b
hdr = "%-38s" % "filename"
for fp, sz in bins[:24]:
    hdr += " %2s" % os.path.basename(fp)[:2]
w(hdr)
for nm in NAMES:
    row = "%-38s" % nm.decode()
    for fp, sz in bins[:24]:
        b = read.get(fp)
        row += " %2s" % ("X" if b and nm.lower() in b else ".")
    w(row)
w("")
w("  full paths in column order:")
for i, (fp, sz) in enumerate(bins[:24]):
    w("     [%02d] %s" % (i, fp))

# ---- 2. name-construction patterns near the dat dir --------------------
w("")
w("=" * 78)
w("2. NAME-CONSTRUCTION PATTERNS (generic loader)")
w("=" * 78)
exe = read.get(os.path.join(GAME, "AoE2DE_s.exe"), b"")
low = exe
for pat in (b"%s.json", b"_def.json", b"_def", b"resources\\_common\\dat", b"resources\\\\_common\\\\dat",
            b"resources/_common/dat", b"File not found in data set resource: '%s'",
            b"data set resource", b"File System Ready", b"modes\\%s", b"widgetui\\materials.json"):
    w("  %-46r count=%d" % (pat, low.count(pat.lower())))

# ---- 3. genieutils: does any .dat struct model 'linked techs' / 'drop site list'? ---
w("")
w("=" * 78)
w("3. DOES THE SHIPPED TOOL SOURCE MODEL THESE JSON CONCEPTS IN THE .dat?")
w("=" * 78)
SRC = _HERE_PATH("_probe", "source")
needles = ["linkedtech", "linkedunit", "dropsite", "drop_site", "unitline", "unit_line",
           "selection_group", "selectiongroup", "unitcategor", "sharedbuilding", "objectreplacement",
           "objreplacement", "futureavailable", "buttonfile", "command_button", "sound_list",
           "eras", "hotkey", "morematerials", "map_list", "default_map_type"]
srcblob = {}
for root, dirs, files in os.walk(SRC):
    for fn in files:
        fp = os.path.join(root, fn)
        try:
            srcblob[fp] = open(fp, "rb").read().lower()
        except Exception:
            pass
for nd in needles:
    hits = [fp for fp, b in srcblob.items() if nd.encode() in b]
    w("  %-22s files=%d %s" % (nd, len(hits), [os.path.relpath(h, SRC) for h in hits[:4]]))

# ---- 4. genieutils Tech.h / Civ.h enum + field dump -------------------
w("")
w("=" * 78)
w("4. genieutils Tech.h fields (does the .dat hold linked-tech grouping?)")
w("=" * 78)
tp = os.path.join(SRC, "genieutils", "include", "genie", "dat", "Tech.h")
if os.path.exists(tp):
    s = open(tp, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"^\s*(?:int|float|uint|std::vector|std::pair|bool|char)[^;]*;", s, re.M):
        w("     " + m.group(0).strip())

open(os.path.join(OUT, "s37_binaries.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
