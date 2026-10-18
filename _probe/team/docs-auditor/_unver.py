import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DOCS=["项目状态.md","变更日志.md","数据模组能力目录v1.md","图形音效模组能力目录v1.md","UI贴图模组能力目录v1.md",
      "_恢复说明.md","零mod实机实验_观测卡.md","smoke6实机验证卡.md","插件可用清单v1.md","能力目录v0.md"]
NEED=["未验证","未证实","未实机","not yet","Nothing has","no local","0 个提供","no precedent"]
for d in DOCS:
    if not os.path.exists(d): continue
    L=open(d,encoding="utf-8").read().splitlines()
    hits=[(i,l) for i,l in enumerate(L,1) if any(n in l for n in NEED)]
    if hits:
        print("==",d,len(L),"lines;",len(hits),"hits")
        for i,l in hits[:14]: print("  %4d| %s" % (i, l.strip()[:190]))
