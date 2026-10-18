import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src=open("aoe2mod/dat/locate.py",encoding="utf-8").read().splitlines()
for i in range(88,110): print("%4d| %s" % (i, src[i-1].rstrip()[:170]))
print("...")
for i in range(296,330): print("%4d| %s" % (i, src[i-1].rstrip()[:170]))
print("...")
for i in range(455,500): print("%4d| %s" % (i, src[i-1].rstrip()[:170]))
