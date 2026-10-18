import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("数据模组能力目录v1.md",encoding="utf-8").read().splitlines()
for n in range(3175,3216):
    t=L[n-1]
    if t.strip(): print("%d: %s" % (n, t[:300]))
print("\n=== 项目状态.md mentions of 434 / block / misread")
S=open("项目状态.md",encoding="utf-8").read().splitlines()
for i,t in enumerate(S,1):
    if "434" in t or "block" in t or "误读" in t or "test_panel_shape" in t:
        print("%d: %s" % (i, t[:400]))
