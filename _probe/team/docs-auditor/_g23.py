import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("项目状态.md",encoding="utf-8").read().splitlines()
for n in range(1,30):
    if L[n-1].strip(): print("%d| %s" % (n, L[n-1][:300]))
print("...")
for n in (76,78,86,118,121,122,123,124,126,140,144,145,146,147,148,149,150,151,156,157,163,164,165,166,167):
    print("%d| %s" % (n, L[n-1][:400]))
