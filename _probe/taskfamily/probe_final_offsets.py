# -*- coding: utf-8 -*-
"""Final: exact file offset -> RVA for the two exe tables, plus the
authoritative TaskSwapGroup roster as the report will state it."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import struct, json, os
EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
b = open(EXE, "rb").read()
pe = struct.unpack_from("<I", b, 0x3C)[0]
nsec = struct.unpack_from("<H", b, pe + 6)[0]
opt_size = struct.unpack_from("<H", b, pe + 20)[0]
opt = pe + 24
magic = struct.unpack_from("<H", b, opt)[0]
image_base = (struct.unpack_from("<I", b, opt + 28)[0] if magic == 0x10B
              else struct.unpack_from("<Q", b, opt + 24)[0])
sec_off = opt + opt_size
secs = []
for i in range(nsec):
    o = sec_off + i * 40
    secs.append((b[o:o+8].rstrip(b"\0").decode("latin-1"),
                 struct.unpack_from("<I", b, o + 12)[0],
                 struct.unpack_from("<I", b, o + 16)[0],
                 struct.unpack_from("<I", b, o + 20)[0]))
def rva(off):
    for n, va, rs, rp in secs:
        if rp <= off < rp + rs:
            return image_base + va + (off - rp), n
    return None, None

out = []
def p(s=""):
    out.append(s); print(s)

p("image_base = 0x%X" % image_base)
for name, start, count in (("TABLE A (villager pair table)", 0x32B1DCC, 25),
                           ("TABLE B (linked-object pair table)", 0x3232E30, 48)):
    r, sec = rva(start)
    vals = [struct.unpack_from("<i", b, start + 4 * k)[0] for k in range(count)]
    p("\n%s" % name)
    p("  file offset 0x%X  RVA 0x%X  section %s" % (start, r, sec))
    p("  %d x int32 = %d bytes  [0x%X .. 0x%X)" % (count, count*4, start, start+count*4))
    p("  values: %s" % vals)

# TaskSwapGroup roster straight from the dat is already in task_swap_groups.json
j = json.load(open(_HERE_PATH("_probe", "taskfamily", "task_swap_groups.json"),
                   encoding="utf-8"))
p("\ntask_swap_groups.json keys: %s" % list(j.keys()))
p(json.dumps(j, ensure_ascii=False)[:1200])

with open(_HERE_PATH("_probe", "taskfamily", "exe_tables_final.txt"),
          "w", encoding="utf-8") as f:
    f.write("\n".join(out))
p("\nwrote exe_tables_final.txt")
