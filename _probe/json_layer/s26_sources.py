import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, re, io, json
OUT = _HERE_PATH("_probe", "json_layer")
EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

buf = open(EXE, "rb").read()
low = buf.lower()
w("exe size = %d" % len(buf))

def ctx(off, before=120, after=1200):
    seg = buf[max(0, off - before):off + after]
    out = []
    cur = []
    for b in seg:
        if 32 <= b < 127:
            cur.append(chr(b))
        else:
            if len(cur) >= 4:
                out.append("".join(cur))
            cur = []
    if len(cur) >= 4:
        out.append("".join(cur))
    return out

def occ(needle, ci=True):
    n = needle.lower().encode() if ci else needle.encode()
    return [m.start() for m in re.finditer(re.escape(n), low if ci else buf)]

w("\n#### occurrences of key filenames")
for nm in ["CivTechTrees", "civTechTrees.json", "civtechtrees.json", "futuravailableunits.json",
           "unitlines.json", "linkedTechs.json", "linkedUnits.json", "maps.json", "WRITE_MAP_INFO",
           "PhoenixBuilders", "Source\\Game", "Source/Game"]:
    o = occ(nm)
    w("  %-28s %d  %s" % (nm, len(o), o[:12]))

w("\n#### every Source-path string mentioning TechTree / Civ / Json / DataFile")
pat = re.compile(rb"[A-Za-z]:\\\\?[^\x00]{0,140}?(?:TechTree|Civ|Json|DataFile|Dat)[A-Za-z0-9_\\\\]{0,60}\.(?:cpp|h)")
seen = set()
for m in pat.finditer(buf):
    s = m.group(0).decode("latin-1")
    if s not in seen:
        seen.add(s)
w("  (alt) plain scan of printable runs containing 'Source' and 'TechTree':")
for m in re.finditer(rb"[\x20-\x7e]{12,260}", buf):
    s = m.group(0).decode("latin-1")
    if "Source" in s and ("TechTree" in s or "CivTech" in s or "Json" in s or "JSON" in s or "DataFile" in s):
        if s not in seen:
            seen.add(s)
            w("   @%d  %s" % (m.start(), s))

w("\n#### context around each CivTechTrees occurrence")
for o in occ("CivTechTrees"):
    w("---- @%d" % o)
    for t in ctx(o, 400, 1500):
        w("     %s" % t)

w("\n#### search for writer-ish verbs")
for nm in ["WRITE_", "Export", "SaveJson", "WriteJson", "ToJson", "serialize", "SaveData", "DumpJson",
           "GenerateTechTree", "CivTechTree", "GetCivTechTree", "LoadCivTechTree", "ReadCivTechTree",
           "TechTreePreview", "LoadTechTree", "ReadJson", "ParseJson", "LoadJson", "ReadDataFile"]:
    o = occ(nm)
    w("  %-22s %d  %s" % (nm, len(o), o[:10]))

w("\n#### context around TechTreePreviewPanel / LoadJson-ish")
for nm in ["TechTreePreviewPanel", "LoadJson", "ReadJson"]:
    for o in occ(nm)[:4]:
        w("---- %s @%d" % (nm, o))
        for t in ctx(o, 300, 900):
            w("     %s" % t)

open(os.path.join(OUT, "s26_sources.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:7000])
