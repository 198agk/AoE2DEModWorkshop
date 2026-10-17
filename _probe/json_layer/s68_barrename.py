import os, io, re
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
w("=== is bare 'Name' a standalone NUL-terminated literal in the node-field block? ===")
for m in re.finditer(rb"Name\x00", exe):
    c = m.start()
    if 52827900 <= c <= 52829200:
        w("  in CivTechTrees block @%d" % c)
w("  total 'Name\\x00' occurrences in whole exe = %d" % len(re.findall(rb"Name\x00", exe)))
w("  'Name String ID\\x00' occurrences = %d" % len(re.findall(rb"Name String ID\x00", exe)))
w("")
w("=== all NUL-terminated strings in 52828000..52828700 (the node-field block) ===")
lo, hi = 52828000, 52828700
for m in re.finditer(rb"[\x20-\x7e]{3,}\x00", exe[lo:hi]):
    w("  %8d  %s" % (lo + m.start(), m.group(0)[:-1].decode("latin-1")))
open(os.path.join(OUT, "s68_barrename.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
