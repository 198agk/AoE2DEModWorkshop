# -*- coding: utf-8 -*-
"""Census: which assertions still match an English WARNING or REFUSAL string?

The project has converted player-facing sentences to Chinese in several
rounds.  Each round, the product side moved and some probe kept matching the
old English wording -- and a probe whose marker no longer appears does not
fail loudly, it reports a WRONG number or silently passes everything.  This
census finds the remaining suspects so a person can look at them.

What counts as a suspect: a call whose first argument is a *sentence* (not a
code) and whose expected substring is pure ASCII words of length >= 4.  It is
a census, not a test: it prints and exits 0 either way, because "how many are
left" is a number to read, not a pass/fail question.
"""
import ast
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

# Substrings that are NOT natural-language wording: they are codes, identifiers,
# units, or shapes that no translation round would touch.
_CODEISH = (
    "reason_code", "_", "%", ".py", ".dat", ".json", ".sld", "0..", "utf",
    "class ", "unit ", "tech ", "slot", "resource", "label",
)


def _ascii_words(s):
    words = [w for w in s.replace("\u3000", " ").split() if w.isascii()]
    return words, all(len(w) >= 4 and w.isalpha() for w in words)


def _sentence_args(call):
    """Yield (index, value) for the sentence-ish string args of one call."""
    for i, node in enumerate(call.args):
        if not isinstance(node, ast.Constant):
            continue
        val = node.value
        if not isinstance(val, str) or not val.strip():
            continue
        yield i, val


def scan(path):
    out = []
    try:
        tree = ast.parse(open(path, encoding="utf-8", newline="").read(), path)
    except (SyntaxError, UnicodeDecodeError):
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        args = list(_sentence_args(node))
        if len(args) < 2:
            continue
        # The LAST constant arg is the usual "want" marker; earlier ones are the
        # subject (a tech name, a file path...).  Only look at the last.
        idx, want = args[-1]
        if any(c in want for c in _CODEISH):
            continue
        words, sentencey = _ascii_words(want)
        if not words or not sentencey:
            continue
        if len(" ".join(words)) < 8:
            continue
        out.append((node.lineno, want))
    return out


def main():
    hits = 0
    files = 0
    for name in sorted(os.listdir(_HERE)):
        if not name.startswith("test_") or not name.endswith(".py"):
            continue
        path = os.path.join(_HERE, name)
        found = scan(path)
        if not found:
            continue
        files += 1
        print("\n%s" % name)
        for lineno, want in found:
            hits += 1
            print("  %4d  %r" % (lineno, want))
    print("\n%d English-looking markers in %d probe files" % (hits, files))
    print("Each one is a claim: either the sentence is still English on screen,")
    print("or this marker stopped matching when the sentence was translated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
