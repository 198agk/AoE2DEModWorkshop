import os, io, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=" * 90)
w("BB. EVERY '.json'-bearing string literal in AoE2DE_s.exe (complete, sorted by offset)")
w("=" * 90)
pat = re.compile(rb"[ -~]*\.json")
rows = []
for m in re.finditer(rb"[\x20-\x7e]{3,}\.json|[\x20-\x7e]{0,60}\.json", exe):
    s = m.group(0).decode("latin-1")
    # keep only plausible filename-ish tokens
    if len(s) > 80: continue
    rows.append((m.start(), s))
# dedupe by (offset,string) then group strings
seen = {}
for off, s in rows:
    key = s
    seen.setdefault(key, []).append(off)
w("  distinct .json strings = %d ; total occurrences = %d" % (len(seen), len(rows)))
for s in sorted(seen, key=lambda x: min(seen[x])):
    w("  %-58s x%-3d @%s" % (s, len(seen[s]), seen[s][:4]))

w("")
w("=" * 90)
w("CC. Which of those appear in the dat dir / are in scope?")
w("=" * 90)
BASE = os.path.join(GAME, "resources", "_common", "dat")
ondisk = set(os.listdir(BASE)) | {f for f in os.listdir(os.path.join(BASE, "CivTechTrees"))}
w("  on-disk dat-dir files matched an exe .json literal:")
for s in sorted(seen):
    base = s.split("\\")[-1].split("/")[-1]
    if base in ondisk:
        w("     %-46s -> %s" % (s, base))
w("")
w("  in-scope filenames with NO literal anywhere in exe:")
for f in sorted(ondisk):
    if f.endswith(".json") and f.encode() not in exe and f != "CivTechTrees":
        w("     %s" % f)
open(os.path.join(OUT, "s51_jsonnames.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
