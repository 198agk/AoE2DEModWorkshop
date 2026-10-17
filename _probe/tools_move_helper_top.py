# -*- coding: utf-8 -*-
"""Move the `_HERE_PATH` helper to where it is actually available.

The bulk rewrite inserted the helper after the LAST top-level import.  That is
the right place for ordinary code, but the line that needs it is

    sys.path.insert(0, <the old workspace>)

which sits BEFORE the imports, because its whole job is to make them resolve.
So 95 files now raise `NameError: name '_HERE_PATH' is not defined` on the very
first useful line -- and only when run, never when imported, which is why the
suite had not noticed yet.

The helper is three trivial lines with no dependencies, so the correct place is
immediately after the module docstring: before every statement, after the
docstring so `__doc__` survives.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HELPER_LINES = (
    "import os as _os\n",
    "_HERE_PATH = lambda *p: _os.path.join(\n",
    "    _os.path.dirname(_os.path.abspath(__file__)), *p)\n",
    "_ROOT_PATH = lambda *p: _os.path.join(\n",
    "    _os.path.dirname(_os.path.abspath(__file__)), *p)\n",
)
# the old block, in both spellings the earlier passes produced
OLD_BLOCK = re.compile(
    r"import os as _os\r?\n"
    r"_(?:HERE|ROOT)_PATH = lambda \*p: _os\.path\.join\(\r?\n"
    r"    _os\.path\.dirname\(_os\.path\.abspath\(__file__\)\), \*p\)\r?\n",
    re.M,
)
USES = re.compile(r"_(?:HERE|ROOT)_PATH\b")


def find_docstring_end(lines):
    """Return the index just after a leading module docstring, else 0."""
    i = 0
    # skip a shebang, a coding cookie and blank lines
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("#") or not s:
            i += 1
            continue
        break
    if i >= len(lines):
        return 0
    for d in ('"""', "'''"):
        if lines[i].lstrip().startswith(d):
            # single-line docstring?
            body = lines[i].lstrip()[3:]
            if d in body:
                return i + 1
            j = i + 1
            while j < len(lines):
                if d in lines[j]:
                    return j + 1
                j += 1
            return i + 1
    return 0


def process(path, dry=False):
    rel = os.path.relpath(path, ROOT)
    try:
        text = io.open(path, encoding="utf-8").read()
    except Exception as exc:
        return ("skip", rel, str(exc))
    if not USES.search(text):
        return ("skip", rel, "no helper use")

    had_block = bool(OLD_BLOCK.search(text))
    stripped = OLD_BLOCK.sub("", text)
    # collapse the blank line the earlier pass left behind
    stripped = re.sub(r"\n\n\n+", "\n\n", stripped)

    lines = stripped.splitlines(True)
    at = find_docstring_end(lines)
    block = list(HELPER_LINES)
    if at > 0:
        block = ["\n"] + block
    new_lines = lines[:at] + block + lines[at:]
    new = "".join(new_lines)
    new = re.sub(r"\n\n\n+", "\n\n", new)

    if new == text:
        return ("skip", rel, "already at the top")
    try:
        compile(new, path, "exec")
    except SyntaxError as exc:
        return ("BAD", rel, "would not parse: %s" % exc)
    if not dry:
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    return ("ok", rel, "moved (removed old block: %s)" % had_block)


def main(argv):
    dry = "--dry" in argv
    ok = bad = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in sorted(files):
            if not f.endswith(".py") or f.startswith("tools_"):
                continue
            status, rel, note = process(os.path.join(root, f), dry=dry)
            if status == "ok":
                ok += 1
                print("  OK   %-58s %s" % (rel, note))
            elif status == "BAD":
                bad += 1
                print("  BAD  %-58s %s" % (rel, note))
    print()
    print("moved %d, refused %d%s" % (ok, bad, " (dry run)" if dry else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
