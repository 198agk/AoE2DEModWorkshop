import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L = open("aoe2mod/api.py",encoding="utf-8").read().splitlines()
for start in (727,832,912,1564,1573,1617,2380,2836):
    print("----- aoe2mod/api.py:%d" % start)
    for i in range(start, min(start+9, len(L)+1)):
        print("  %d| %s" % (i, L[i-1].rstrip()[:230]))
