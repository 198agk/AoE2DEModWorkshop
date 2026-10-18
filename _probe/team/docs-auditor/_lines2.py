import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for f, lines in [(".dsh/skills/aoe2-de-dat/SKILL.md",[8,38,39,43,46,467,448]),
                 ("数据模组能力目录v1.md",[16,69,1993,2166,2988]),
                 ("变更日志.md",[9,58]),
                 ("UI贴图模组能力目录v1.md",[25,203])]:
    L = open(f, encoding="utf-8").read().splitlines()
    print("="*20, f, len(L), "lines")
    for n in lines:
        s = L[n-1] if n-1 < len(L) else "<EOF>"
        print("%4d| %s" % (n, s[:420]))
print("="*20, "dirs")
for p in ["_probe/sld_out", "_shots", "_probe/hud_render"]:
    print(p, os.path.isdir(p))
print("hud_render files:", sorted(os.listdir("_probe/hud_render"))[:40] if os.path.isdir("_probe/hud_render") else None)
