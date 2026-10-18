import sys, io, glob, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
docs = ["项目状态.md","变更日志.md","数据模组能力目录v1.md","图形音效模组能力目录v1.md","UI贴图模组能力目录v1.md",
        "能力目录v0.md","_恢复说明.md","插件可用清单v1.md","零mod实机实验_观测卡.md","smoke6实机验证卡.md"]
docs += glob.glob(".dsh/skills/*/SKILL.md")
for d in docs:
    for i, ln in enumerate(open(d,encoding="utf-8").read().splitlines(), 1):
        if "test_scan_panels" in ln:
            print("%s:%d: %s" % (d,i,ln[:200]))
