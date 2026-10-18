import sys, io, os, glob, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
root = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
for kind in ("local","subscribed"):
    for d in sorted(os.listdir(os.path.join(root,kind))):
        p = os.path.join(root,kind,d)
        if not os.path.isdir(p): continue
        inf = os.path.join(p,"info.json")
        title = None
        if os.path.exists(inf):
            try:
                j = json.load(open(inf,encoding="utf-8-sig"))
                title = j.get("Title") or j.get("title")
            except Exception as e: title = "<ERR %s>" % e
        print("%-10s %-58s Title=%r  same=%s" % (kind, d[:58], title, (title==d)))
print()
print("=== docs claiming which dsh test versions are installed")
import re
for doc in ["项目状态.md","变更日志.md",".dsh/skills/aoe2-de-dat/SKILL.md",".dsh/skills/aoe2-de-sprites/SKILL.md","数据模组能力目录v1.md","图形音效模组能力目录v1.md"]:
    for i,t in enumerate(open(doc,encoding="utf-8").read().splitlines(),1):
        for m in re.finditer(r"dsh test v\d+|v1[0-3] 已装|v1[0-3] 已?实机", t):
            print("%s:%d  %s" % (doc,i,m.group(0)))
            break
