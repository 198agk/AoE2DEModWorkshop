import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# 1. suite count + which panel pins are registered
src = open("_probe/run_suites.py", encoding="utf-8").read()
m = re.search(r"SUITES\s*=\s*\[(.*?)\]", src, re.S)
names = re.findall(r'"([^"]+)"', m.group(1)) if m else []
print("run_suites SUITES entries:", len(names))
print("panel pins registered:", [n for n in names if "panel" in n])
print("reskin registered:", [n for n in names if "reskin" in n])
# 2. committed suite artifact
for cand in ("_probe/out_suites_final2.txt", "_probe/out_suites_bundle2.txt", "_probe/out_suites_final.txt"):
    if os.path.exists(cand):
        t = open(cand, encoding="utf-8", errors="replace").read()
        print("%s EXISTS  exit=0 lines=%d  ALLPASSED=%s  bytes=%d" % (cand, t.count("exit=0"), "ALL PASSED" in t, len(t.encode("utf-8"))))
    else:
        print("%s ABSENT" % cand)
# 3. doc byte sizes
for f in ("项目状态.md","数据模组能力目录v1.md","变更日志.md","图形音效模组能力目录v1.md",
          ".dsh/skills/aoe2-de-dat/SKILL.md",".dsh/skills/aoe2-de-sprites/SKILL.md",
          ".dsh/skills/aoe2-de-ui-textures/SKILL.md"):
    b = os.path.getsize(f); L = len(open(f,encoding="utf-8").read().splitlines())
    print("%-42s %8d B  %6.1f KB  %5d lines" % (f, b, b/1024, L))
# 4. py counts
def count(root):
    n=0
    for dp,dn,fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git","__pycache__")]
        n += sum(1 for f in fn if f.endswith(".py"))
    return n
print("aoe2mod .py:", count("aoe2mod"), " tools .py:", count("tools"), " _probe .py:", count("_probe"),
      " _probe top-level .py:", len([f for f in os.listdir("_probe") if f.endswith(".py")]))
# 5. old root in shipped code
hits=[]
for base in ("aoe2mod","tools"):
    for dp,dn,fn in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git","__pycache__")]
        for f in fn:
            if f.endswith(".py"):
                p=os.path.join(dp,f)
                for i,line in enumerate(open(p,encoding="utf-8",errors="replace"),1):
                    if "工作区2" in line or "DeepSeek Harness" in line:
                        hits.append((p,i,line.strip()[:120]))
print("old-root hits in aoe2mod+tools:", len(hits))
for h in hits: print("   %s:%d  %s" % h)
