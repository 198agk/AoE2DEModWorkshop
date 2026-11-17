# -*- coding: utf-8 -*-
"""Does stripping comments and docstrings leave the program alone?

The seal step rewrites every shipped module before compiling it: comments go
away, docstrings become "" so line numbers stay put.  Nothing else may change.
That is not a style preference -- it is the difference between the shipped
engine and the source it claims to be.

It changed once.  The stripper decided "is this string a docstring?" by asking
"is the token before it a colon or a newline?", and those two tests are true
for every dict value and for every value written on its own line inside
braces.  So 64 of 109 modules shipped with their dict values emptied:

    {"why": "%s table unreadable: %s" % (table, exc)}
    -> {"why": "" % (table, exc)}

which parses, compiles, and then raises "TypeError: not all arguments
converted during string formatting" the first time that message is built --
from a line that no longer exists on disk, in a folder that has no source.
The sealed engine answered civs=63 and every route the gate checked, because
those lines are only reached on an upgrade check.  That is the whole shape of
this bug: it hides behind routes nobody exercised.

The test is a comparison of ASTs with every bare string expression removed
from both sides.  A docstring IS a bare string expression, so dropping them
from both trees means the two must then be identical -- any other difference
is code that was changed.
"""
import ast
import io
import os
import sys
import tokenize

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "_probe", "protect"))

import seal  # noqa: E402

FAIL = []


def check(name, ok, detail=None):
    if ok:
        print("  ok   %s" % name)
        return
    FAIL.append(name + ("" if detail is None else " :: %s" % (detail,)))
    print("  FAIL %s%s" % (name, "" if detail is None else " :: %s" % (detail,)))


def prune(tree):
    """Remove every bare string expression -- i.e. every docstring."""
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            seq = getattr(node, field, None)
            if isinstance(seq, list) and seq:
                keep = [s for s in seq
                        if not (isinstance(s, ast.Expr)
                                and isinstance(s.value, ast.Constant)
                                and isinstance(s.value.value, str))]
                setattr(node, field, keep or [ast.Pass()])
        for handler in getattr(node, "handlers", None) or ():
            keep = [s for s in handler.body
                    if not (isinstance(s, ast.Expr)
                            and isinstance(s.value, ast.Constant)
                            and isinstance(s.value.value, str))]
            handler.body = keep or [ast.Pass()]
    return tree


def old_strip(text):
    """The stripper that shipped 64 broken modules, kept so the test can prove
    it would fail.  A regression test that only ever exercises the fixed code
    cannot tell you the fix is load-bearing."""
    lines = text.splitlines(True)
    toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    anchors = (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL)
    prev = None
    docs = []
    for t in toks:
        if t.type == tokenize.COMMENT:
            row = t.start[0]
            if row - 1 < len(lines):
                lines[row - 1] = lines[row - 1][:t.start[1]].rstrip() + "\n"
            continue
        if t.type == tokenize.STRING:
            if (prev is None or prev.type in anchors
                    or (prev.type == tokenize.OP and prev.string == ":")):
                docs.append(t)
            prev = t
            continue
        if t.type in (tokenize.NL, tokenize.COMMENT):
            continue
        prev = t
    for t in reversed(docs):
        r0, c0 = t.start
        r1, c1 = t.end
        if r0 - 1 >= len(lines) or r1 - 1 >= len(lines):
            continue
        head = lines[r0 - 1][:c0]
        tail = lines[r1 - 1][c1:]
        if r0 == r1:
            lines[r0 - 1] = head + '""' + tail
        else:
            lines[r0 - 1] = head + '""' + "\n"
            for row in range(r0 + 1, r1 + 1):
                if row - 1 < len(lines):
                    lines[row - 1] = "\n"
    return "".join(lines)


def same_meaning(before, after):
    try:
        want = ast.dump(prune(ast.parse(before)))
    except SyntaxError as exc:
        return "the original does not parse: %s" % (exc,)
    try:
        got = ast.dump(prune(ast.parse(after)))
    except SyntaxError as exc:
        return "the stripped copy does not parse: %s" % (exc,)
    return None if got == want else "the code is not the same after stripping"


def _any_const(code, needle):
    """Does this compiled code (or any code nested inside it) hold `needle`?"""
    import marshal
    import types
    if isinstance(code, (bytes, bytearray)):
        try:
            code = marshal.loads(code)
        except Exception:
            return False
    if not isinstance(code, types.CodeType):
        return False
    for const in code.co_consts:
        if isinstance(const, str) and const == needle:
            return True
        if isinstance(const, types.CodeType) and _any_const(const, needle):
            return True
    return False


def _read_pack(pack, cfg):
    """Decrypt engine.pak without booting it, keyed the way seal.py keyed it."""
    import hashlib
    import json
    import zlib
    raw = open(pack, "rb").read()
    if raw[:8] != b"AOE2PAK1":
        return {}
    hlen = int.from_bytes(raw[8:12], "little")
    head = json.loads(raw[12:12 + hlen].decode("utf-8"))
    base = 12 + hlen
    key = hashlib.sha256(b"aoe2mod-pack-v1|" + bytes.fromhex(cfg.MASTER)
                         + b"|" + cfg.BUYER.encode()).digest()
    out = {}
    for it in head["items"]:
        blob = raw[base + it["off"]:base + it["off"] + it["len"]]
        ks = hashlib.shake_256(key + bytes.fromhex(it["nonce"])).digest(len(blob))
        pt = (int.from_bytes(blob, "big") ^ int.from_bytes(ks, "big")).to_bytes(len(blob), "big")
        out[it["name"]] = (it["kind"], it["pkg"], zlib.decompress(pt))
    return out


def main():
    print("stripping: does it only take away comments and docstrings?")

    # 1. the shapes that broke it, spelled out.
    cases = [
        ('d = {"why": "%s broken" % (t,)}',
         "a dict value with a % argument right after the colon"),
        ('d = {"why": "one line "' + "\n" + '          "two" % (t,)}',
         "the same value continued on the next line inside the braces"),
        ("x = {\n    'k': 'v',\n}",
         "a value on its own line inside a dict literal"),
        ("def f():\n    'doc'\n    return 1\n",
         "a real docstring is still removed"),
    ]
    for src, why in cases:
        problem = same_meaning(src, seal.strip_source(src))
        check(why, problem is None, problem)

    # 2. the fixed stripper is tested against the bug it fixes.
    broken_src = 'd = {"why": "%s broken" % (t,)}'
    check("the old stripper would fail this test",
          same_meaning(broken_src, old_strip(broken_src)) is not None,
          "old_strip is no longer the bug it was; the test is not proving anything")

    # 3. every module that actually gets shipped.
    root = os.path.join(HERE, "aoe2mod")
    tools_dir = os.path.join(HERE, "tools")
    bad = []
    seen = 0
    for base in (root, tools_dir):
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                text = open(path, "r", encoding="utf-8", errors="replace").read()
                seen += 1
                problem = same_meaning(text, seal.strip_source(text))
                if problem is not None:
                    bad.append("%s :: %s" % (os.path.relpath(path, HERE), problem))
    check("every shipped module keeps its meaning (%d files)" % seen,
          not bad, bad[:6])

    # 4. and the shipped pack really contains the fixed text, not just the
    #    repo.  This is the step that was missing when the broken engine went
    #    out: seal.py was correct-looking, the pack was built from it, and the
    #    only test ran against source.
    pack = os.path.join(HERE, "_cache", "sealed", "app", "runtime", "engine.pak")
    check("the sealed pack exists to inspect", os.path.isfile(pack), pack)
    if os.path.isfile(pack):
        cfg_dir = os.path.join(os.path.dirname(pack))
        sys.path.insert(0, cfg_dir)
        import _rt_cfg as cfg                       # noqa: E402
        mods = _read_pack(pack, cfg)
        check("the pack still names every module it should",
              "aoe2mod.mod.upgrade" in mods, len(mods))
        # The exact string that used to be emptied.  The bug turned
        # {"why": "「%s」表读不出来：%s" % (table, exc)} into {"why": "" % (table, exc)},
        # so the format string itself disappeared from the compiled code.  Its
        # presence is the difference between an engine that explains a refusal
        # and one that raises TypeError on the way to explaining it.
        item = mods.get("aoe2mod.mod.upgrade")
        # A whole dict value, picked because the old stripper emptied exactly
        # this shape: the string sits right after a colon, so the "prev token is
        # a colon" test called it a docstring and replaced it with "".
        needle = "落在文明 %s 的头部字段缝隙里（布局说法不一致）"
        found = bool(item) and _any_const(item[2], needle)
        check("the shipped upgrade module still carries its dict values", found,
              "a dict value is gone from the compiled pack" if item else "no module")

    print("")
    if FAIL:
        print("STRIP NEUTRALITY: %d CHECK(S) FAILED" % len(FAIL))
        for f in FAIL:
            print("  - " + f)
        return 1
    print("STRIP NEUTRALITY: COMMENTS AND DOCSTRINGS GO, THE PROGRAM STAYS -- AND "
          "THE OLD STRIPPER WOULD STILL FAIL THIS, SO THE TEST IS LOAD-BEARING")
    return 0


if __name__ == "__main__":
    sys.exit(main())