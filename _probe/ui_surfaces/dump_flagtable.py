import re, io

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

# The flag table pattern:  "Description sentence."  <padding>  FLAGNAME
# Scan a wide region and pull (desc, flag) pairs.
lo, hi = 0x3258a00, 0x3259a00
seg = data[lo:hi]

runs = [(lo + m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{3,}", seg)]
w("### runs in 0x%x-0x%x: %d\n\n" % (lo, hi, len(runs)))

# Heuristic: a description contains a space and >=2 words and ends with '.' or is sentence-like;
# the next run that looks like a FLAG (ALLCAPS, no lowercase, no space) is its flag.
FLAG = re.compile(r"^[A-Z][A-Z0-9_]{2,40}$")
def is_desc(s):
    return (" " in s) and len(s) >= 12 and not s.startswith("0x")

pairs = []
for i, (off, s) in enumerate(runs):
    if is_desc(s):
        # look ahead up to 3 runs for a flag
        for j in range(i + 1, min(i + 4, len(runs))):
            if FLAG.match(runs[j][1]):
                pairs.append((off, s, runs[j][1]))
                break

w("### %d (description -> flag) pairs ###\n" % len(pairs))
for off, d, f in pairs:
    w("0x%08x  %-38s | %s\n" % (off, f, d[:150]))

# raw dump too
w("\n\n### RAW ###\n")
for off, s in runs:
    w("  0x%08x  %s\n" % (off, s[:180]))

txt = out.getvalue()
io.open(r"D:\Software\DeepSeek Harness\工作区2\_probe\ui_surfaces\exe_flagtable.txt", "w", encoding="utf-8").write(txt)
print("pairs:", len(pairs))
for off, d, f in pairs:
    print("  %-34s | %s" % (f, d[:130]))
