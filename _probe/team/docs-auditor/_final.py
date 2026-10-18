import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for pat in ["_rng*.py","*rng3*","*rng4*","*rng5*","*tech_describe_audit*","*cost_fallback_impact*","*probe_donor_bias*","*_subctx*","*fix_frames*"]:
    hits = glob.glob(pat)+glob.glob("_probe/"+pat)+glob.glob("_probe/**/"+pat, recursive=True)
    print("%-26s %s" % (pat, hits[:4] if hits else "NONE"))
print()
# mod title vs folder name claim (项目状态.md:78 "8/8")
import json
base = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
for kind in ("local","subscribed"):
    p = os.path.join(base,kind)
    if not os.path.isdir(p): continue
    for d in sorted(os.listdir(p)):
        f = os.path.join(p,d,"info.json")
        if os.path.isdir(os.path.join(p,d)) and os.path.exists(f):
            try: t = json.load(open(f,encoding="utf-8-sig")).get("Title","")
            except Exception as e: t = "<err %s>" % e
            print("%-9s %-62s | Title=%-52s | same=%s" % (kind, d, t[:50], t==d))
