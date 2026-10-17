"""Round 6: message model, options, and the remaining unknowns."""
import glob
import json
import os
import warnings
warnings.filterwarnings("ignore")

SITE = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\AoE2ScenarioParser"
HERE = os.path.dirname(os.path.abspath(__file__))

print("=== locate message-related sources ===")
for p in sorted(glob.glob(os.path.join(SITE, "**", "*.py"), recursive=True)):
    rel = os.path.relpath(p, SITE)
    low = rel.lower()
    if any(k in low for k in ("message", "option_manager", "fileheader", "dataheader")):
        print("  ", rel, os.path.getsize(p))

print()
print("=== MessageManager source ===")
for cand in ("managers/message_manager.py", "objects/managers/message_manager.py",
             "managers/message_manager/message_manager.py"):
    p = os.path.join(SITE, *cand.split("/"))
    if os.path.exists(p):
        print("  FOUND:", cand)
        src = open(p, encoding="utf-8").read()
        print("  bytes:", len(src))
        for line in src.splitlines():
            s = line.rstrip()
            if s.strip().startswith(("def ", "class ")) or ("=" in s and "self." in s.split("=")[0] and "struct" in s.lower()):
                print("   ", s.strip()[:120])
        break
else:
    hits = glob.glob(os.path.join(SITE, "**", "message_manager*"), recursive=True)
    print("  glob hits:", [os.path.relpath(h, SITE) for h in hits])

print()
print("=== Messages section in v1.54 structure.json ===")
st = json.load(open(os.path.join(SITE, "versions", "DE", "v1.54", "structure.json"), encoding="utf-8"))
print(json.dumps(st["Messages"], indent=1)[:2000])

print()
print("=== Options section retriever names (v1.54) ===")
opts = st["Options"]["retrievers"]
print("  count:", len(opts))
print("  names:", list(opts.keys()))

print()
print("=== per-section retriever names (v1.54) ===")
for sec, body in st.items():
    if isinstance(body, dict) and "retrievers" in body:
        print(f"  {sec} ({len(body['retrievers'])}): {list(body['retrievers'].keys())}")

print()
print("=== version-diff: v1.53 vs v1.54 section list ===")
for v in ("1.53", "1.54", "1.59"):
    p = os.path.join(SITE, "versions", "DE", f"v{v}", "structure.json")
    s = json.load(open(p, encoding="utf-8"))
    print(f"  v{v}: {list(s.keys())}")
    print(f"        counts: { {k: len(s[k].get('retrievers', {})) for k in s} }")
