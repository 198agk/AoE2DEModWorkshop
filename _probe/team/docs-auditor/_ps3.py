import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("项目状态.md",encoding="utf-8").read().splitlines()
for n in (143,139,140,155,152):
    print("---- %d" % n); print(L[n-1]); print()
