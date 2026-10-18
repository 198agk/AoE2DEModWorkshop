import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DOCS = ["项目状态.md","变更日志.md","数据模组能力目录v1.md","图形音效模组能力目录v1.md","UI贴图模组能力目录v1.md",
        "能力目录v0.md","_恢复说明.md","_会话迁移记录.md","_会话清理记录.md","插件可用清单v1.md",
        "_probe/../AoE2DE_DDS技术研究报告.md",
        ".dsh/skills/aoe2-de-dat/SKILL.md",".dsh/skills/aoe2-de-sprites/SKILL.md",".dsh/skills/aoe2-de-ui-textures/SKILL.md"]
tok = re.compile(r"`([^`\n]*?\.py)`")
def find(t):
    t = t.replace("\\","/").strip()
    for c in (t, "_probe/"+t, "_probe/"+os.path.basename(t)):
        if os.path.exists(c): return c
    bn = os.path.basename(t)
    for dp,dn,fn in os.walk("_probe"):
        dn[:] = [d for d in dn if d!="__pycache__"]
        if bn in fn: return os.path.join(dp,bn)
    for dp,dn,fn in os.walk("aoe2mod"):
        dn[:] = [d for d in dn if d!="__pycache__"]
        if bn in fn: return os.path.join(dp,bn)
    if os.path.exists("tools/"+bn): return "tools/"+bn
    return None
seen = {}
for d in DOCS:
    if not os.path.exists(d): print("MISSING DOC", d); continue
    for i, ln in enumerate(open(d,encoding="utf-8").read().splitlines(),1):
        for m in tok.finditer(ln):
            t = m.group(1)
            if any(ch in t for ch in "<>*{}"): continue
            seen.setdefault((d,i,t), None)
miss = []
for (d,i,t) in seen:
    r = find(t)
    if r is None: miss.append((d,i,t))
print("distinct .py references:", len(seen), " unresolved:", len(miss))
for d,i,t in miss: print("  %-42s:%-4d %s" % (d.split("/")[-1], i, t))
