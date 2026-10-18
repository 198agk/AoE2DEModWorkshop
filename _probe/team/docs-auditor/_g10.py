import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
S=open("项目状态.md",encoding="utf-8").read().splitlines()
print("total lines", len(S))
for i,t in enumerate(S,1):
    if ("面板" in t) or ("Round 5" in t) or ("误读" in t) or ("shape" in t):
        print("%d: %s" % (i, t[:260]))
