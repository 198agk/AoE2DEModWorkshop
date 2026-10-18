import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
S=open("项目状态.md",encoding="utf-8").read().splitlines()
for n in (233,234,235,236,237):
    print("--- 项目状态.md:%d\n%s\n" % (n, S[n-1][:600]))
L=open("数据模组能力目录v1.md",encoding="utf-8").read().splitlines()
print("=== catalogue 3204 area, look for superseded marker")
for n in range(3202,3210):
    print("%d: %s" % (n, L[n-1][:200]))
print("=== search catalogue for 15.4ae cross-ref / 已修正")
for i,t in enumerate(L,1):
    if "15.4ae" in t or "15.4am" in t: print("  %d: %s" % (i,t[:160]))
