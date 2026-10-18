# -*- coding: utf-8 -*-
"""Resolve every backticked path token in the three skills + the project-state file map
against BOTH the workspace root and the game root, and report genuinely missing ones."""
import sys, os, io, re, json, fnmatch

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd()
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"

SKILLS = [
    ".dsh/skills/aoe2-de-dat/SKILL.md",
    ".dsh/skills/aoe2-de-sprites/SKILL.md",
    ".dsh/skills/aoe2-de-ui-textures/SKILL.md",
]

# index of workspace files (skip .git / __pycache__)
ws = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
    for fn in filenames:
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace("\\", "/")
        ws.setdefault(fn, []).append(rel)
        ws.setdefault(rel, [rel])

def game_index():
    idx = {}
    for dirpath, dirnames, filenames in os.walk(GAME):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, GAME).replace("\\", "/")
            idx.setdefault(fn, []).append(rel)
            idx.setdefault(rel, [rel])
    return idx
gidx = game_index()

PATH_RE = re.compile(r"^[\w./\\\-\u4e00-\u9fff{}*<>%]+\.(py|json|md|js|dat|sld|pal|xaml|txt|png|dds|xs|per|pck|slp|smp|box|conf|col|exe|gpv)$", re.I)

def resolve(tok):
    """Return list of (where, resolved) or empty."""
    t = tok.replace("\\", "/").lstrip("./")
    out = []
    for label, base, idx in (("ws", ROOT, ws), ("game", GAME, gidx)):
        if re.search(r"[{}*<>%]", t):
            pat = t
            for a, b in (("{", "*"), ("}", "*"), ("<", "*"), (">", "*"), ("%s", "*"), ("%d", "*")):
                pat = pat.replace(a, b)
            base_dir = os.path.dirname(pat)
            for k, v in idx.items():
                if "/" not in k:
                    continue
                if fnmatch.fnmatchcase(k, pat):
                    out.append((label, k))
                    break
            continue
        if os.path.exists(os.path.join(base, t)):
            out.append((label, t))
            continue
        # bare filename anywhere
        if "/" not in t and t in idx:
            out.append((label, idx[t][0]))
    return out

rows = []
for rel in SKILLS:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            for m in re.finditer(r"`([^`]+)`", line):
                v = m.group(1).strip()
                if PATH_RE.match(v):
                    rows.append((rel, i, v))

dead, alive = [], []
seen = set()
for rel, i, v in rows:
    k = (rel, v)
    if k in seen:
        continue
    seen.add(k)
    r = resolve(v)
    if r:
        alive.append((rel, i, v, r[0]))
    else:
        dead.append((rel, i, v))

print("RESOLVED:", len(alive), " UNRESOLVED:", len(dead))
print()
print("=== UNRESOLVED ===")
for rel, i, v in dead:
    print("%-40s %4d  %s" % (rel, i, v))

json.dump({"alive": alive, "dead": dead}, open("_probe/team/docs-auditor/paths.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
