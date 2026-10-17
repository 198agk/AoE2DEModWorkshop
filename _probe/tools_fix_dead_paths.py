# -*- coding: utf-8 -*-
"""Rewrite every hardcoded reference to the dead workspace into a derived path.

What this is fixing
-------------------
The workspace lived at `D:\\Software\\DeepSeek Harness\\工作区2` -- inside the
application install directory -- and an update wiped it.  The project now lives
at `D:\\Software\\AI\\帝国项目`.  About 170 files still name the old directory,
and they fail in the quiet way this project has paid for repeatedly: a script
writes into a directory that no longer exists, or `os.makedirs` recreates it,
and the script exits 0 while producing nothing anyone reads.

What it does
------------
Every occurrence becomes a path derived from the file's own location:

    r"D:\\Software\\DeepSeek Harness\\工作区2\\_probe\\out_x"
      -> _HERE_PATH("_probe", "out_x")

with a two-line preamble inserted once per file (after the last top-level
`import`, before the first other statement):

    import os as _os
    _HERE_PATH = lambda *p: _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), *p)

Files at the repository root get `_ROOT_PATH` instead (their `__file__` dir IS
the root), so a root-level script's `_probe\\x` still resolves to the real one.

`sys.path.insert(0, <dead>)` becomes `sys.path.insert(0, <root>)` computed the
same way, because the package really does live at the root.

What it does NOT do
-------------------
It does not touch the string when it appears inside a docstring sentence (the
history is worth keeping readable) -- only executable lines.  It does not fix
scripts that reference artifacts which no longer exist under any root; those
stay broken and stay honest about it.

Run with `--dry` to see the plan without writing.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEAD = "D:" + os.sep + "Software" + os.sep + "DeepSeek Harness" + os.sep + "工作区2"
# Match the WHOLE literal, including the closing quote.  An earlier version
# stopped at the dead root and then split the remainder on backslashes, which
# left the closing `"` glued to the last path segment and produced
# `"_probe", "out_x""` -- 346 files refused to parse.  That refusal was the
# guard working: nothing was written.
DEAD_PREFIX = re.compile(r'r?"' + re.escape(DEAD) + r'(?:\\[^"]{0,200})?"')
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
    body = lit[2:-1] if lit.startswith('r"') else lit[1:-1]
    tail = body[len(DEAD):]
    # `tail` is everything after the dead root: "", "\\_probe\\out_x", ...
    parts = [p for p in tail.replace("/", "\\").split("\\") if p]
    quoted = ", ".join('"%s"' % p for p in parts)
    return '%s(%s)' % (fn, quoted) if parts else '%s()' % fn


def _is_docstring_or_comment(line):
    s = line.lstrip()
    return s.startswith("#") or s.startswith('"""') or s.startswith("'''")


_STR_CONT = re.compile(r'^\s*r?["\']')


def _joins_next(lines, i, match):
    """True when this literal is split across lines by implicit concatenation.

    `MINE = (r"D:\\...\\_probe\\out_smoke2\\resources\\_common\\dat"`
    `        r"\\futuravailableunits.json")`

    Rewriting the first half into a call leaves the second half dangling and the
    file stops parsing.  Those two-line literals are rare and worth reading by
    hand, so this reports them instead of guessing a join.
    """
    rest = lines[i][match.end():].strip()
    if rest and not rest.startswith((")", ",", "]", "#")):
        return True
    if not rest and i + 1 < len(lines) and _STR_CONT.match(lines[i + 1]):
        return True
    return False


def _needs_prelude(text, is_root):
    want = "_ROOT_PATH" if is_root else "_HERE_PATH"
    return want not in text


def _insert_prelude(lines, is_root):
    """Put the helper after the last top-level import, before anything else."""
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
    if not DEAD_PREFIX.search(text):
        return ("skip", rel, "no dead path")

    lines = text.splitlines(True)
    changed = 0
    out = []
    in_doc = False
    for i, line in enumerate(lines):
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
        m = DEAD_PREFIX.search(line)
        if _is_docstring_or_comment(line) or not m:
            out.append(line)
            continue
        if _joins_next(lines, i, m):
            return ("BAD", rel, "path literal continues on the next line; "
                                "fix by hand (line %d)" % (i + 1))
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

    # Refuse to write anything that no longer parses.
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
    ok = bad = skipped = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            status, rel, note = process(p, dry=dry)
            if status == "ok":
                ok += 1
                print("  FIXED  %-58s %s" % (rel, note))
            elif status == "BAD":
                bad += 1
                print("  BAD    %-58s %s" % (rel, note))
            else:
                skipped += 1
    print()
    print("rewritten %d, refused %d, untouched %d%s"
          % (ok, bad, skipped, " (dry run)" if dry else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
