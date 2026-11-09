# -*- coding: utf-8 -*-
"""Read, validate and write AoE2 DE AI (`.per`) and XS (`.xs`) scripts.

Why this module exists at all
-----------------------------
A player who wants to change AI behaviour today has to hand-edit a `.per` file
in a text editor with no help: no completion, no wrong-arity warning, no idea
which of the 192 `up-*` commands exist in THIS build.  The tool already ships a
sentence layer for `.dat` edits; scripts are the other half of "make the mod I
want", and they were the missing one.

The data it runs on
-------------------
``aoe2mod/data/ai_xs_lang.json`` is generated from two sources, and the file
records which source every fact came from so the UI can say so:

* **the game binary** (`AoE2DE_s.exe`) -- the command vocabulary and its RVAs,
  the 232 XS syscall prototypes, the XS keywords.  This is what proves a name
  exists in this build, and the RVA in the payload lets a later check re-verify.
* **the shipped scripts** under ``resources/_common/ai`` and ``xs`` -- the
  argument COUNT of each command, taken from 40,575 real call sites.

Argument count is the one field that must come from corpus, not from the binary:
the engine's dispatch table for `up-*`/base commands is not statically
reachable (18 independent scans found zero references to any command name), so
this project cannot derive arity by disassembly.  Deriving it from call sites is
not a guess -- it is the same evidence the game's own AI files use, and a
command whose call sites disagree is marked ambiguous instead of guessed.

Honesty boundary
----------------
``arity`` is ``None`` for 129 of the 324 names: 72 commands never appear in the
shipped scripts, and 7 (`chat-local`, `chat-to-all`, ...) are variadic by design
or used at more than one width.  For those, :func:`validate` does not invent an
argument count -- it reports ``arity unknown`` and stays silent.  A validator
that guessed would report false errors on correct scripts, which is worse than
saying nothing.
"""
import json
import os
import re

#: Where the generated vocabulary lives.  Kept beside the package so a build of
#: the tool carries it without needing the game installed.
DATA_REL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "ai_xs_lang.json")

#: Commands whose call sites in the shipped scripts disagree, so no single
#: argument count can be asserted.  Listed rather than silently swallowed: a
#: wrong arity here would produce red squiggles on correct code.
VARIADIC = frozenset((
    "chat-local-to-self", "chat-to-all", "chat-to-allies", "chat-to-player",
    "up-change-name", "up-chat-data-to-player", "up-chat-data-to-self",
))

#: `.per` structural keywords.  These are NOT in the command table because they
#: are handled by the loader before any command is dispatched.  `or`/`and`/`not`
#: are here for the same reason: they are combinators, not commands.
PER_KEYWORDS = frozenset((
    "defrule", "defconst", "defstrategic-number", "defrule-comment",
    "load", "load-if", "else", "endif", "end-if", "or", "and", "not",
    # Logic operators the grammar accepts in the position of a fact.  They are
    # in the payload's `ai_logic` table (from the binary) but not in the command
    # table, because they are combinators: `(nor (a) (b))` is not a command call.
    "nor", "nand", "xor", "xnor", "less-than", "less-or-equal",
    "greater-than", "greater-or-equal", "not-equal",
))

#: Bare literals the engine accepts where a fact would go.  `(true)` is the
#: "always" condition and appears in the shipped scripts on purpose; treating it
#: as a misspelled command would flag correct code.
PER_LITERALS = frozenset(("true", "false"))

#: Names the shipped corpus uses but the 59-name base-command block does not
#: contain.  `(build <unit>)` occurs 249 times across the game's own `.per`
#: files, yet `build` is absent from the command block at 0x032237f8..0x03223c60
#: -- it lives instead at 0x03213630 among `patrol` / `flag` / `Trade`, which is
#: the unit-order verb table, not the AI command table.  The engine therefore
#: dispatches it through a different path, and a vocabulary built only from the
#: AI command block would call correct code "unknown".
#:
#: Right now this set holds exactly one name: a corpus head that no table in the
#: binary claims.  It is kept explicit rather than auto-derived so the list
#: cannot silently grow into "whatever the corpus happens to contain".
CORPUS_EXTRA = frozenset(("build",))

_LOADIF = re.compile(r"^\s*#\s*(load-if|else|endif|end-if)\b(.*)$", re.I)


def load(path=None):
    """Read the vocabulary payload.  Raises if it is missing or malformed."""
    if path is None:
        #: A packager that moves the package must not break this lookup, so the
        #: relative location is derived from __file__, never from the cwd.
        path = os.environ.get("AOE2MOD_LANG_DATA") or DATA_REL
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class Vocab(object):
    """Query surface over one loaded vocabulary payload."""

    def __init__(self, payload):
        self.payload = payload
        self.commands = payload.get("ai_commands") or {}
        # Facts are a SEPARATE name space from commands: `(goal x 1)` appears in
        # the condition half of a rule, `(set-goal x 1)` in the action half.  They
        # share spelling conventions but not the table, and a checker that only
        # knows commands reports every correct condition as "unknown".
        self.facts = payload.get("ai_facts") or {}
        self.constants = payload.get("ai_constants") or {}
        self.syscalls = payload.get("xs_syscalls") or {}
        self.provenance = payload.get("generated_from") or {}

    # ---- AI side ---------------------------------------------------------
    def command(self, name):
        return self.commands.get(name)

    def arity(self, name):
        """Return an int, ``None`` when unknown, or ``"variadic"``."""
        if name in VARIADIC:
            return "variadic"
        row = self.commands.get(name)
        if row is None:
            return None
        return row.get("arity")

    def known(self, name):
        return (name in self.commands or name in self.facts
                or name in PER_KEYWORDS or name in PER_LITERALS
                or name in CORPUS_EXTRA)

    def fact(self, name):
        return self.facts.get(name)

    def fact_arity(self, name):
        row = self.facts.get(name)
        return None if row is None else row.get("arity")

    def by_prefix(self, prefix):
        return sorted(n for n in self.commands if n.startswith(prefix))

    # ---- XS side ---------------------------------------------------------
    def syscall(self, name):
        return self.syscalls.get(name)

    def syscall_argc(self, name):
        row = self.syscalls.get(name)
        if not row:
            return None
        return len(row.get("args") or ())

    def xs_arg_types(self, name):
        row = self.syscalls.get(name) or {}
        return [a.split()[-1] if " " in a else a for a in (row.get("args") or ())]

    def syscall_argc_range(self, name):
        """``(min, max)`` argument counts for one syscall.

        The binary's prototype gives ``max``; it is the FULL signature as the
        engine declares it.  ``min`` comes from the shipped
        ``resources/_common/xs`` corpus -- an argument count that appears there
        is one the engine ran, so a smaller count is legal, not a typo.  Merging
        the two is what stopped 141 false warnings on the game's own scripts:
        ``xsEffectAmount`` is declared with 6 parameters and every shipped call
        passes 5.
        """
        row = self.syscalls.get(name) or {}
        proto = len(row.get("args") or ())
        obs = (self.payload.get("xs_argc") or {}).get(name) or {}
        lo = obs.get("min")
        hi = obs.get("max")
        if lo is None:
            lo = proto
        if hi is None:
            hi = proto
        return (int(lo), int(hi))

    # ---- XS graded surfaces ---------------------------------------------
    def producer_of(self, name):
        """Buildings that train ``name``, from the DAT's own Creatable table.

        ``{"id": 4, "buildings": [87], ...}`` for ``archer``.  This is the only
        non-guessed source for the third slot of
        ``xsEffectAmount(cSpawnUnit, unitId, buildingId, count, playerId)``:
        DAT effect type 7 stores ``(unit, spawn-building, count, 0)`` and the one
        witnessed XS call site (``Effects.xs:136``) matches that order exactly.
        """
        row = (self.payload.get("ai_unit_producer") or {}).get(name)
        if not row:
            return None
        return list(row.get("buildings") or ())

    def witnessed(self, name):
        """Corpus call count for an XS syscall, or 0 when never used.

        A syscall with 0 here exists in the engine (its prototype is in the
        binary) but no shipped script ever called it, so emitting it is a guess
        about runtime behaviour, not a documented use.  Surfacing the number is
        what lets the caller grade the output instead of pretending.
        """
        obs = (self.payload.get("xs_argc") or {}).get(name) or {}
        n = obs.get("calls")
        if n is None:
            proof = obs.get("proof") or ""
            m = re.match(r"\s*(\d+)", proof)
            n = int(m.group(1)) if m else 0
        return int(n)


# ---------------------------------------------------------------------------
# .per tokenising
# ---------------------------------------------------------------------------
#: `.per` is a small Lisp: everything is a parenthesised sexp, `;` starts a
#: comment to end of line, and `#load-if` lines are preprocessor-ish and sit
#: OUTSIDE any sexp.  Tokenising those three rules correctly is enough to walk
#: every shipped file; anything fancier (a real BNF) is not needed to answer
#: "is this name spelled right and does it have the right number of arguments".
_COMMENT = re.compile(r";[^\n]*")
_LOADIF_LINE = re.compile(r"^\s*#\s*(load-if|else|endif|end-if)\b[^\n]*$", re.I | re.M)
#: A sexp head name: everything up to whitespace or `(`.  `defrule`, `goal`,
#: `c:min` and `or` all match; `or(unit-type-count-total` yields `or`.
_HEAD = re.compile(r"([^\s()]+)")

#: What a string literal's body is replaced with while scanning.  A control char
#: that cannot appear in source, chosen so the literal collapses to ONE token:
#: blanking it to spaces made `(xs-script-call "FindAdjacentAngle")` look like a
#: two-argument call and produced false arity warnings on the game's own scripts.
_STR_FILL = "\x01"


def _mask_strings(text):
    """Blank the INSIDE of `"..."` literals, keeping length and offsets.

    `.per` strings are real literals and may contain `(`, `)` and `;`.  The
    shipped corpus has a chat constant whose text ends in a smiley --
    `(defconst text-hey-brute "... :)")` at Promisory/const.per:2088 -- and a
    scanner that counts raw parens sees that `)` as closing the defconst, then
    reports every following line as unbalanced.  Six of the game's own files came
    out "broken" that way, which is exactly the kind of false alarm that teaches
    a player to ignore the checker.

    Blanking rather than deleting keeps every later offset (and therefore every
    reported line number) valid.  An unterminated quote is left alone so the
    brace check still reports the real problem.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == "\n":          # a string cannot span lines
                    j = -1
                    break
                j += 1
            if j == -1 or j >= n:
                i += 1                       # unterminated: leave it visible
                continue
            for k in range(i + 1, j):
                if out[k] != "\n":
                    out[k] = _STR_FILL
            i = j + 1
            continue
        i += 1
    return "".join(out)


def strip_comments(text):
    """Remove `;` comments and `#load-if` directive lines, preserving offsets.

    Offsets are preserved by blanking rather than deleting, because a diagnostic
    that points at the wrong character is a bug report waiting to happen.
    """
    def blank(m):
        return "".join("\n" if ch == "\n" else " " for ch in m.group(0))
    # Strings first: a `;` inside a chat constant is text, not a comment, and
    # blanking it first is what keeps the comment rule from eating the rest of
    # the line including the closing paren.
    text = _mask_strings(text)
    text = _COMMENT.sub(blank, text)
    return _LOADIF_LINE.sub(blank, text)


def sexps(text):
    """Yield ``(name, args, line, pos)`` for EVERY list, at any nesting depth.

    Depth matters: a rule is one top-level list `(defrule (cond) ... => (act))`,
    so the commands that actually get validated live two and three levels down.
    An earlier version of this function yielded only depth-0 lists and therefore
    validated nothing but `defrule` itself -- it reported zero diagnostics on 52
    shipped files, which read as "all correct" when it meant "all skipped".
    That is the same defect class as a route that answers 200 with an empty list.

    ``args`` are the raw argument strings, split on whitespace, but only when the
    body holds no nested list.  A body with a nested list (`defrule`, `or`) gets
    ``args = None`` so arity is never asserted about a shape that whitespace
    splitting cannot describe.
    """
    clean = strip_comments(text)
    stack = []                                # (start_pos, line)
    line = 1
    for i, ch in enumerate(clean):
        if ch == "\n":
            line += 1
            continue
        if ch == "(":
            stack.append((i, line))
        elif ch == ")":
            if not stack:
                continue                      # stray close: reported by balanced()
            start, ln = stack.pop()
            body = clean[start + 1:i]
            # The head name ends at the first whitespace OR the first `(`.  Lisp
            # lets `(or(a)(b))` be written without spaces, and the shipped scripts
            # do exactly that in places: splitting on whitespace alone produced
            # the head `or(unit-type-count-total`, which then read as a misspelled
            # command 180 times.  The name is a delimiter-delimited token, not a
            # whitespace-delimited one.
            stripped = body.lstrip()
            if not stripped:
                continue                      # empty list, e.g. `()`
            m = _HEAD.match(stripped)
            name = m.group(1) if m else stripped[0]
            if "(" in body:
                yield (name, None, ln, start)
            else:
                rest = stripped[m.end():] if m else ""
                yield (name, rest.split(), ln, start)
    for _start, ln in stack:
        yield (None, None, ln, len(clean))


def balanced(text):
    """Return ``(ok, line)`` for the first unbalanced position, or ``(True, None)``."""
    clean = strip_comments(text)
    depth = 0
    for i, ch in enumerate(clean):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return (False, clean.count("\n", 0, i) + 1)
    if depth:
        return (False, None)
    return (True, None)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
#: How many call sites a command needs before its argument count is asserted.
#: The payload records the count observed in the shipped corpus, and a name that
#: occurs ONCE carries no weight: `chat-to-enemies` appears once in
#: `AI (HD version).per`, and that single occurrence had ten tokens after it
#: because the string literal was counted as several.  Asserting an arity from one
#: sample produced a warning on the game's own file, which is the checker telling
#: a player their correct script is wrong.  Three is the point where the count has
#: survived at least one chance to disagree with itself.
MIN_USES_FOR_ARITY = 3


def validate_ai(text, vocab):
    """Check a `.per` source.  Returns a list of ``(line, level, message)``.

    ``level`` is ``"error"`` for things the engine will refuse (unknown command,
    unbalanced parens) and ``"warn"`` for things it accepts but that are almost
    always a mistake (wrong argument count, unknown constant).

    Arity is only asserted where the payload HAS an arity (188 of 324 names) and
    the call body has no nested list.  Everywhere else the check stays silent on
    purpose: a validator that guesses produces red squiggles on correct scripts,
    and a player cannot tell that kind of error from a real one.
    """
    out = []
    ok, line = balanced(text)
    if not ok:
        out.append((line, "error",
                    "括号不配对" if line else "有未闭合的 ("))

    seen = set()
    count = 0
    # `defconst` is file-scoped, and every author names their own constants.
    # Collect them first so a slot check does not report `desired-villagers` as
    # "should be an integer" when the file defines it as one three lines up.
    local = _defconsts(text)
    for name, args, ln, pos in sexps(text):
        if name is None:
            continue
        count += 1
        if count > 400000:                    # pathological input guard
            break
        if (ln, name) in seen:
            continue
        if name in PER_KEYWORDS or name in PER_LITERALS or name in CORPUS_EXTRA:
            continue
        row = vocab.command(name)
        if row is None:
            fact = vocab.fact(name)
            if fact is not None:
                want = fact.get("arity")
                if isinstance(want, int) and args is not None and len(args) != want:
                    out.append((ln, "warn",
                                "%s 需要 %d 个参数，这里 %d 个" % (name, want, len(args))))
                    seen.add((ln, name))
                    continue
                # Facts have argument domains too, and they are where the silent
                # failures live: `(building-type-count-total villager >= 2)` is
                # a well-formed call to a real fact that counts buildings, so the
                # engine reads it as "count the buildings named villager" -- zero,
                # forever.  Same slot-domain table as commands.
                if args is not None:
                    for msg in _grammar_problems(name, args, local):
                        out.append((ln, "warn", msg))
                        seen.add((ln, name))
                continue
            # Not a command, not a fact, not a rule keyword.  A misspelling of a
            # real name is far more likely here than a construct this walker
            # cannot see, so it is reported -- but as a warning, because the
            # vocabulary itself is incomplete (72 of 267 commands never occur in
            # the shipped corpus, so a legitimate name can be missing).
            out.append((ln, "warn", "未知的名字 %s（不在命令表与 fact 表里）" % name))
            seen.add((ln, name))
            continue
        want = vocab.arity(name)
        uses = (row or {}).get("uses") or 0
        if isinstance(want, int) and args is not None and len(args) != want:
            if uses < MIN_USES_FOR_ARITY:
                seen.add((ln, name))
                continue
            out.append((ln, "warn",
                        "%s 需要 %d 个参数，这里 %d 个" % (name, want, len(args))))
            seen.add((ln, name))
            continue
        # Argument *count* right is not the same as argument *kind* right:
        # `(building-type-count-total villager >= 2)` has the right arity and is
        # the exact shape a writer reaches for, but the engine silently ignores
        # it because that slot takes a building.  aigram learned each slot's
        # domain from 113,987 shipped call sites; use it rather than leave the
        # writer to find out at runtime.
        if args is not None:
            for msg in _grammar_problems(name, args, local):
                out.append((ln, "warn", msg))
                seen.add((ln, name))
    return out


_GRAMMAR = []


def _defconsts(text):
    """Names this file declares with ``(defconst NAME VALUE)``."""
    out = set()
    for name, args, _ln, _pos in sexps(text):
        if name == "defconst" and args:
            out.add(args[0])
    return out


def _grammar_problems(name, args, local=None):
    """Slot-domain check, sharing one lazily-loaded grammar table."""
    if not _GRAMMAR:
        try:
            from .aigram import Grammar
            _GRAMMAR.append(Grammar.load())
        except Exception:
            _GRAMMAR.append(None)
    g = _GRAMMAR[0]
    if g is None:
        return []
    try:
        return g.problems(name, args, local)
    except Exception:
        return []


_XS_CALL = re.compile(r"\b(xs[A-Za-z0-9_]+)\s*\(")


def validate_xs(text, vocab):
    """Check an `.xs` source against the syscall prototypes read from the binary.

    Only calls to names that START with ``xs`` are checked, because those are
    the engine syscalls; a user-defined function is the script's own business.
    """
    out = []
    clean = re.sub(r"//[^\n]*", "", text)
    clean = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"),
                   clean, flags=re.S)
    for m in _XS_CALL.finditer(clean):
        name = m.group(1)
        row = vocab.syscall(name)
        ln = clean.count("\n", 0, m.start()) + 1
        if row is None:
            out.append((ln, "warn", "未知 syscall %s" % name))
            continue
        args = _split_call(clean, m.end())
        if args is None:
            continue                          # unbalanced: reported elsewhere
        lo, hi = vocab.syscall_argc_range(name)
        if hi and not (lo <= len(args) <= hi):
            if lo == hi:
                why = "%s 需要 %d 个参数，这里 %d 个" % (name, hi, len(args))
            else:
                why = ("%s 参数的合法个数是 %d..%d，这里 %d 个"
                       % (name, lo, hi, len(args)))
            out.append((ln, "warn", why))
    ok_par = _xs_parens(text)
    if ok_par is not None:
        out.append((ok_par, "error", "括号不配对"))
    return out


def _split_call(text, pos):
    """Split the argument list of a call whose ``(`` ends at ``pos``."""
    depth = 1
    args = []
    cur = []
    for i in range(pos, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                tail = "".join(cur).strip()
                if tail or args:
                    args.append(tail)
                return args
        elif ch == "," and depth == 1:
            args.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    return None


def _xs_parens(text):
    clean = re.sub(r"//[^\n]*", "", text)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.S)
    depth = 0
    for i, ch in enumerate(clean):
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
            if depth < 0:
                return clean.count("\n", 0, i) + 1
    return None if depth == 0 else None


# ---------------------------------------------------------------------------
# Writing / installing
# ---------------------------------------------------------------------------
#: Where a script has to sit inside a mod folder for the game to read it in
#: place of the shipped one.  Verified against a real subscribed mod on this
#: machine (`15373_Multiple Buffs Mod v1` ships
#: `resources/_common/xs/Effects.xs` and works in game), so the loose-file
#: override reaches XS.  `.per` follows the same rule -- a mod wins by
#: providing the same relative path as the base game.
AI_REL = os.path.join("resources", "_common", "ai")
XS_REL = os.path.join("resources", "_common", "xs")


def storage_rel(path):
    """Which mod-relative folder a script belongs in, from its extension."""
    low = path.lower()
    if low.endswith(".per") or low.endswith(".ai"):
        return AI_REL
    if low.endswith(".xs"):
        return XS_REL
    raise ValueError("不是 AI/XS 脚本: %s" % path)
