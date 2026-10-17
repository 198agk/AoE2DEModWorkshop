import re, io

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

# The flag table lives around 0x3258c00. Find its true start/end by
# scanning a wide window and keeping only runs that look like
#   ALL_CAPS_FLAG  or  English description sentence
lo, hi = 0x3256000, 0x325a400
seg = data[lo:hi]

FLAG = re.compile(r"^[A-Z][A-Z0-9_]{2,42}$")
def is_desc(s):
    if len(s) < 8:
        return False
    if FLAG.match(s):
        return False
    if not re.search(r"[a-z]", s):
        return False
    if not re.search(r"[ .]", s):
        return False
    # reject garbage
    if re.search(r"[{}<>|\\^~`]", s):
        return False
    return True

runs = [(lo + m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{4,}", seg)]

w("### structured walk of flag table region ###\n")
i = 0
pairs = []
while i < len(runs):
    off, s = runs[i]
    if is_desc(s):
        # next flag-ish run
        for j in range(i + 1, min(i + 3, len(runs))):
            if FLAG.match(runs[j][1]):
                pairs.append((runs[j][1], s))
                break
    i += 1

# dedupe keeping first
seen = set()
final = []
for f, d in pairs:
    if f in seen:
        continue
    seen.add(f)
    final.append((f, d))

w("distinct (flag, description): %d\n\n" % len(final))
for f, d in final:
    w("  %-40s %s\n" % (f, d[:150]))

txt = out.getvalue()
io.open(r"D:\Software\DeepSeek Harness\工作区2\_probe\ui_surfaces\exe_flagtable3.txt", "w", encoding="utf-8").write(txt)
print("distinct pairs:", len(final))
for f, d in final:
    print("  %-38s | %s" % (f, d[:120]))
