"""Independent JSON structural checks for claims 2, 3, 4. stdlib only."""
import hashlib
import json
import os

MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
REL_TREE = r"resources\_common\dat\CivTechTrees\BRITONS.json"
REL_PANEL = r"resources\_common\dat\futuravailableunits.json"

out = []


def p(s=""):
    out.append(s)
    print(s)


def load(p):
    with open(p, "rb") as f:
        b = f.read()
    return b, json.loads(b.decode("utf-8"))


p("### CLAIM 2: BRITONS.json")

tb_m, t_m = load(os.path.join(MOD, REL_TREE))
tb_g, t_g = load(os.path.join(GAME, REL_TREE))
p("  mod  sha256 %s size %d" % (hashlib.sha256(tb_m).hexdigest(), len(tb_m)))
p("  game sha256 %s size %d" % (hashlib.sha256(tb_g).hexdigest(), len(tb_g)))
p("  top-level type: mod=%s game=%s" % (type(t_m).__name__, type(t_g).__name__))
p("  top-level keys mod : %s" % (sorted(t_m) if isinstance(t_m, dict) else "-"))
p("  top-level keys game: %s" % (sorted(t_g) if isinstance(t_g, dict) else "-"))


def nodes(tree):
    """Return list of node dicts wherever the tree stores them."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            if "Node ID" in o:
                found.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tree)
    return found


nm = nodes(t_m)
ng = nodes(t_g)
p("  node count mod=%d game=%d" % (len(nm), len(ng)))
map_m = {n["Node ID"]: n for n in nm}
map_g = {n["Node ID"]: n for n in ng}
added = sorted(set(map_m) - set(map_g))
removed = sorted(set(map_g) - set(map_m))
changed = sorted(k for k in set(map_m) & set(map_g) if map_m[k] != map_g[k])
p("  added Node IDs  : %s" % added)
p("  removed Node IDs: %s" % removed)
p("  field-changed   : %s" % changed)
for k in added:
    p("  ADDED node %s (mod) = %s" % (k, json.dumps(map_m[k], ensure_ascii=False, sort_keys=True)))
    p("  same id in game?  %s" % (k in map_g))
# claim-specific fields
want = {"Node ID": 2550, "Use Type": "Unit", "Age ID": 1, "Building ID": 12}
n = map_m.get(2550)
p("  node 2550 present in MOD:  %s" % (n is not None))
p("  node 2550 present in GAME: %s" % (2550 in map_g))
if n:
    for k, v in want.items():
        p("    field %-12s expected %-6r actual %r  -> %s"
          % (k, v, n.get(k), "OK" if n.get(k) == v else "MISMATCH"))
    p("    full added node = %s" % json.dumps(n, ensure_ascii=False, sort_keys=True))
# any OTHER node difference than 2550?
p("  other diffs besides 2550: added=%s removed=%s changed=%s"
  % ([a for a in added if a != 2550], removed, changed))
# raw text first differing byte offset
off = next((i for i in range(min(len(tb_m), len(tb_g))) if tb_m[i] != tb_g[i]), None)
p("  first differing raw byte offset: %s (mod len %d, game len %d)" % (off, len(tb_m), len(tb_g)))
if off is not None:
    p("    game ctx: %r" % tb_g[off - 40:off + 40])
    p("    mod  ctx: %r" % tb_m[off - 40:off + 40])

p("")
p("### CLAIM 3 + 4: futuravailableunits.json")
pb_m, pj_m = load(os.path.join(MOD, REL_PANEL))
pb_g, pj_g = load(os.path.join(GAME, REL_PANEL))
p("  mod  sha256 %s size %d" % (hashlib.sha256(pb_m).hexdigest(), len(pb_m)))
p("  game sha256 %s size %d" % (hashlib.sha256(pb_g).hexdigest(), len(pb_g)))
p("  top-level type mod=%s game=%s" % (type(pj_m).__name__, type(pj_g).__name__))
p("  mod top-level keys (%d): %s" % (len(pj_m), list(pj_m)[:80] if isinstance(pj_m, dict) else "-"))
p("  game top-level keys (%d): %s" % (len(pj_g), list(pj_g)[:80] if isinstance(pj_g, dict) else "-"))


def flatdiff(a, b, path=""):
    """Yield (path, av, bv) for every leaf-level difference."""
    if type(a) is not type(b):
        yield (path, a, b)
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                yield (path + "/" + str(k), "<absent>", b[k])
            elif k not in b:
                yield (path + "/" + str(k), a[k], "<absent>")
            else:
                yield from flatdiff(a[k], b[k], path + "/" + str(k))
    elif isinstance(a, list):
        if len(a) != len(b):
            yield (path + "/len", len(a), len(b))
        for i in range(min(len(a), len(b))):
            yield from flatdiff(a[i], b[i], path + "/%d" % i)
    else:
        if a != b:
            yield (path, a, b)


diffs = list(flatdiff(pj_g, pj_m))
p("  total leaf/path differences (game -> mod): %d" % len(diffs))
civs_touched = set()
for path, gv, mv in diffs:
    top = path.split("/")[1] if path.startswith("/") and len(path.split("/")) > 1 else path
    civs_touched.add(top)
p("  distinct top-level keys touched: %s" % sorted(civs_touched))
for path, gv, mv in diffs[:40]:
    p("    DIFF %s : game=%r mod=%r" % (path, gv, mv))
if len(diffs) > 40:
    p("    ... (%d more)" % (len(diffs) - 40))

# claim 3 specifics: find Britons key
bkey = None
for k in pj_g:
    if k == "Britons":
        bkey = k
        break
p("  panel key 'Britons' present: game=%s mod=%s" % ("Britons" in pj_g, "Britons" in pj_m))


def find_unit_entries(obj, unit_id):
    """Find every dict with ID==unit_id inside a Units list, return (path, dict, parent)."""
    hits = []

    def walk(o, path):
        if isinstance(o, dict):
            if o.get("ID") == unit_id and ("Name" in o or "RequiredAge" in o):
                hits.append((path, o))
            for k, v in o.items():
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + "/%d" % i)
    walk(obj, "")
    return hits


for tag, j in (("GAME", pj_g), ("MOD", pj_m)):
    hits = find_unit_entries(j.get("Britons"), 74)
    p("  %s Britons: entries with ID 74: %d" % (tag, len(hits)))
    for path, d in hits:
        p("    path=%s  value=%s" % (path, json.dumps(d, ensure_ascii=False, sort_keys=True)))

# building 12 context in game Britons
p("  -- GAME Britons structure around ID 74 --")
br_g = pj_g.get("Britons")
br_m = pj_m.get("Britons")


def summarize(obj, label):
    p("  %s Britons type=%s" % (label, type(obj).__name__))
    if isinstance(obj, dict):
        p("    keys: %s" % list(obj)[:30])
    if isinstance(obj, list):
        for i, e in enumerate(obj):
            if isinstance(e, dict):
                p("    [%d] keys=%s  bID=%r bName=%r nUnits=%s"
                  % (i, list(e)[:12], e.get("ID"), e.get("Name"),
                     len(e.get("Units", [])) if isinstance(e.get("Units"), list) else "-"))


summarize(br_g, "GAME")
summarize(br_m, "MOD")

# claim 3 second half: every other civ that shipped (Britons,74) still has it
ships_g, ships_m, still = [], [], []
for k in pj_g:
    if find_unit_entries(pj_g[k], 74):
        ships_g.append(k)
    if find_unit_entries(pj_m.get(k, {}), 74):
        ships_m.append(k)
p("  civs shipping unit 74 in GAME: %d %s" % (len(ships_g), ships_g))
p("  civs shipping unit 74 in MOD : %d %s" % (len(ships_m), ships_m))
p("  GAME-shipping but MOD-missing: %s" % sorted(set(ships_g) - set(ships_m)))
p("  MOD-shipping but GAME-missing: %s" % sorted(set(ships_m) - set(ships_g)))

# find RequiredAge/Building for 74 in game Britons
def building_of(obj, unit_id):
    res = []

    def walk(o):
        if isinstance(o, dict):
            us = o.get("Units")
            if isinstance(us, list) and any(isinstance(u, dict) and u.get("ID") == unit_id for u in us):
                res.append({kk: vv for kk, vv in o.items() if kk != "Units"})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return res


p("  GAME Britons: containers holding unit 74 -> %s"
  % json.dumps(building_of(br_g, 74), ensure_ascii=False))
p("  MOD  Britons: containers holding unit 74 -> %s"
  % json.dumps(building_of(br_m, 74), ensure_ascii=False))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "v4_out.txt"), "w",
          encoding="utf-8") as f:
    f.write("\n".join(out))
