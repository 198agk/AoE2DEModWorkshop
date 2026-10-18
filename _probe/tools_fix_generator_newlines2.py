# -*- coding: utf-8 -*-
"""Add newline="\\n" to every write-mode `open(...)` that lacks it.

The first version of this patcher used a regex that demanded no parentheses in
the arguments, so it silently skipped every call whose path was built with
`os.path.join(...)` -- which is most of them.  It reported "5 writes across 3
generators" and left `build_semantic.py` and `build_schema.py` untouched, and
those two are exactly the ones producing unit_names.json / tech_names.json /
armor_classes.json / effect_attributes.json / effect_command_types.json.

That is the same failure shape this whole cleanup is about: a tool that reports
success while doing part of the job.  So this version scans for balanced
parentheses, which is the only way to see the real argument list.
"""
import io
import glob
import os

ROOT = r"D:\Software\AI\帝国项目"
SKIP = ("tools_fix_", "tools_regen_")


def _calls(text):
    """Yield (start, end) of each `open(` ... matching `)`."""
    i = 0
    while True:
        i = text.find("open(", i)
        if i < 0:
            return
        if i and (text[i - 1].isalnum() or text[i - 1] in "._"):
            i += 5
            continue
        depth = 0
        j = i + 4
        while j < len(text):
            ch = text[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    yield i, j
                    break
            elif ch in "\"'":
                q = ch
                j += 1
                while j < len(text) and text[j] != q:
                    if text[j] == "\\":
                        j += 1
                    j += 1
            j += 1
        i = j + 1


def patch(path):
    text = io.open(path, encoding="utf-8").read()
    edits = []
    for start, end in _calls(text):
        inner = text[start + 5:end]
        if "newline" in inner:
            continue
        # a write-mode literal must be present
        if not ("'w'" in inner or '"w"' in inner):
            continue
        edits.append((start, end, inner))
    if not edits:
        return 0
    for start, end, inner in reversed(edits):
        text = text[:end] + ', newline="\\n"' + text[end:]
    compile(text, path, "exec")
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return len(edits)


def main():
    total = files = 0
    for pat in ("_probe/schema/*.py", "_probe/semantic/*.py"):
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            name = os.path.basename(p)
            if name.startswith(SKIP):
                continue
            n = patch(p)
            if n:
                files += 1
                total += n
                print("  %-46s %d write(s)" % (name, n))
    print()
    print("patched %d write(s) across %d generator(s)" % (total, files))


if __name__ == "__main__":
    main()
