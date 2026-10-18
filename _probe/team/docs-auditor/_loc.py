import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src=open("aoe2mod/dat/locate.py",encoding="utf-8").read().splitlines()
for i,l in enumerate(src,1):
    s=l.strip()
    if s.startswith("def ") or s.startswith("class "): print("%4d| %s" % (i,s[:150]))
print("---- around 250-290")
for i in range(248,292): print("%4d| %s" % (i, src[i-1].rstrip()[:170]))
