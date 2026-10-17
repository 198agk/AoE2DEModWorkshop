import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re, sys, collections, glob, datetime
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
def ts(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")

exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
low = exe.lower()

# ---------- 1. hotkeys: is it an INPUT whose file the game writes? ------
w("=" * 78)
w("1. HOTKEYS: input file vs game-written settings")
w("=" * 78)
hk = json.loads(open(os.path.join(BASE, "hotkeys.json"), "rb").read().decode("utf-8-sig"))
w("  hotkeys.json top keys: %s ; groups=%d/%d" % (list(hk), len(hk["shared_hotkey_group_list"]),
                                                  len(hk["hotkey_group_list"])))
keys = set()
def collect(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(k); collect(v, acc)
    elif isinstance(o, list):
        for v in o:
            collect(v, acc)
collect(hk, keys)
w("  distinct key names in file: %s" % sorted(keys))
w("  all present as literals in exe: %s" % {k: (k.encode() in exe) for k in sorted(keys)})
# does the game write a hotkeys file into the user profile?
hits = []
for root, dirs, files in os.walk(USER):
    for fn in files:
        if fn.lower().endswith((".hkp", ".json", ".ini", ".nfp")) and (
                "hotkey" in fn.lower() or "hotkey" in root.lower()):
            hits.append(os.path.join(root, fn))
w("  user-tree hotkey-ish files: %s" % hits)
w("  exe strings mentioning 'HotKeys': %s" % [m.group(0).decode('latin-1')
    for m in re.finditer(rb"[ -~]*[Hh]ot[Kk]eys?[ -~]*", exe)][:12])

# ---------- 2. .dat redundancy for the small relationship files --------
w("")
w("=" * 78)
w("2. Do linkedUnits / sharedbuildings / unitcategories come from the .dat?")
w("=" * 78)
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
# gather all unit ids + names from civ 1 (British) and all unit headers
allnames = {}
for civ in st["civs"][:3]:
    for u in civ["units"]:
        allnames.setdefault(u["id"], u["name"])
w("  .dat sample unit names (id->name): %s" % dict(list(sorted(allnames.items()))[:8]))
for f in ("linkedUnits.json", "sharedbuildings.json", "unitcategories.json", "objreplacement.json",
          "sounds.json", "buttons.json", "eras.json", "dropsites.json", "unitlines.json",
          "maps.json", "AIConsts.json", "airesourcetypes.json"):
    j = json.loads(open(os.path.join(BASE, f), "rb").read().decode("utf-8-sig"))
    # collect every integer that could be a unit/building/tech id
    ints = set()
    def ci(o):
        if isinstance(o, dict):
            for v in o.values(): ci(v)
        elif isinstance(o, list):
            for v in o: ci(v)
        elif isinstance(o, int) and not isinstance(o, bool):
            ints.add(o)
    ci(j)
    top = list(j)[:6] if isinstance(j, dict) else ["<array>"]
    w("  %-24s top=%s ints=%d ; of these in .dat unit ids=%d" % (
        f, top, len(ints), len(ints & set(allnames))))
w("  NOTE: '.dat unit ids' here = ids seen in 3 sampled civs only; id-space overlap is expected and")
w("        does NOT by itself prove derivation (building ids and unit ids share one numeric space).")

# ---------- 3. objreplacement: the one key missing from exe ------------
w("")
w("=" * 78)
w("3. objreplacement.json key coverage (11/12) - which key is missing?")
w("=" * 78)
oj = json.loads(open(os.path.join(BASE, "objreplacement.json"), "rb").read().decode("utf-8-sig"))
k3 = set()
collect(oj, k3)
for k in sorted(k3):
    if k.encode() not in exe:
        w("  MISSING from exe: %r" % k)
w("  all keys: %s" % sorted(k3))

# ---------- 4. selection_group: content-side test -----------------------
w("")
w("=" * 78)
w("4. selection_group_def.json: content evidence")
w("=" * 78)
sg = json.loads(open(os.path.join(BASE, "selection_group_def.json"), "rb").read().decode("utf-8-sig"))
w("  top keys: %s" % list(sg))
w("  selection_group count=%d ; first 3 names: %s" % (
    len(sg["selection_group"]), [x["name"] for x in sg["selection_group"][:3]]))
w("  radial_data keys: %s" % (list(sg["radial_data"]) if isinstance(sg["radial_data"], dict) else type(sg["radial_data"])))
# do the group names / OBJECT_GROUP_ labels appear in exe?
labels = set()
for g in sg["selection_group"]:
    labels.add(g["name"])
    for it in g.get("item_list", []) or []:
        if isinstance(it, dict) and "label" in it:
            labels.add(it["label"])
n_in = sum(1 for L in labels if L.encode() in exe)
w("  distinct group names + labels = %d ; present as exe strings = %d" % (len(labels), n_in))
for L in sorted(labels)[:14]:
    w("     %-40s %s" % (L, "IN EXE" if L.encode() in exe else "-"))

# ---------- 5. adapterblacklist name mismatch ---------------------------
w("")
w("=" * 78)
w("5. adapterblacklist.json: exe spells it WITH underscore")
w("=" * 78)
w("  exe has 'adapter_blacklist.json' : %s" % (b"adapter_blacklist.json" in exe))
w("  exe has 'adapterblacklist.json'  : %s" % (b"adapterblacklist.json" in exe))
w("  on-disk name                     : adapterblacklist.json  (%d B, %s)"
  % (os.path.getsize(os.path.join(BASE, "adapterblacklist.json")), ts(os.path.join(BASE, "adapterblacklist.json"))))
w("  -> engine looks for a file name that DOES NOT EXIST on disk => shipped file is inert.")

# ---------- 6. airesourcetypes case mismatch ---------------------------
w("")
w("=" * 78)
w("6. airesourcetypes.json case")
w("=" * 78)
for nm in (b"AIResourceTypes.json", b"airesourcetypes.json", b"AIResourceTypes", b"airesourcetypes"):
    w("  exe[%s] = %d" % (nm.decode(), exe.count(nm)))
w("  on-disk: airesourcetypes.json (lowercase, %d B)" % os.path.getsize(os.path.join(BASE, "airesourcetypes.json")))
# filesystem case-insensitivity means this still resolves on Windows.

# ---------- 7. all dat-dir file mtimes, one table -----------------------
w("")
w("=" * 78)
w("7. TIMESTAMPS (batch analysis)")
w("=" * 78)
rows = []
for e in sorted(os.listdir(BASE)):
    fp = os.path.join(BASE, e)
    if os.path.isfile(fp):
        rows.append((e, os.path.getsize(fp), ts(fp)))
rows.sort(key=lambda r: r[2])
for r in rows:
    w("  %-42s %10d  %s" % r)
open(os.path.join(OUT, "s41_verify.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
