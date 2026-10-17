import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re, glob, collections
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
CTT = os.path.join(BASE, "CivTechTrees")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

# ---------- A. which string files hold the 405xxx / 407xxx ids ----------
w("=" * 74)
w("A. Where do the `true mismatch` string ids live?  (all 17 languages + paphos)")
w("=" * 74)
langs = sorted(os.listdir(os.path.join(GAME, "resources")))
w("  resources/ subdirs: %s" % langs)
need = [405028, 405027, 405052, 407132, 414055, 407084, 4201, 120150]
tables = {}
for lg in langs:
    d = os.path.join(GAME, "resources", lg, "strings", "key-value")
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        p = os.path.join(d, fn)
        t = {}
        for line in open(p, "rb").read().decode("utf-8-sig", errors="replace").splitlines():
            if not line.strip() or line.lstrip().startswith("//"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                t[int(parts[0])] = parts[1].strip().strip('"')
        tables[lg + "/" + fn] = t
        if lg == "en":
            pass
w("  loaded %d string tables, sizes: %s" % (len(tables), {k: len(v) for k, v in list(tables.items())[:4]}))
for sid in need:
    who = [(k, v[sid]) for k, v in tables.items() if sid in v]
    w("  sid=%-7d found in %2d table(s): %s" % (sid, len(who), who[:3]))

# recompute true mismatch with ALL english-ish tables pooled
pool = {}
for k, v in tables.items():
    if k.startswith("en/") or "paphos" in k or "modded" in k:
        for i, s in v.items():
            pool.setdefault(i, s)
w("  pooled (en + modded + paphos) table has %d ids" % len(pool))
def norm(s):
    return re.sub(r"\s+", " ", s.replace("\\n", " ")).strip().lower()
tot = soft = notfound = 0
real = []
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for lst in ("civ_techs_buildings", "civ_techs_units"):
        for nd in d[lst]:
            nm, sid = nd.get("Name"), nd.get("Name String ID")
            if nm is None or sid is None:
                continue
            tot += 1
            s = pool.get(sid)
            if s is None:
                notfound += 1
                continue
            if s == nm:
                continue
            if norm(s) == norm(nm):
                soft += 1
            else:
                real.append((os.path.basename(fp), lst, sid, nm, s))
w("  POOLED: total=%d  exact=%d  soft-break-only=%d  id-not-in-pool=%d  TRUE-text-mismatch=%d"
  % (tot, tot - soft - notfound - len(real), soft, notfound, len(real)))
w("  true mismatch per civ: %s" % dict(collections.Counter(r[0] for r in real)))
for r in real[:40]:
    w("     %-16s %-19s sid=%-7d Name=%-32r pool=%r" % r)

# ---------- B. Pompeii monolithic civTechTrees.json vs per-civ files, same civ ----------
w("")
w("=" * 74)
w("B. Pompeii `civTechTrees.json` vs `CivTechTrees/*.json` for the SAME civ")
w("=" * 74)
POM = os.path.join(GAME, "modes", "Pompeii", "resources", "_common", "dat")
mono = json.loads(open(os.path.join(POM, "civTechTrees.json"), "rb").read().decode("utf-8-sig"))
w("  mono top keys: %s ; civs: %d" % (list(mono.keys()), len(mono["civs"])))
w("  mono civ_ids: %s" % [c["civ_id"] for c in mono["civs"]])
byciv = {c["civ_id"]: c for c in mono["civs"]}
pdir = os.path.join(POM, "CivTechTrees")
for fn in sorted(os.listdir(pdir)):
    civ = fn[:-5].upper()
    a = json.loads(open(os.path.join(pdir, fn), "rb").read().decode("utf-8-sig"))
    b = byciv.get(civ)
    if not b:
        w("  %-16s per-civ only (civ_id=%s) mono has no entry" % (fn, a.get("civ_id")))
        continue
    w("  %-16s per-civ b/u=%d/%d  mono b/u=%d/%d  same_keys=%s" % (
        fn, len(a["civ_techs_buildings"]), len(a["civ_techs_units"]),
        len(b["civ_techs_buildings"]), len(b["civ_techs_units"]),
        set(a) == set(b)))
    ka = set(); kb = set()
    for lst in ("civ_techs_buildings", "civ_techs_units"):
        for n in a[lst]: ka |= set(n)
        for n in b[lst]: kb |= set(n)
    w("      per-civ keys: %s" % sorted(ka))
    w("      mono    keys: %s" % sorted(kb))
    w("      mono-ONLY: %s   per-civ-ONLY: %s" % (sorted(kb - ka), sorted(ka - kb)))
    # node-level equality on shared fields
    for lst in ("civ_techs_buildings", "civ_techs_units"):
        na = {n.get("Node ID"): n for n in a[lst] if "Node ID" in n}
        nb = {n.get("Node ID"): n for n in b[lst] if "Node ID" in n}
        shared = set(na) & set(nb)
        diff = 0
        for k in shared:
            if na[k].get("Node Status") != nb[k].get("Node Status"):
                diff += 1
        w("      %-19s shared NodeIDs=%d  a-only=%d b-only=%d  NodeStatus differs on %d" % (
            lst, len(shared), len(set(na) - set(nb)), len(set(nb) - set(na)), diff))
    break

# ---------- C. futuravailableunits redundancy vs .dat tech tree ----------
w("")
w("=" * 74)
w("C. futuravailableunits.json vs the .dat: is the content derivable?")
w("=" * 74)
fu = json.loads(open(os.path.join(BASE, "futuravailableunits.json"), "rb").read().decode("utf-8-sig"))
w("  top-level civ keys: %d" % len(fu))
w("  key sample: %s" % list(fu)[:8])
civkey = next(k for k in fu if fu[k].get("Buildings"))
civ = fu[civkey]
w("  using civ key %r  entry keys: %s" % (civkey, list(civ.keys())))
w("  buildings: %d" % len(civ["Buildings"]))
b0 = civ["Buildings"][0]
w("  first building verbatim: %s" % json.dumps(b0)[:400])
nunits = sum(len(b.get("Units", [])) for b in civ["Buildings"])
ntechs = sum(len(b.get("Techs", [])) for b in civ["Buildings"])
w("  total Units across buildings=%d  Techs=%d" % (nunits, ntechs))
allkeys = set()
for b in civ["Buildings"]:
    allkeys |= set(b)
    for u in b.get("Units", []): allkeys |= set(u)
    for t in b.get("Techs", []): allkeys |= set(t)
w("  all key paths: %s" % sorted(allkeys))

open(os.path.join(OUT, "s32_synth.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
