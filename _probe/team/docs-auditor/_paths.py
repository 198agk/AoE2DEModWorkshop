# -*- coding: utf-8 -*-
"""Extract backticked tokens that look like paths / API names from the three skills,
then report which files exist and which API names are absent from the attributed module."""
import sys, os, io, re, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd()

SKILLS = [
    ".dsh/skills/aoe2-de-dat/SKILL.md",
    ".dsh/skills/aoe2-de-sprites/SKILL.md",
    ".dsh/skills/aoe2-de-ui-textures/SKILL.md",
]

PATH_RE = re.compile(r"^[\w./\\\-\u4e00-\u9fff{}*<>]+\.(py|json|md|js|dat|sld|pal|xaml|txt|png|dds|xs|per|pck|slp|smp|box|conf|col|exe|gpv|sldx?)$", re.I)

rows = []
for rel in SKILLS:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            for m in re.finditer(r"`([^`]+)`", line):
                v = m.group(1).strip()
                if PATH_RE.match(v):
                    rows.append((rel, i, v))

seen = set()
dead = []
alive = []
for rel, i, v in rows:
    key = (rel, v)
    if key in seen:
        continue
    seen.add(key)
    # normalise: strip leading ./ and any {..} / * / <> pattern pieces
    cand = v.replace("\\", "/").lstrip("./")
    pat_parts = []
    if re.search(r"[{}*<>]", cand):
        # build a regex from the pattern
        rx = re.escape(cand)
        rx = rx.replace(r"\{", "(?:").replace(r"\}", ")")
        rx = rx.replace(r"\*", ".*")
        rx = rx.replace(r"\<\w+\>", ".*")
        rx = "^" + rx + "$"
        base_dir = os.path.dirname(cand) or "."
        found = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "_probe")]
            for fn in filenames:
                full = os.path.join(dirpath, fn).replace("\\", "/")
                if re.match(rx, full):
                    found.append(full)
        if found:
            alive.append((rel, i, v, found[0]))
        else:
            dead.append((rel, i, v, "glob matched 0 files"))
        continue
    full = os.path.join(ROOT, cand)
    if os.path.exists(full):
        alive.append((rel, i, v, cand))
    else:
        dead.append((rel, i, v, "MISSING"))

print("=== DEAD (glob/pattern) ===")
for d in dead:
    print("%-42s %4d  %-70s %s" % d)
print()
print("=== ALIVE count:", len(alive), " DEAD count:", len(dead))

with open("_probe/team/docs-auditor/paths.json", "w", encoding="utf-8") as fh:
    json.dump({"alive": alive, "dead": dead}, fh, ensure_ascii=False, indent=1)
