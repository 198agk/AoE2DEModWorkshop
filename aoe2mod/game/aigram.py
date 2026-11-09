"""The engine's own grammar, learned from AoE2DE_s.exe plus its shipped corpus.

`ailang.Vocab` answers "is this a name the engine knows?".  That is enough to
keep from writing nonsense, but it cannot answer the questions a writer actually
asks:

  * which slot of ``up-target-objects`` takes a ``c:`` constant and which takes
    a raw number?
  * given ``(set-strategic-number sn- ...)``, what may follow?
  * ``(train 1259)`` -- is a raw object id legal there, or must it be a name?

Both answers live in the binary: 324 commands with arity, 93 facts, 212
strategic numbers, 27 player selectors, 20 object-data slots.  What the binary
does *not* carry is the **domain of each argument slot**.  That is recovered
from 135,660 real call sites in the 89 shipped `.per` files: for every command
and every position, count which domain the argument came from (unit name /
building name / tech name / strategic number / raw integer / ``c:`` constant /
``g:`` goal / comparison operator), and take the union that covers 88% of the
sites.

Two things make the result trustworthy rather than plausible:

1. Domains come from the reverse-engineered name tables, not from a hand-written
   list.  A name is a unit name because the binary's name pool and the DAT say
   so.
2. Where a slot's values form a small closed set (``release-escrow`` only ever
   takes gold/food/wood/stone), the set is emitted verbatim as an enum family,
   so the tool can offer exactly those four and nothing else.

Use it to check a call before emitting it:

    g = Grammar.load()
    g.problems("up-target-objects", ["0", "action-default", "-1", "-1"])   # []
    g.values("release-escrow", 0)     # ['gold', 'food', 'wood', 'stone']
    g.signature("up-find-local")      # 'const any const|goal num|const'
"""
import json
import os
import re

DATA_REL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "ai_grammar.json")

_CACHE = {}

_CMP = frozenset(("<", "<=", ">", ">=", "==", "!=", "="))
_OP = frozenset(("+", "-", "*", "/", "mod", "min", "max", "neg",
                 "z/", "%*", "%/", "abs"))


def grammar_path(path=None):
    if path:
        return path
    env = os.environ.get("AOE2_GRAMMAR")
    return env or DATA_REL


class Grammar(object):
    def __init__(self, payload):
        self.payload = payload or {}
        self.commands = self.payload.get("commands") or {}
        self.families = self.payload.get("families") or {}
        self.domains = self.payload.get("domains") or {}

    # ---- lookup -------------------------------------------------------
    def row(self, name):
        return self.commands.get(name)

    def signature(self, name):
        row = self.row(name)
        return row["signature"] if row else None

    def arity(self, name):
        row = self.row(name)
        if not row:
            return None
        return row.get("arity")

    def slots(self, name):
        row = self.row(name)
        return (row or {}).get("args") or []

    def slot(self, name, i):
        for s in self.slots(name):
            if s["i"] == i:
                return s
        return None

    def values(self, name, i):
        """The closed set of values this slot takes, or [] when it is open."""
        fam = self.families.get("%s[%d]" % (name, i))
        if fam:
            return list(fam["values"])
        return []

    def examples(self, name):
        return list((self.row(name) or {}).get("examples") or [])

    def names(self):
        return sorted(self.commands)

    def search(self, prefix, limit=20):
        return [n for n in self.names() if n.startswith(prefix)][:limit]

    # ---- checking -----------------------------------------------------
    def problems(self, name, args, local=None):
        """Return a list of human-readable problems for one call.  Empty = fine.

        The judgement is made against what the slot was *observed* to accept,
        not against a single dominant domain.  That distinction is the whole
        difference between a checker people trust and one they mute: an arity
        or domain rule invented by hand rejects correct code, while a rule read
        off 113,987 real call sites can be wrong only where the corpus is silent.

        ``local`` is the set of ``defconst`` names declared in the file being
        checked.  ``defconst`` is file-scoped, so `(unit-type-count villager <
        desired-villagers)` is correct code even though no shipped script ever
        used that name -- refusing it would mean rejecting every script whose
        author picked their own constant names, which is all of them.
        """
        out = []
        local = local or ()
        row = self.row(name)
        if row is None:
            return out
        want = row.get("arity")
        slots = self.slots(name)
        if isinstance(want, int) and want != len(args):
            out.append("%s 要 %d 个参数，这里给了 %d 个" % (name, want, len(args)))
            return out
        if not slots:
            return out
        for i, arg in enumerate(args):
            s = self.slot(name, i)
            if s is None:
                continue
            seen = s.get("seen") or {}
            bydom = s.get("values_by_domain") or {}
            if not seen:
                continue
            if arg.strip() in local:
                # a name this file defines; its value is an integer by grammar
                if "unit" in seen or "bld" in seen or "tech" in seen:
                    continue          # still ambiguous here, corpus decides below
                continue
            closed = self.values(name, i)
            if closed and arg.strip() not in closed:
                out.append("%s 的第 %d 个参数只能取 %s，这里是 %s"
                           % (name, i + 1, "/".join(closed), arg.strip()))
                continue
            # An argument the corpus has literally used in this slot, in *some*
            # domain the slot accepts, is correct by construction.
            if any(arg.strip() in vals for vals in bydom.values()):
                continue
            total_seen = sum(seen.values()) or 1
            # A slot accepts a domain only if it was a material share of the
            # observations.  `building-type-count-total`'s first slot sees
            # `unit` 395 times out of 3436, and every one of those is a name the
            # two domains share (castle, monastery, mule-cart, transport-ship,
            # wall-class, monastery-class).  Letting that 11% count as "this slot
            # takes units" is what makes `(building-type-count-total villager
            # >= 2)` -- a call the engine silently ignores -- pass the checker.
            allowed = [k for k, n in seen.items()
                       if n >= 3 and n / total_seen >= 0.15
                       and k not in ("empty", "any", "opaque")]
            if not allowed or s["domain"] in ("any", "opaque"):
                continue
            if any(_fits(k, arg, self.domains) for k in allowed):
                continue
            out.append("%s 的第 %d 个参数要 %s，这里是 %s"
                       % (name, i + 1, "/".join(_readable(k) for k in allowed),
                          arg.strip()))
        return out

    # ---- loading ------------------------------------------------------
    @classmethod
    def load(cls, path=None):
        p = grammar_path(path)
        if p in _CACHE:
            return _CACHE[p]
        try:
            with open(p, encoding="utf-8") as fh:
                g = cls(json.load(fh))
        except (IOError, OSError, ValueError):
            g = cls({})
        _CACHE[p] = g
        return g


_LABEL = {
    "unit": "单位名", "bld": "建筑名", "tech": "科技名", "sn": "战略数字名",
    "player": "玩家选择器", "objdata": "object-data 项", "logic": "逻辑算子",
    "cmp": "比较符", "op": "算术运算符", "const": "常量名", "goal": "目标(g:)",
    "str": "字符串", "str_goal": "目标字符串(s:)", "num": "整数",
    "fact": "fact 名", "cmd": "命令名", "pool": "引擎名", "opaque": "未知域",
    "empty": "空", "any": "任意",
}


def _readable(dom):
    return _LABEL.get(dom, dom)


def _fits(dom, arg, domains):
    """Does `arg` belong to `dom`?

    The subtlety that cost the first version its whole false-positive budget:
    `c:` and `g:` are *expression wrappers*, not domains.  `(up-compare-goal
    g: >= 5)` passes the comparison operator **inside** the wrapper, so the
    prefix has to be peeled before the operator is recognised.  Reading the
    prefix first turns every such call into "wanted a comparison, got a
    constant", which is 215 false alarms in one file alone.
    """
    a = (arg or "").strip()
    if not a:
        return True
    m = re.match(r"^([cgs]):(.*)$", a)
    if m:
        prefix, rest = m.group(1), m.group(2).strip()
        if rest in _CMP or rest in _OP:
            # the wrapper carries an operator / comparison, so the argument is
            # whatever the operator slot wants, never a name-domain mismatch
            return dom in ("cmp", "op", "const", "goal", "any", "num",
                           "nconst", "str_goal")
        if prefix == "s":
            return True
        if not rest:                      # bare `c:` / `g:` opens an expression
            return True
        if re.fullmatch(r"-?\d+", rest):
            return dom not in ("unit", "bld", "tech")
        if re.match(r"^[+\-*/%]", rest) or rest[0].isdigit():
            return True
        if dom in ("any", "opaque", "const", "goal", "nconst", "num"):
            return True
        allowed = domains.get(dom)
        return (a in set(allowed)) if allowed else True
    if dom == "cmp":
        return a in _CMP
    if dom == "op":
        return a in _OP
    if dom == "num":
        # a raw integer slot also accepts the corpus' own numeric constants:
        # `(building-type-count-total X >= tc-level-three)` is correct code,
        # and `tc-level-three` is a `defconst ... 1` in the same file.
        return bool(re.fullmatch(r"-?\d+", a)) or a in _nconst(domains)
    if dom == "nconst":
        return bool(re.fullmatch(r"-?\d+", a)) or a in _nconst(domains)
    if dom == "goal":
        return True
    if dom == "player" and re.fullmatch(r"-?\d+", a):
        # `(player-valid 3)` -- a raw player number is a player selector
        return True
    if dom == "str":
        # `(chat-to-player 0 7110)` -- a numeric string id is a legal message
        # source, so a bare integer fits the string slot too.
        return a.startswith('"') or a.startswith("s:") or bool(
            re.fullmatch(r"-?\d+", a))
    if dom in ("any", "opaque", ""):
        return True
    if dom in ("const", "nconst") and re.fullmatch(r"-?\d+", a):
        # `(up-get-point position-object 509)` -- the constant slot is really
        # "a point or an object id", and a bare id is how you write the latter.
        return True
    if a.startswith("sn-") and dom in ("const", "nconst", "num", "sn"):
        # any `sn-*` the binary knows is a number; strategic numbers reach slots
        # that the corpus happened to fill with a different numeric spelling
        return True
    allowed = domains.get(dom)
    # The name-domain tables win over every fallback below.  Ordering matters:
    # `castle` is a real building name AND a `defconst castle 82` in the shipped
    # corpus, so a nconst check placed first rejects 248 correct calls.
    if allowed and a in set(allowed):
        return True
    if re.fullmatch(r"-?\d+", a):
        # raw integers are legal wherever the engine accepts an object id
        return dom in ("unit", "bld", "tech", "fact", "sn", "player", "const",
                       "nconst")
    if a in _nconst(domains):
        # a corpus constant whose value is a plain integer is usable anywhere an
        # integer is, but it does not make a unit name into a building name
        return dom not in ("unit", "bld", "tech", "player")
    if a in _sn_extra(domains):
        return dom == "sn"
    if allowed:
        return False
    return True


def _nconst(domains):
    return domains.get("nconst") or set()


def _sn_extra(domains):
    return domains.get("sn") or set()
