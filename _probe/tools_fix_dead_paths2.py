# -*- coding: utf-8 -*-
"""Second pass: the shapes the first rewrite deliberately skipped.

The first pass handled `r"D:\\...\\工作区2\\..."` with a double-quoted raw
literal on a single line.  What is left:

  * single-quoted literals  `r'D:\\...\\工作区2\\_probe\\out.txt'`
  * string concatenation    `"D:\\...\\工作区2" + os.sep + "x"`
  * docstrings naming the   (left alone on purpose -- the history is readable
    old directory            and the text is a record, not a path)

Same preamble contract as `tools_fix_dead_paths.py`.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEAD = "D:" + os.sep + "Software" + os.sep + "DeepSeek Harness" + os.sep + "工作区2"
# double OR single quoted, raw or not, closing quote required
DEAD_PREFIX = re.compile(
    r"""r?(["'])""" + re.escape(DEAD) + r"""(?:\\[^"']{0,200})?\1"""
)

PRELUDE = (
    "import os as _os\n"
    "_HERE_PATH = lambda *p: _os.path.join(\n"
    "    _os.path.dirname(_os.path.abspath(__file__)), *p)\n"
)
PRELUDE_ROOT = (
    "import os as _os\n"
    "_ROOT_PATH = lambda *p: _os.path.join(\n"
    "    _os.path.dirname(_os.path.abspath(__file__)), *p)\n"
)


def _replacement(match, is_root):
    fn = "_ROOT_PATH" if is_root else "_HERE_PATH"
    lit = match.group(0)
    q = lit[1]
    body = lit[2:-1] if lit[0] == "r" else lit[1:-1]
    tail = body[len(DEAD):]
    parts = [p for p in tail.replace("/", "\\").split("\\") if p]
    quoted = ", ".join('"%s"' % p for p in parts)
    return "%s(%s)" % (fn, quoted) if parts else "%s()" % fn


def _needs_prelude(text, is_root):
    return ("_ROOT_PATH" if is_root else "_HERE_PATH") not in text


def _insert_prelude(lines, is_root):
    last_import = -1
    in_doc = False
    for i, line in enumerate(lines):
        s = line.strip()
        if not in_doc and (s.startswith('"""') or s.startswith("'''")):
            q = s[:3]
            if s.count(q) < 2:
                in_doc = True
            continue
        if in_doc:
            if '"""' in s or "'''" in s:
                in_doc = False
            continue
        if re.match(r"^(import |from \S+ import )", line):
            last_import = i
    at = last_import + 1 if last_import >= 0 else 0
    block = (PRELUDE_ROOT if is_root else PRELUDE).splitlines(True)
    return lines[:at] + ["\n"] + block + lines[at:]


def process(path, dry=False):
    rel = os.path.relpath(path, ROOT)
    is_root = os.path.dirname(path) == ROOT
    try:
        text = io.open(path, encoding="utf-8").read()
    except Exception as exc:
        return ("skip", rel, "cannot read: %s" % exc)
    if DEAD not in text:
        return ("skip", rel, "no dead path")

    lines = text.splitlines(True)
    changed = 0
    out = []
    in_doc = False
    for line in lines:
        stripped = line.lstrip()
        if not in_doc and (stripped.startswith('"""') or stripped.startswith("'''")):
            q = stripped[:3]
            out.append(line)
            if stripped.count(q) < 2:
                in_doc = True
            continue
        if in_doc:
            out.append(line)
            if '"""' in line or "'''" in line:
                in_doc = False
            continue
        if stripped.startswith("#") or not DEAD_PREFIX.search(line):
            out.append(line)
            continue
        new = DEAD_PREFIX.sub(lambda mm: _replacement(mm, is_root), line)
        if new != line:
            changed += 1
        out.append(new)

    if not changed:
        return ("skip", rel, "only comments/docstrings")

    new_text = "".join(out)
    if _needs_prelude(new_text, is_root):
        out = _insert_prelude(out, is_root)
        new_text = "".join(out)
    try:
        compile(new_text, path, "exec")
    except SyntaxError as exc:
        return ("BAD", rel, "would not parse: %s" % exc)
    if not dry:
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
    return ("ok", rel, "%d line(s)" % changed)


def main(argv):
    dry = "--dry" in argv
    ok = bad = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            status, rel, note = process(os.path.join(root, f), dry=dry)
            if status == "ok":
                ok += 1
                print("  FIXED  %-58s %s" % (rel, note))
            elif status == "BAD":
                bad += 1
                print("  BAD    %-58s %s" % (rel, note))
    print()
    print("rewritten %d, refused %d%s" % (ok, bad, " (dry run)" if dry else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
