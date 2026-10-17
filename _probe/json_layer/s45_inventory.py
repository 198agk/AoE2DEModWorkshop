import os, io, json, re, hashlib
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def topkeys(o):
    if isinstance(o, dict): return list(o)[:4]
    if isinstance(o, list): return ["<array len=%d>" % len(o)]
    return [type(o).__name__]

w("=" * 100)
w("COMPLETE INVENTORY OF %s" % BASE)
w("=" * 100)
root_json, sub_all = [], []
for e in sorted(os.listdir(BASE)):
    fp = os.path.join(BASE, e)
    if os.path.isdir(fp):
        w("DIR  %-24s (%d files)" % (e, len(os.listdir(fp))))
        continue
    if e.lower().endswith(".json"):
        root_json.append(e)
        try:
            j = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
            tk = topkeys(j)
            nd = None
            if isinstance(j, dict) and all(isinstance(v, list) for v in j.values()):
                nd = {k: len(v) for k, v in j.items()}
        except Exception as ex:
            tk = ["<parse error: %s>" % ex]; nd = None
        w("  %-38s %9d B  exe=%-5s  keys=%s %s" % (
            e, os.path.getsize(fp), e.encode() in exe,
            json.dumps(tk, ensure_ascii=False)[:90], nd or ""))
    else:
        w("  %-38s %9d B  (non-json)" % (e, os.path.getsize(fp)))
w("")
w("root .json count = %d" % len(root_json))
sub = os.path.join(BASE, "CivTechTrees")
w("CivTechTrees\\ .json count = %d" % len([f for f in os.listdir(sub) if f.endswith(".json")]))
w("TOTAL .json = %d" % (len(root_json) + len([f for f in os.listdir(sub) if f.endswith('.json')])))

w("")
w("=" * 100)
w("VERDICT TABLE SOURCE: does each file have a CONTIGUOUS key-literal parse site in the exe?")
w("=" * 100)
def keyset(o, acc=None):
    if acc is None: acc = set()
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(k); keyset(v, acc)
    elif isinstance(o, list):
        for v in o: keyset(v, acc)
    return acc

def maxrun(fp):
    j = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    ks = sorted(k for k in keyset(j) if len(k) >= 4 and re.match(r"^[A-Za-z_][A-Za-z0-9_ ]*$", k))
    offs = []
    for k in ks:
        m = re.search(re.escape(k.encode()), exe)
        if m: offs.append((m.start(), k))
    offs.sort()
    best, cur = 0, 1
    for i in range(1, len(offs)):
        if offs[i][0] - offs[i-1][0] <= 600:
            cur += 1; best = max(best, cur)
        else:
            cur = 1
    missing = [k for k in ks if k.encode() not in exe]
    return len(ks), len(ks) - len(missing), best, missing

for e in root_json:
    try:
        nk, npresent, mr, miss = maxrun(os.path.join(BASE, e))
        w("  %-38s keys=%-3d present=%-3d maxrun=%-3d missing=%s" % (
            e, nk, npresent, mr, json.dumps(miss, ensure_ascii=False)[:100]))
    except Exception as ex:
        w("  %-38s ERROR %s" % (e, ex))
open(os.path.join(OUT, "s45_inventory.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
