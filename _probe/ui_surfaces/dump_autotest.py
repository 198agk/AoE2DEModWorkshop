import re, io

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

def region(lo, hi, label):
    w("\n########## %s [0x%x-0x%x] ##########\n" % (label, lo, hi))
    seg = data[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{4,200}", seg):
        w("  0x%08x  %s\n" % (lo + m.start(), m.group().decode("ascii")))

region(0x31f9b00, 0x31fa200, "AUTOTEST flag region")
region(0x321c000, 0x321d200, "command line switch region (FORCE_LANGUAGE etc)")

# Autotest-related strings anywhere
w("\n########## AUTOTEST / KBM / event controller strings anywhere ##########\n")
pats = [rb"AUTOTEST", rb"autotest", rb"KBM", rb"EVENTTASK", rb"EventController", rb"EventTask"]
for p in pats:
    w("\n--- %s ---\n" % p.decode())
    for m in re.finditer(p, data):
        o = m.start()
        ctx = data[max(0, o - 80):o + 120]
        s = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
        w("  0x%x  %s\n" % (o, s.strip()))

txt = out.getvalue()
io.open(r"D:\Software\DeepSeek Harness\工作区2\_probe\ui_surfaces\exe_autotest.txt", "w", encoding="utf-8").write(txt)
print(txt[:8000])
