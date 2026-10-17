# -*- coding: utf-8 -*-
"""Analyze AoE2DE AI scripts: .per / .per2 / .ai / .xs"""
import os, re, json, collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROF = r"C:\Users\26913\Games\Age of Empires 2 DE"
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\survey_rms_ai"
os.makedirs(OUT, exist_ok=True)

def walk(root, exts):
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if os.path.splitext(f)[1].lower() in exts:
                out.append(os.path.join(dp, f))
    return sorted(out)

def decode(path):
    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    body = raw[3:] if bom else raw
    for enc in ("utf-8", "cp1252"):
        try:
            return body.decode(enc), enc, bom
        except UnicodeDecodeError:
            continue
    return body.decode("latin-1"), "latin-1", bom

files = walk(GAME, {".per", ".per2", ".ai", ".xs"}) + walk(PROF, {".per", ".per2", ".ai", ".xs"})
by_ext = collections.Counter()
report = []
kw = collections.Counter()
kw_files = collections.defaultdict(set)
dirs = collections.defaultdict(set)

# AI script language constructs
CONSTRUCTS = [
    "defrule", "defconst", "defglobal", "deffact", "load", "load-random",
    "startup", "detect-", "(true)", ">=", "<=", "=>",
]
DIRECTIVES = re.compile(r"\((up-[a-z0-9\-]+|[a-z][a-z0-9\-]*)")

for path in files:
    ext = os.path.splitext(path)[1].lower()
    by_ext[ext] += 1
    txt, enc, bom = decode(path)
    dirs[os.path.dirname(path)].add(ext)
    n_defrule = len(re.findall(r"\(\s*defrule\b", txt))
    n_defconst = len(re.findall(r"\(\s*defconst\b", txt))
    n_defglobal = len(re.findall(r"\(\s*defglobal\b", txt))
    n_comments = len(re.findall(r"^\s*;", txt, re.M))
    report.append({
        "path": path, "rel": os.path.relpath(path, GAME) if path.startswith(GAME) else path,
        "ext": ext, "size": os.path.getsize(path), "encoding": enc, "bom": bom,
        "lines": txt.count("\n") + 1,
        "defrule": n_defrule, "defconst": n_defconst, "defglobal": n_defglobal,
        "comment_lines": n_comments,
        "head": txt[:200].replace("\n", "\\n"),
    })
    for m in DIRECTIVES.finditer(txt):
        t = m.group(1)
        kw[t] += 1
        kw_files[t].add(path)

res = {
    "by_ext": by_ext.most_common(),
    "files": report,
    "top_directives": kw.most_common(120),
    "directive_spread": {k: len(v) for k, v in sorted(kw_files.items(), key=lambda x: -len(x[1]))},
}
with open(os.path.join(OUT, "ai_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

print("=== EXTENSION COUNTS ===")
for e, c in by_ext.most_common(): print(f"  {e}: {c}")
print("\n=== FILES (sorted by size) ===")
for r in sorted(report, key=lambda x: -x["size"]):
    print(f"  {r['size']:8d} {r['ext']:6s} rules={r['defrule']:4d} const={r['defconst']:4d} glob={r['defglobal']:3d}  {r['rel']}")
print("\n=== .ai FILES DETAIL ===")
for r in report:
    if r["ext"] == ".ai":
        print(f"  size={r['size']} path={r['rel']} head={r['head'][:80]!r}")
print("\n=== TOP 90 DIRECTIVES ===")
for k, c in kw.most_common(90):
    print(f"  {c:7d}  {k:44s} files={len(kw_files[k])}")
