import json, sys, os, glob

base = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\AoE2ScenarioParser\versions\DE"

def show(ver):
    p = os.path.join(base, ver, "structure.json")
    if not os.path.exists(p):
        print(f"--- {ver}: MISSING")
        return
    d = json.load(open(p, encoding="utf-8"))
    fh = d["FileHeader"]["retrievers"]
    print(f"--- {ver} FileHeader ({len(fh)} retrievers)")
    for name, attr in fh.items():
        print(f"    {name:38s} {json.dumps(attr)}")

for v in sys.argv[1:]:
    show(v)
