import os, io, re

OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def dump(center, before=700, after=900, label=""):
    w("=" * 78)
    w("NEIGHBORHOOD %s  @%d" % (label, center))
    w("=" * 78)
    lo = max(0, center - before); hi = min(len(exe), center + after)
    chunk = exe[lo:hi]
    cur = lo
    for m in re.finditer(rb"[ -~]{4,200}", chunk):
        w("  @%-9d %r" % (lo + m.start(), m.group(0).decode("latin-1")))
    w("")

targets = {
    "resources\\_common\\dat": b"resources\\_common\\dat",
    "%s.json": b"%s.json",
    "File not found in data set resource": b"File not found in data set resource",
}
for lab, pat in targets.items():
    for m in re.finditer(re.escape(pat), exe):
        dump(m.start(), 500, 700, lab)

# Where are the 19 filenames, listed with their offsets
w("=" * 78)
w("FILENAME OFFSETS (all occurrences)")
w("=" * 78)
NAMES = ["AIConsts.json", "AIResourceTypes.json", "airesourcetypes.json", "adapter_blacklist.json",
         "buttons.json", "civTechTrees.json", "CivTechTrees", "civilizations.json", "dropsites.json",
         "eras.json", "futuravailableunits.json", "history.json", "hotkeys.json", "linkedTechs.json",
         "linkedUnits.json", "maps.json", "objreplacement.json", "sharedbuildings.json", "sounds.json",
         "unitcategories.json", "unitlines.json", "selection_group_def.json",
         "chronicles_selection_group_def.json", "paphosfutureavailableunits.json",
         "paphos_campaign.json", "peru_campaign.json", "providence_campaign.json",
         "morematerials", "materials.json", "water_def.json", "stringreference.json"]
for n in NAMES:
    offs = [m.start() for m in re.finditer(re.escape(n.encode()), exe)]
    w("  %-40s %s" % (n, offs))
open(os.path.join(OUT, "s38_loader.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue()[:14000])
