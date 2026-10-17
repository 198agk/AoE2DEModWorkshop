# -*- coding: utf-8 -*-
"""Generate the GV_* constant block for parse_dat.py straight from the
genieutils enum, replacing whatever hand-written block is there.

Hand-transcribing 59 enum ordinals is exactly the kind of thing that silently
goes wrong (it did: GV_C5 was written as 26 instead of 27).  Generate it.
"""
import re
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse")
import vg_diff_full as V

TARGET = r"D:\Software\DeepSeek Harness\工作区2\_probe\datparse\parse_dat.py"

gv = V.parse_enum()
# preserve declaration order as it appears in the enum body
txt = open(V.TYPES, encoding="utf-8", errors="replace").read()
m = re.search(r"enum\s+GameVersion\s*\{(.*?)\n\s*\};", txt, re.S)
order = []
for raw in m.group(1).split("\n"):
    line = raw.split("//")[0].strip()
    for tok in line.split(","):
        tok = tok.strip()
        if re.match(r"^GV_\w+$", tok):
            order.append(tok)

lines = []
for name in order:
    lines.append("%s = %d" % (name, gv[name]))
block = "\n".join(lines)

src = open(TARGET, encoding="utf-8").read()
start = src.index("GV_None = 0")
end = src.index("GV_CCV2 = 58") + len("GV_CCV2 = 58")
new = src[:start] + block + src[end:]
open(TARGET, "w", encoding="utf-8", newline="").write(new)

print("replaced %d chars with %d generated lines" % (end - start, len(lines)))
print("first:", lines[0], "| last:", lines[-1])
