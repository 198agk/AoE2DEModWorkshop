import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, sys, collections, glob
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# ---------- 1. complete dat-dir file inventory -------------------------
w("=" * 78)
w("1. COMPLETE INVENTORY of resources\\_common\\dat\\")
w("=" * 78)
allf = []
for e in sorted(os.listdir(BASE)):
    fp = os.path.join(BASE, e)
    if os.path.isfile(fp):
        allf.append((e, os.path.getsize(fp), "f"))
    else:
        n = len(os.listdir(fp))
        tot = sum(os.path.getsize(os.path.join(fp, x)) for x in os.listdir(fp))
        allf.append((e + "\\", tot, "d(%d)" % n))
ext = collections.Counter(os.path.splitext(a[0])[1].lower() for a in allf)
w("  total entries=%d ; by ext=%s" % (len(allf), dict(ext)))
for a in allf:
    w("     %-46s %10d  %s" % (a[0], a[1], a[2]))

# ---------- 2. futuravailableunits: fields absent from .dat -----------
w("")
w("=" * 78)
w("2. futuravailableunits.json: which fields CANNOT come from the .dat?")
w("=" * 78)
fu = json.loads(open(os.path.join(BASE, "futuravailableunits.json"), "rb").read().decode("utf-8-sig"))
fielduse = collections.Counter()
unitfields = collections.Counter()
for civ, v in fu.items():
    for b in v.get("Buildings", []):
        fielduse[("building", tuple(sorted(b.keys())))] += 1
        for u in b.get("Units", []):
            unitfields[tuple(sorted(u.keys()))] += 1
        for t in b.get("Techs", []):
            unitfields[("TECH:" + str(t) if not isinstance(t, dict) else "TECH:" + str(tuple(sorted(t.keys()))))] += 1
w("  building key shapes:")
for k in sorted(fielduse, key=str):
    w("     %-70s %d" % (str(k[1]), fielduse[k]))
w("  leaf key shapes (units + techs):")
for k in sorted(unitfields, key=str):
    w("     %-70s %d" % (str(k), unitfields[k]))
# do RequiredTechID / RequiredUnitID / PrereqStringID / PrereqStyle appear?
for probe in ("RequiredTechID", "RequiredUnitID", "PrereqStringID", "PrereqStyle",
              "PrereqTech", "RequiredAge", "PrereqIconSet", "PrereqIconIndex"):
    n = sum(1 for civ in fu.values() for b in civ.get("Buildings", [])
            for u in b.get("Units", []) if probe in u)
    w("  field %-16s occurrences=%d" % (probe, n))
# sample a unit with RequiredUnitID
for civ, v in fu.items():
    for b in v.get("Buildings", []):
        for u in b.get("Units", []):
            if "RequiredUnitID" in u or "RequiredTechID" in u:
                w("  sample with Required*ID: civ=%s %s" % (civ, json.dumps(u, ensure_ascii=False)))
                break
        else:
            continue
        break
    else:
        continue
    break
# .dat has no 'prereq icon' concept: check genieutils for it
src = _HERE_PATH("_probe", "source")
hits = {}
for needle in ("PrereqIconSet", "PrereqIconIndex", "PrereqStringID", "PrereqStyle",
               "RequiredTechID", "RequiredUnitID", "futuravailable", "FutureAvailable"):
    c = 0
    for root, dirs, files in os.walk(src):
        for fn in files:
            try:
                if needle.lower() in open(os.path.join(root, fn), "rb").read().lower():
                    c += 1
            except Exception:
                pass
    hits[needle] = c
w("  occurrences of these fields in shipped tool source (AGE+genieutils): %s" % hits)

# ---------- 3. mod linkedTechs invented entry vs mod .dat ------------
w("")
w("=" * 78)
w("3. mod 550749: linkedTechs.json invented entry vs its own .dat tech list")
w("=" * 78)
mp = os.path.join(MODS, "550749_{2026}10倍资源文明联盟2倍科技 北欧dlc可用 v48",
                  "resources", "_common", "dat")
lt = json.loads(open(os.path.join(mp, "linkedTechs.json"), "rb").read().decode("utf-8-sig"))
w("  mod linkedTechs entries=%d" % len(lt["LinkedTechs"]))
for e in lt["LinkedTechs"]:
    w("     %s" % json.dumps(e, ensure_ascii=False))
mdat = os.path.join(mp, "empires2_x2_p1.dat")
data, how = P.load_dat(mdat)
p = P.Parser(data); st = p.parse()
w("  mod .dat stats: civs=%s techs=%s unit_headers=%s" % (st.get("civ_count"), st.get("tech_count"), st.get("unit_header_count")))
w("  -> referencing tech ids 4666..4670 requires the mod's own .dat to define them")
ids = set()
w("  base .dat tech_count=%s" % 1510)

# ---------- 4. base linkedTechs: do its Techs exist in base .dat? ----
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
w("")
lt = json.loads(open(os.path.join(BASE, "linkedTechs.json"), "rb").read().decode("utf-8-sig"))
w("  BASE linkedTechs.json: %d entries" % len(lt["LinkedTechs"]))
w("  base .dat tech records = %s (count only exposed)" % st.get("tech_count"))
w("  base file entries:")
for e in lt["LinkedTechs"]:
    w("     %s" % json.dumps(e, ensure_ascii=False))
w("  base NameId range: %s" % sorted(e["NameId"] for e in lt["LinkedTechs"]))

# ---------- 5. selection_group_def: does any other engine name exist? -
w("")
w("=" * 78)
w("5. selection_group_def naming evidence")
w("=" * 78)
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
low = exe.lower()
for needle in ("selection_group_def", "selection_group", "selectiongroup",
               "chronicles_selection_group_def", "radial_data", "item_list",
               "role_settings", "selection_group.json"):
    w("  exe[%s] = %d" % (needle, low.count(needle.lower().encode())))
# what filenames appear near 'selection'
import re
for m in re.finditer(rb"selection[a-z_]*", low[:]):
    pass
w("  sample of exe strings containing 'selection':")
seen = set()
for m in re.finditer(rb"[ -~]{6,90}", exe):
    s = m.group(0)
    if b"election" in s and s not in seen:
        seen.add(s)
        if len(seen) <= 30:
            w("     @%d %r" % (m.start(), s.decode("latin-1")))
open(os.path.join(OUT, "s36_final.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:12000])
