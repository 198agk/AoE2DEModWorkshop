import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("图形音效模组能力目录v1.md",encoding="utf-8").read().splitlines()
for n in range(228,300):
    t=L[n-1]
    if t.strip(): print("%d: %s" % (n, t[:260]))
