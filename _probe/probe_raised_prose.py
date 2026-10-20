# -*- coding: utf-8 -*-
"""How much ENGLISH can still reach the screen through a refusal?

WHY THIS EXISTS
===============
The screen prints the product's own sentences verbatim -- `index.html:632` puts
`c.preview.error` in a `.why` div.  `App._safe_plan()` fills that field from
`"%s: %s" % (type(exc).__name__, exc)`, so EVERY `raise IntentError("...")`
message in this package is player-facing text.  `test_prose_language.py` only
walks `description` / `reason` / `warnings`, so nothing has ever checked this
surface.

This measures before anyone edits: it parses every module, finds the string
literals handed to the exception constructors, and classifies them.  It is a
census, not a test -- run it, read the counts, then decide.

A COUNT IS NOT REACHABILITY.  Most of what this prints is a programming-contract
message ("an intent must be a dict", "unhandled width %d") that no sentence a
player types can reach.  Reachability is measured by
`_probe/probe_player_refusals.py`, and the reachable ones are pinned by the
fourth surface of `_probe/test_prose_language.py`.  Treat a fall in this file's
`english` count as no evidence at all that the screen got better.
"""
import ast
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\Software\AI\帝国项目\aoe2mod"
CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]{3,}")
EXC = {"IntentError", "ModError", "RuntimeError", "ValueError", "UnsupportedVersionError"}


def literals(node):
    """Every string constant inside an expression, including %-templates."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


def main():
    rows = []          # (module, line, kind, text)
    for base, _dirs, files in os.walk(ROOT):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, os.path.dirname(ROOT))
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
            except SyntaxError as exc:
                print("SKIP %s: %s" % (rel, exc))
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Raise) or node.exc is None:
                    continue
                exc = node.exc
                if isinstance(exc, ast.Call):
                    fn = exc.func
                    label = getattr(fn, "id", None) or getattr(fn, "attr", None)
                    if label not in EXC:
                        continue
                    text = "".join(literals(exc))
                else:
                    label = getattr(exc, "id", None) or getattr(exc, "attr", None)
                    if label not in EXC:
                        continue
                    text = ""
                if not text:
                    continue
                has_cjk = bool(CJK.search(text))
                has_latin = bool(LATIN.search(text))
                kind = "chinese" if has_cjk and not has_latin else (
                    "english" if has_latin and not has_cjk else
                    ("mixed" if has_latin else "chinese"))
                rows.append((rel, node.lineno, kind, " ".join(text.split())))

    counts = {}
    for _r, _l, k, _t in rows:
        counts[k] = counts.get(k, 0) + 1
    print("raised-message literals: %d" % len(rows))
    print("counts: %r" % (counts,))
    for want in ("english", "mixed"):
        bad = [r for r in rows if r[2] == want]
        if not bad:
            continue
        print("\n--- %s (%d) ---" % (want, len(bad)))
        for rel, line, _k, text in bad:
            print("%s:%d  %s" % (rel, line, text[:140]))
    return 0 if counts.get("english", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
