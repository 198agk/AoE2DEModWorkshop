# -*- coding: utf-8 -*-
"""Make `tools/sync_engine.py` stop rewriting line endings.

Why this matters
----------------
`sync_engine.py` is the vendoring contract: it copies the research sources in
`_probe/` into `aoe2mod/` and then proves the copy byte-identical by sha256.

On Windows, `open(path, "w", encoding="utf-8")` translates every `\\n` into
`\\r\\n`.  The sources are LF.  So the copy is NOT byte-identical, the sha256
assertion fails... except it does not, because the assertion compares the
research file to the copy with the same translation applied, or reads the copy
back through `str` and hashes that.  Either way the contract passed while the
tree on disk gained 668 CRLF in locate.py and 56,854 in unit_names.json.

Visible consequence: `git status` showed 13 vendored files as fully rewritten
(107,057 +/-).  Normalising EOL makes them identical, so nothing was lost --
but a 200k-line diff is where a real change goes to hide.

This patch adds `newline=""` (or `newline="\\n"` where the output is generated
text rather than a copy) to the three writes that produce vendored artifacts.
"""
import io

PATH = r"D:\Software\AI\帝国项目\tools\sync_engine.py"

EDITS = (
    (
        '    with open(dst, "w", encoding="utf-8") as fh:\n'
        "        fh.write(out)",
        "    # newline=\"\" keeps the source's own line endings.  Without it Windows\n"
        "    # rewrites every \\n as \\r\\n, so a byte-identical copy shows up in git\n"
        "    # as a whole-file diff while the sha256 provenance still passes -- the\n"
        "    # two checks disagreed because only one of them looked at bytes.\n"
        '    with open(dst, "w", encoding="utf-8", newline="") as fh:\n'
        "        fh.write(out)",
    ),
    (
        '    with open(dst, "w", encoding="utf-8") as fh:\n'
        "        fh.write(header + body)",
        '    with open(dst, "w", encoding="utf-8", newline="") as fh:\n'
        "        fh.write(header + body)",
    ),
    (
        '    with open(mp, "w", encoding="utf-8") as fh:\n'
        "        json.dump(manifest, fh, indent=2)",
        '    with open(mp, "w", encoding="utf-8", newline="\\n") as fh:\n'
        "        json.dump(manifest, fh, indent=2)",
    ),
)


def main():
    text = io.open(PATH, encoding="utf-8").read()
    for old, new in EDITS:
        n = text.count(old)
        if n != 1:
            raise SystemExit("expected 1 match, found %d for:\n%s" % (n, old))
        text = text.replace(old, new)
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("patched %s (%d writes now bypass newline translation)"
          % (PATH, len(EDITS)))


if __name__ == "__main__":
    main()
