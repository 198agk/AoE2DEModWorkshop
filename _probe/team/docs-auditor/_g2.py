import sys, io, subprocess, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for pat in ["4,239","4239","287/287","62/62"]:
    print("=== " + pat)
    for root,dirs,files in os.walk("."):
        if ".git" in root or "node_modules" in root: continue
        for f in files:
            if not f.endswith((".md",".py",".txt",".json")): continue
            p=os.path.join(root,f)
            try: t=open(p,encoding="utf-8",errors="replace").read()
            except Exception: continue
            if pat in t:
                for i,ln in enumerate(t.splitlines(),1):
                    if pat in ln:
                        print("  %s:%d: %s" % (p,i,ln.strip()[:120]))
