import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, re, json, collections

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
OUT = _HERE_PATH("_probe", "json_layer")
buf = open(EXE, "rb").read()
low = buf.lower()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def keypaths(o, prefix="", acc=None, depth=0):
    if acc is None:
        acc = collections.Counter()
    if depth > 6:
        return acc
    if isinstance(o, dict):
        for k, v in o.items():
            acc[str(k)] += 1
            keypaths(v, prefix + "." + str(k), acc, depth + 1)
    elif isinstance(o, list):
        for v in o[:5]:
            keypaths(v, prefix + "[]", acc, depth + 1)
    return acc

def positions(s, cap=6):
    res = []
    p = s.lower().encode("utf-8")
    i = low.find(p)
    while i >= 0 and len(res) < cap:
        res.append(i)
        i = low.find(p, i + 1)
    return res

targets = sorted(f for f in os.listdir(DAT) if f.endswith(".json"))
w("### KEY-NAME COVERAGE IN EXE, per JSON file (keys extracted from the file itself)")
w("%-42s %6s %7s %7s %8s  %s" % ("file", "#keys", "#inExe", "%", "maxrun", "contiguous schema run found"))

results = {}
for f in targets:
    try:
        j = json.loads(open(os.path.join(DAT, f), "rb").read().decode("utf-8-sig"))
    except Exception as e:
        w("%-42s PARSE-FAIL %s" % (f, e))
        continue
    kc = keypaths(j)
    keys = [k for k in kc if len(k) >= 4 and re.match(r"^[A-Za-z_][A-Za-z0-9_ ]*$", k)]
    inx = []
    for k in keys:
        p = positions(k, 1)
        if p:
            inx.append((k, p[0]))
    inx.sort(key=lambda t: t[1])
    # longest run where consecutive keys are within 600 bytes
    best = 0; beststart = None; cur = 0; start = None
    for i, (k, off) in enumerate(inx):
        if i > 0 and off - inx[i - 1][1] <= 600:
            cur += 1
        else:
            cur = 1; start = off
        if cur > best:
            best = cur; beststart = start
    results[f] = dict(nkeys=len(keys), nin=len(inx), maxrun=best, start=beststart,
                      keys=[k for k, _ in inx])
    w("%-42s %6d %7d %6.1f%% %8d  %s" % (f, len(keys), len(inx),
      100.0 * len(inx) / max(1, len(keys)), best, ("@%s" % beststart) if beststart else ""))

w("\n\n### FILES WHOSE KEYS ARE (ALMOST) ABSENT FROM THE EXE -> engine has no schema for them")
for f, r in sorted(results.items(), key=lambda kv: kv[1]["nin"] - kv[1]["nkeys"]):
    frac = r["nin"] / max(1, r["nkeys"])
    if frac < 0.34:
        w("  %-42s %d/%d keys in exe (%.0f%%)   maxrun=%d" % (f, r["nin"], r["nkeys"], 100 * frac, r["maxrun"]))

w("\n\n### FILES WITH A LONG CONTIGUOUS KEY RUN (>=5 within 600B) -> engine has a real schema block")
for f, r in sorted(results.items(), key=lambda kv: -kv[1]["maxrun"]):
    if r["maxrun"] >= 5:
        w("  %-42s maxrun=%-3d starts @%s" % (f, r["maxrun"], r["start"]))

w("\n\n### per-file detail for the ambiguous ones")
for f in ["futuravailableunits.json", "paphosfutureavailableunits.json", "linkedUnits.json",
          "unitcategories.json", "selection_group_def.json", "chronicles_selection_group_def.json",
          "linkedTechs.json", "AIConsts.json", "airesourcetypes.json", "hotkeys.json", "sounds.json"]:
    r = results.get(f)
    if r:
        w("  %-40s %d/%d in exe: %s" % (f, r["nin"], r["nkeys"], r["keys"][:25]))

w("\n\n### '_def.json' occurrence context")
p = b"_def.json"
i = buf.find(p)
w("  @%d  %s" % (i, repr(buf[max(0, i - 200): i + 200])))

w("\n\n### writer-side evidence search")
for pat in ["serialize", "to_string", "ofstream", "fopen", "\\.tmp", ".tmp",
            "CivTechTrees", "civtech", "SaveCiv", "WriteJson", "write_json", "dump(",
            "boost::json", "nlohmann", "rapidjson", "writeJsonFile"]:
    n = len(re.findall(re.escape(pat.lower().encode()), low))
    w("  %-20s n=%d" % (pat, n))

json.dump(results, open(os.path.join(OUT, "s16_coverage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(OUT, "s16_coverage.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
