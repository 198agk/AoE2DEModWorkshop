import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, glob, os
d = _ROOT_PATH("aoe2docs")
KEYS = ["dds", "dxt", "mipmap", ".mip", "texconv", "texture format", "a8b8g8r8", "b8g8r8a8",
        "dxgi", "compressed texture", "uncompressed"]
for f in sorted(glob.glob(os.path.join(d, "*.json"))):
    try:
        j = json.load(open(f, encoding="utf-8-sig"))
    except Exception:
        continue
    ps = j.get("posts") or (j.get("post_stream") or {}).get("posts") or []
    hits = []
    for p in ps:
        t = (p.get("raw") or p.get("cooked") or p.get("blurb") or "")
        tl = t.lower()
        if any(k in tl for k in KEYS):
            hits.append((p.get("post_number"), p.get("username"), t))
    if hits:
        print("#" * 90)
        print("FILE", os.path.basename(f))
        for pn, u, t in hits:
            t = t.replace("\n", " ")
            print(f"  p{pn} @{u}: {t[:1200]}")
        print()
