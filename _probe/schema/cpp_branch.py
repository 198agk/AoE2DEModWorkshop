# -*- coding: utf-8 -*-
"""cpp_branch.py -- extract a version-conditional AGE list for AoE2:DE.

AGE's ``Lists.cpp`` builds its combo tables with runtime ``if/else`` on
``GenieVersion`` and ``isAoE2DE``.  A naive "grab every .Add(\"...\") in the
file" harvests *every* engine's names and then resolves the collisions by
last-write-wins -- which is exactly backwards for the ids where AGE puts the
correct branch first (attribute 19, 101, 104-106, and the whole class table).

This module walks the real branch structure and evaluates each condition for
the AoE2:DE build.  An unrecognised condition RAISES instead of guessing, so a
future AGE revision cannot silently change what we ship.

Ground truth for the constants is ``aoe2mod/dat/parser.py`` (the vendored,
byte-verified parser) plus AGE's own ``lists.h``.
"""
import re

# genie::GameVersion, transcribed VERBATIM from the enum in
# _probe/source/genieutils/include/genie/Types.h.  Order is load-bearing: AGE
# compares these with < and >=, so an invented value silently flips branches.
CONSTS = {
    "GV_None": 0, "GV_TEST": 1, "GV_MIK": 2, "GV_DAVE": 3, "GV_MATT": 4,
    "GV_AoEB": 5, "GV_AoE": 6, "GV_RoR": 7,
    "GV_Tapsa": 8, "GV_T2": 9, "GV_T3": 10, "GV_T4": 11, "GV_T5": 12,
    "GV_T6": 13, "GV_T7": 14, "GV_T8": 15,
    "GV_AoKE3": 16, "GV_AoKA": 17, "GV_AoKB": 18, "GV_AoK": 19,
    "GV_TC": 20, "GV_TCV": 21, "GV_Cysion": 22,
    "GV_C2": 23, "GV_C3": 24, "GV_C4": 25, "GV_CK": 26, "GV_C5": 27,
    "GV_C6": 28, "GV_C7": 29, "GV_C8": 30, "GV_C9": 31, "GV_C10": 32,
    "GV_C11": 33, "GV_C12": 34, "GV_C13": 35, "GV_C14": 36, "GV_C15": 37,
    "GV_C16": 38, "GV_C17": 39, "GV_C18": 40, "GV_C19": 41, "GV_C20": 42,
    "GV_C21": 43, "GV_C22": 44, "GV_C23": 45, "GV_C24": 46, "GV_C25": 47,
    "GV_C26": 48, "GV_C27": 49, "GV_C28": 50, "GV_C29": 51, "GV_C30": 52,
    "GV_C31": 53, "GV_C32": 54,
    "GV_SWGB": 55, "GV_CC": 56, "GV_CCV": 57, "GV_CCV2": 58,
    "GV_LatestTap": 15,          # genieutils: const GV_LatestTap = GV_T8
    "GV_LatestDE2": 54,          # genieutils: const GV_LatestDE2 = GV_C32
}
# AGE's own EditableVersion enum (_probe/source/AGE/EditableVersion.h), which is
# what `GameVersion` holds.  AoE2:DE is EV_DE2, so `GameVersion == EV_UP` is
# false here -- the UP-only branches must not win.
DE_GAMEVERSION = {
    "EV_ORIG": 0, "EV_TEST": 1, "EV_MIK": 2, "EV_DAVE": 3, "EV_MATT": 4,
    "EV_AoEB": 5, "EV_AoE": 6, "EV_RoR": 7, "EV_AoKE3": 8, "EV_AoKA": 9,
    "EV_AoKB": 10, "EV_AoK": 11, "EV_TC": 12, "EV_UP": 13, "EV_TCV": 14,
    "EV_Cysion": 15, "EV_SWGB": 16, "EV_CC": 17, "EV_EF": 18, "EV_EF2": 19,
    "EV_Tapsa": 20, "EV_DE2": 21,
}
DE_EDITION = "EV_DE2"
# AoE2:DE reports itself as GV_C32 (54) and sets isAoE2DE.
DE_GV = 54
DE_FLAGS = {"isAoE2DE": True, "isAoE1DE": False, "isSWGB": False, "isSWGBDE": False,
            "isAoE1": False, "isAoE2": True, "isHD": False, "isUP": True}


class UnsupportedCondition(Exception):
    """The source used a condition this extractor does not model."""


def _skip_ws(s, i):
    n = len(s)
    while i < n:
        if s[i] in " \t\r\n":
            i += 1
        elif s.startswith("//", i):
            j = s.find("\n", i)
            i = n if j < 0 else j + 1
        elif s.startswith("/*", i):
            j = s.find("*/", i)
            i = n if j < 0 else j + 2
        else:
            break
    return i


def _skip_string(s, i):
    i += 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            return i + 1
        i += 1
    raise ValueError("unterminated string literal")


def _balanced(s, i):
    """s[i] is '('; return the index just past its match."""
    depth = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            i = _skip_string(s, i)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced parentheses")


_CMP = re.compile(
    r"^(?P<lhs>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?P<op><=|>=|==|!=|<|>)\s*"
    r"(?:genie::)?(?P<rhs>[A-Za-z_][A-Za-z0-9_]*)$")


def eval_cond(cond):
    """Evaluate one AGE list condition for the AoE2:DE build."""
    cond = cond.strip()
    # strip a redundant outer paren pair
    while cond.startswith("(") and cond.endswith(")"):
        inner = cond[1:-1]
        if _balanced("(" + inner, 0) == len(inner) + 1:
            cond = inner.strip()
        else:
            break

    if cond in DE_FLAGS:
        return DE_FLAGS[cond]
    if cond in DE_GAMEVERSION:
        return DE_GAMEVERSION[cond]
    if cond.startswith("!"):
        return not eval_cond(cond[1:])
    for joiner, fn in (("||", any), ("&&", all)):
        if joiner in cond:
            parts = _split_top(cond, joiner)
            return fn(eval_cond(p) for p in parts)
    m = _CMP.match(cond)
    if not m:
        raise UnsupportedCondition(cond)
    lhs, op, rhs = m.group("lhs"), m.group("op"), m.group("rhs")
    if lhs == "GameVersion" or rhs == "GameVersion":
        other = rhs if lhs == "GameVersion" else lhs
        if other not in DE_GAMEVERSION:
            raise UnsupportedCondition(cond)
        lhs, rhs = "GameVersion", "GameVersion"       # compare in one namespace
        a = DE_GAMEVERSION[DE_EDITION]
        b = DE_GAMEVERSION[other]
    else:
        a = DE_GV if lhs == "GenieVersion" else CONSTS.get(lhs)
        b = DE_GV if rhs == "GenieVersion" else CONSTS.get(rhs)
    if a is None or b is None:
        raise UnsupportedCondition(cond)
    return {"<": a < b, "<=": a <= b, "==": a == b,
            "!=": a != b, ">": a > b, ">=": a >= b}[op]


def _split_top(text, joiner):
    """Split on a joiner that is not inside parentheses."""
    out, depth, start = [], 0, 0
    i = 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and text.startswith(joiner, i):
            out.append(text[start:i])
            i += len(joiner)
            start = i
            continue
        i += 1
    out.append(text[start:])
    return out


_ADD = re.compile(r'\s*\.Add\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)\s*;')
# .Add(cond ? "a" : "b");  -- AGE uses this so two engines' names share one slot
_TERNARY = re.compile(
    r'\s*\.Add\s*\(\s*(?P<cond>[^"?]+?)\s*\?\s*"(?P<a>(?:[^"\\]|\\.)*)"\s*:'
    r'\s*"(?P<b>(?:[^"\\]|\\.)*)"\s*\)\s*;')
_ANY_ADD = re.compile(r'\s*\.Add\s*\(')


class _Walker(object):
    def __init__(self, text, var):
        self.s = text
        self.var = var
        self.out = []
        self.end = None

    # ---- statements ------------------------------------------------------
    def run(self, i, emit=True):
        """Walk a statement SEQUENCE (not a brace block) to its end."""
        while True:
            i = _skip_ws(self.s, i)
            if i >= len(self.s):
                return i
            try:
                i = self.stmt(i, emit)
            except StopIteration:
                return i

    def block(self, i, emit=True):
        i = _skip_ws(self.s, i)
        if i < len(self.s) and self.s[i] == "{":
            i += 1
            while True:
                i = _skip_ws(self.s, i)
                if i >= len(self.s):
                    raise ValueError("unterminated block in %s" % self.var)
                if self.s[i] == "}":
                    return i + 1
                i = self.stmt(i, emit)
        return self.stmt(i, emit)

    def stmt(self, i, emit):
        i = _skip_ws(self.s, i)
        if re.match(r"if\s*\(", self.s[i:]):
            j = i + self.s[i:].index("(")
            k = _balanced(self.s, j)
            cond = self.s[j + 1:k - 1]
            take = eval_cond(cond)
            nxt = self.block(k, emit and take)
            p = _skip_ws(self.s, nxt)
            if self.s.startswith("else", p):
                e = _skip_ws(self.s, p + 4)
                return self.block(e, emit and not take)
            return nxt

        m = re.match(r"%s\s*\." % re.escape(self.var), self.s[i:])
        if not m:
            raise StopIteration
        j = i + m.end() - 1              # the '.'
        tail = self.s[j:]

        tm = _TERNARY.match(tail)
        if tm:
            if emit:
                pick = "a" if eval_cond(tm.group("cond")) else "b"
                self.out.append(tm.group(pick).replace('\\"', '"'))
            return j + tm.end()

        am = _ADD.match(tail)
        if am:
            if emit:
                self.out.append(am.group(1).replace('\\"', '"'))
            return j + am.end()

        # some other member call on the list: consume to the ';'
        if not _ANY_ADD.match(tail):
            raise StopIteration
        semi = self.s.find(";", j)
        if semi < 0:
            raise StopIteration
        return semi + 1


def extract(text, var):
    """Return every .Add() string visible in `var`'s DE branch, in order."""
    start = text.find(var + ".Clear();")
    if start < 0:
        raise ValueError("no %s.Clear(); in this source" % var)
    w = _Walker(text, var)
    w.run(start + len(var) + len(".Clear();"))
    return w.out


_NUM = re.compile(r"^(\d+)\s*-\s*(.*)$")


def by_number(strings):
    """Key an AGE list by the id in its label.

    AGE's lists carry the id in the text ("18 - Monk"); the sentinel entries
    ("No Class/Invalid Class") do not.  AoE2 DE stores that id as the value, so
    keying by list POSITION is off by however many branches collapsed -- see
    the module docstring.
    """
    out = {}
    for s in strings:
        m = _NUM.match(s)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def selftest():
    """Assert our constants agree with the vendored, byte-verified parser."""
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    sys.path.insert(0, root)
    from aoe2mod.dat import parser as P
    pairs = [("GV_AoEB", P.GV_AoEB), ("GV_AoKA", P.GV_AoKA), ("GV_AoKB", P.GV_AoKB),
             ("GV_TC", P.GV_TC), ("GV_Cysion", P.GV_Cysion),
             ("GV_SWGB", P.GV_SWGB), ("GV_CC", P.GV_CC), ("GV_C32", P.GV_C32)]
    for name, want in pairs:
        got = CONSTS[name]
        assert got == want, "%s: cpp_branch=%r parser=%r" % (name, got, want)
    assert CONSTS["GV_C32"] == DE_GV
    return True
