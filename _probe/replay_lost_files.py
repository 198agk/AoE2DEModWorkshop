# -*- coding: utf-8 -*-
"""Rebuild each lost file by replaying its write/edit tool calls in time order.

filter-repo's reset --hard put every uncommitted edit back to HEAD, but the tool
calls that made those edits are still in the DSH session store.  Writes carry a
whole file; edits carry only old_string/new_string, so the newest write is the
base and every later edit is re-applied on top.  Read-only over the store.
"""
import json, glob, os, zstandard

STORE = r"C:/Users/26913/.dsh/sessions/--D-Software-AI-Aoe2--"
OUT = r"D:/Software/AI/Aoe2/_cache/_recover"
TARGETS = {
 "README.md": "README.md", "RELEASE.md": "RELEASE.md",
 "变更日志.md": "变更日志.md", "项目状态.md": "项目状态.md",
 "_probe/render_acceptance.py": "render_acceptance.py",
 "_probe/ship_and_verify.py": "ship_and_verify.py",
 "_probe/test_about_page.py": "test_about_page.py",
 "_probe/test_name_text.py": "test_name_text.py",
 "_probe/test_online_unit.py": "test_online_unit.py",
 "_probe/test_page_route_contract.py": "test_page_route_contract.py",
}
events = []
files = sorted(glob.glob(os.path.join(STORE, "*", "session.v4.jsonl.zstd")), key=os.path.getmtime)
for fp in files:
    try:
        raw = zstandard.ZstdDecompressor().stream_reader(open(fp, "rb")).read()
    except Exception:
        continue
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") not in ("tool/call", "tool/ptc-dispatch"):
            continue
        d = ev.get("data") or {}
        arg = d.get("arguments") or ""
        if not arg:
            continue
        events.append((ev.get("time") or 0, d.get("name") or "", arg))
events.sort(key=lambda e: e[0])
os.makedirs(OUT, exist_ok=True)
report = []
for rel, short in TARGETS.items():
    base = None; base_t = 0; applied = 0; failed = 0
    for t, name, arg in events:
        if rel not in arg:
            continue
        try:
            a = json.loads(arg)
        except Exception:
            continue
        fp_ = a.get("file_path") or a.get("path") or ""
        if not isinstance(fp_, str) or not (fp_.replace("\\", "/").endswith(rel)):
            continue
        if name in ("write",) and isinstance(a.get("content"), str):
            base = a["content"]; base_t = t; applied = 0; failed = 0
        elif name in ("edit",) and base is not None and isinstance(a.get("old_string"), str):
            old = a["old_string"]; new = a.get("new_string") or ""
            if old in base:
                base = base.replace(old, new, -1 if a.get("replace_all") else 1)
                applied += 1
            else:
                failed += 1
    if base is None:
        report.append((short, "NO WRITE FOUND", 0, 0))
        continue
    with open(os.path.join(OUT, short), "w", encoding="utf-8", newline="") as f:
        f.write(base)
    report.append((short, "rebuilt", base.count("\n") + 1, applied))
for r in report:
    print(r)
