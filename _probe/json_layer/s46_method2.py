import os, io, json, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

NAMES = ["AIConsts.json","adapterblacklist.json","adapter_blacklist.json","airesourcetypes.json",
         "AIResourceTypes.json","buttons.json","chronicles_selection_group_def.json",
         "civilizations.json","dropsites.json","eras.json","futuravailableunits.json","hotkeys.json",
         "linkedTechs.json","linkedUnits.json","maps.json","objreplacement.json","paphos_campaign.json",
         "paphosfutureavailableunits.json","peru_campaign.json","providence_campaign.json",
         "selection_group_def.json","sharedbuildings.json","sounds.json","unitcategories.json",
         "unitlines.json","civTechTrees.json","CivTechTrees"]

w("=" * 90)
w("METHOD 2: search TEXT files all over the game tree for these filenames")
w("   (a second, independent method: engine-independent references)")
w("=" * 90)
TEXT_EXT = {".lua", ".xs", ".xml", ".json", ".txt", ".ini", ".cfg", ".py", ".md", ".js", ".html", ".rms", ".csv"}
hits = {n: [] for n in NAMES}
scanned = 0
for root, dirs, files in os.walk(GAME):
    # skip heavy binary dirs for speed but keep scripts/config
    if any(s in root.lower() for s in ("\\drs\\", "\\sound\\", "\\textures\\", "\\resources\\_packages")):
        continue
    for fn in files:
        if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
            continue
        fp = os.path.join(root, fn)
        try:
            if os.path.getsize(fp) > 8_000_000: continue
            b = open(fp, "rb").read()
        except Exception:
            continue
        scanned += 1
        try:
            t = b.decode("utf-8", "ignore")
        except Exception:
            continue
        for n in NAMES:
            if n in t:
                hits[n].append(os.path.relpath(fp, GAME))
w("  text files scanned: %d" % scanned)
for n in NAMES:
    h = hits[n]
    w("  %-34s hits=%d  %s" % (n, len(h), h[:5]))

w("")
w("=" * 90)
w("selection_group_def.json: how could the engine find it if the name is not a literal?")
w("=" * 90)
for pat in (b"selection", b"Selection", b"SELECTION", b"radial", b"Radial", b"item_list", b"is_building"):
    offs = [m.start() for m in re.finditer(re.escape(pat), exe)]
    w("  %-12s count=%d offsets=%s" % (pat.decode(), len(offs), offs[:8]))
w("  window around 'radial' if present:")
for m in re.finditer(rb"radial", exe):
    lo = max(0, m.start() - 120); hi = m.start() + 160
    for mm in re.finditer(rb"[ -~]{5,}", exe[lo:hi]):
        w("     %8d %s" % (lo + mm.start(), mm.group(0).decode("latin-1")))
    break
w("")
w("  '_def' occurrences sample (first 20):")
offs = [m.start() for m in re.finditer(rb"_def", exe)]
w("     %s" % offs[:20])
for o in offs[:6]:
    lo = max(0, o - 60); hi = o + 60
    w("     @%d  %r" % (o, exe[lo:hi]))

w("")
w("=" * 90)
w("sounds.json key->name mapping: is 'name' mechanically derived from 'key'?")
w("=" * 90)
sj = json.loads(open(os.path.join(BASE, "sounds.json"), "rb").read().decode("utf-8-sig"))["sound_list"]
derived = 0; underived = []
for e in sj:
    guess = "Play_" + "_".join(p.capitalize() for p in e["key"].split("_"))
    if guess == e["name"]: derived += 1
    else: underived.append((e["key"], e["name"], guess))
w("  entries=%d exact-mechanical-derivation=%d not-derivable=%d" % (len(sj), derived, len(underived)))
for u in underived: w("     key=%-22s name=%-26s guess=%s" % u)

w("")
w("=" * 90)
w("futuravailableunits civ keys: internal_name spellings vs exe civ registry")
w("=" * 90)
fau = json.loads(open(os.path.join(BASE, "futuravailableunits.json"), "rb").read().decode("utf-8-sig"))
w("  n=%d keys=%s" % (len(fau), sorted(fau)[:12]))
present = [k for k in fau if k.encode() in exe]
absent = [k for k in fau if k.encode() not in exe]
w("  keys present as exe literals: %d ; absent: %d" % (len(present), len(absent)))
w("  absent sample: %s" % absent[:12])
w("  -> NOTE the exe carries the '-CIV' data_name registry (BRITON-CIV...), not plain internal names.")
w("  civilization_list internal_name present in exe: %s" % {
    k: (k.encode() in exe) for k in ["Gaia", "Britons", "Franks", "Goths", "Aztecs", "Armenians"]})
open(os.path.join(OUT, "s46_method2.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
