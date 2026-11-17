# -*- coding: utf-8 -*-
"""Recover the un-committed text that filter-repo's reset --hard threw away.

The DSH session store keeps every tool call as a zstd-compressed JSONL file, so
an edit's new_string is still on disk even though the file it wrote is gone.
Read-only: writes only the recovered copies under _cache/_recover/.
"""
import json, os, sys, glob, zstandard

STORE = r"C:/Users/26913/.dsh/sessions/--D-Software-AI-Aoe2--"
OUT = r"D:/Software/AI/Aoe2/_cache/_recover"
TARGETS = ["变更日志.md", "项目状态.md", "README.md", "RELEASE.md",
           "_probe/render_acceptance.py", "_probe/ship_and_verify.py",
           "_probe/test_about_page.py", "_probe/test_name_text.py",
           "_probe/test_online_unit.py", "_probe/test_page_route_contract.py"]

def walk(obj, sink):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and len(v) > 200:
                sink.append((k, v))
            else:
                walk(v, sink)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, sink)

hits = {}
files = sorted(glob.glob(os.path.join(STORE, "*", "session.v4.jsonl.zstd")), key=os.path.getmtime)
print("sessions:", len(files))
for fp in files:
    try:
        with open(fp, "rb") as f:
            raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    except Exception as exc:
        print("skip", fp, exc); continue
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        blob = json.dumps(ev, ensure_ascii=False)
        for t in TARGETS:
            if t not in blob:
                continue
            sink = []
            walk(ev, sink)
            for key, val in sink:
                if t in val or ("file_path" in key and False):
                    hits.setdefault(t, []).append((os.path.basename(os.path.dirname(fp)), key, len(val), val))

os.makedirs(OUT, exist_ok=True)
for t, rows in hits.items():
    rows.sort(key=lambda r: r[2], reverse=True)
    name = t.replace("/", "_")
    with open(os.path.join(OUT, name + ".candidates.txt"), "w", encoding="utf-8") as f:
        for sess, key, ln, val in rows[:60]:
            f.write("=== %s %s len=%d ===\n" % (sess, key, ln))
            f.write(val[:200000] + "\n")
    print(t, "candidates", len(rows), "top len", rows[0][2] if rows else 0)
