# -*- coding: utf-8 -*-
"""Third pass: the forward-slash spelling of the dead workspace.

`D:\\Software\\DeepSeek Harness\\工作区2` and
`D:/Software/DeepSeek Harness/工作区2` are the same directory, but the first two
passes only matched the backslash form.  Four probes build paths with forward
slashes and were still pointing at a directory that no longer exists.

Same preamble contract as the other two passes.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEAD_FWD = _HERE_PATH()
PAT = re.compile(r"""r?(["'])""" + re.escape(DEAD_FWD) + r"""(/[^"']{0,200})?\1""")

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
    body = lit[2:-1] if lit[0] == "r" else lit[1:-1]
    tail = body[len(DEAD_FWD):]
    parts = [p for p in tail.split("/") if p]
    quoted = ", ".join('"%s"' % p for p in parts)
    return "%s(%s)" % (fn, quoted) if parts else "%s()" % fn


def _insert_prelude(lines, is_root):
    last_import = -1
    for i, line in enumerate(lines):
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
    if DEAD_FWD not in text:
        return ("skip", rel, "no forward-slash dead path")

    lines = text.splitlines(True)
    changed = 0
    out = []
    for line in lines:
        if line.lstrip().startswith("#") or not PAT.search(line):
            out.append(line)
            continue
        new = PAT.sub(lambda m: _replacement(m, is_root), line)
        if new != line:
            changed += 1
        out.append(new)
    if not changed:
        return ("skip", rel, "nothing executable")
    new_text = "".join(out)
    want = "_ROOT_PATH" if is_root else "_HERE_PATH"
    if want not in new_text:
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
