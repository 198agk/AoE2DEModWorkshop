# -*- coding: utf-8 -*-
"""Mine the game's own rules into a template knowledge base.

Why this and not a hand-written rule library
--------------------------------------------
The player's ask is "which units, in which situation, doing what".  That is a
decision tree, and the game already ships a decision tree: 12 000+ `defrule`
blocks across 52 `. per` files, written by the developers, tested by shipping.
Every one of them is a shape the loader accepts and the evaluator runs.

So the reliable move is not to invent rules, it is to INDEX the ones that exist
and instantiate them with the player's numbers.  A template that came out of
`AiBuilder/militaryUnits.per` cannot have a wrong argument order, because it is
the argument order the engine was built against.

What a template is
------------------
A rule block reduced to its skeleton:

    (defrule (cond) (cond) => (act) (act))

becomes

    conditions: [ "unit-type-count-total %s g:< %s", "can-train %s" ]
    actions:    [ "train %s" ]
    slots:      [ "unit" ]

The `%s` mark the positions the player's choices fill.  Slots are typed by what
the shipped script puts there (a unit name, a strategic number, a count, a goal
name), so substitution cannot put a number where a unit name belongs.

The harness this gives you
--------------------------
1. MINE once -> a JSON file next to the package.  Takes seconds, runs at build
   time, and the result is checked in, so the tool never mines at runtime.
2. The composer picks templates by (action verb, slot type) and fills them.
3. Anything the player asks for that has no template is REPORTED, not guessed.
"""
import json
import os
import re

#: Where the mined file lives.  Next to the package, not in the user profile:
#: it is derived data, identical for every player of this game build.
KB_REL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "data", "ai_rules_kb.json")

_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[^\s()]+")


def _strip(text):
    """Drop comments, keep structure.  `#load-if` lines are not rule content."""
    text = re.sub(r";[^\n]*", "", text)
    text = re.sub(r"^\s*#\s*[^\n]*$", "", text, flags=re.M)
    return text


def _tokens(text):
    return _TOKEN.findall(text)


def _lists(text):
    """Yield every balanced `(...)` group as ``(head, body, depth)``.

    Iterative so a 1.1 MB file cannot blow the stack.  Depth is relative to the
    file, which is what lets the caller keep only top-level `defrule` blocks.
    """
    stack = []
    depth = 0
    out = []
    for m in re.finditer(r"[()]", text):
        if m.group(0) == "(":
            stack.append(m.start())
            depth += 1
        elif stack:
            start = stack.pop()
            depth -= 1
            body = text[start + 1:m.start()]
            head_m = _TOKEN.match(body.lstrip())
            head = head_m.group(0) if head_m else ""
            out.append((head, body, depth, start))
    return out


#: What a `%s` slot may be filled with, decided by the token that was there in
#: the shipped script.  Ordered: the first matching rule wins.
SLOT_KINDS = (
    ("player", re.compile(r"^(any|every|this)-")),
    ("sn", re.compile(r"^sn-")),
    ("goal", re.compile(r"^(goal|temporary-goal|gl-|goal[0-9])")),
    ("timer", re.compile(r"-timer$|^timer-")),
    ("cmp", re.compile(r"^(c:|s:|g:|[<>]=?$|==$|!=$)")),
    ("unit", re.compile(r"^[a-z][a-z0-9-]*$")),
)


def _slot_kind(token, vocab):
    """Classify a literal position so substitution stays type-correct."""
    if re.match(r"^-?\d+(\.\d+)?$", token or ""):
        return "number"
    name = token.split(":")[-1] if ":" in token else token
    if name in vocab.constants:
        return "const"
    if name in (vocab.payload.get("ai_unit_ids") or {}):
        return "unit"
    for kind, rx in SLOT_KINDS:
        if rx.search(token or ""):
            return kind
    if re.match(r"^[a-z][a-z0-9-]*$", name or ""):
        return "name"
    return "opaque"


def _split_rule(body):
    """Split a `defrule` body into condition tokens and action tokens.

    The `=>` separator is the language's own; everything before it is the
    condition list, everything after is the action list.
    """
    idx = body.find("=>")
    if idx < 0:
        return None
    return body[:idx], body[idx + 2:]


def _sexp_list(body):
    """Top-level `(..)` groups inside a body, in order."""
    out = []
    depth = 0
    start = None
    head = ""
    for i, ch in enumerate(body):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                inner = body[start + 1:i]
                m = _TOKEN.match(inner.lstrip())
                out.append((m.group(0) if m else "", inner))
                start = None
    return out


def _skeleton(inner):
    """`inner` (head + args) -> (template string, [slot kinds]).

    The head is kept verbatim: it is the command/fact name, and the whole point
    is that the name is right.  Only the ARGUMENT positions become slots.
    """
    toks = _tokens(inner)
    if not toks:
        return None
    head = toks[0]
    args = []
    for t in toks[1:]:
        args.append(t)
    return head, args


def mine(ai_dir, vocab, limit=None):
    """Walk ``ai_dir`` and return a list of template dicts.

    Each template records the file it came from, so a player reading the tool's
    output can see which shipped rule it is based on.  That traceability is the
    difference between "the AI does something" and "the AI does this because
    `AiBuilder/militaryUnits.per` does this".
    """
    templates = []
    files = []
    for root, _d, fnames in os.walk(ai_dir):
        for f in sorted(fnames):
            if f.lower().endswith(".per"):
                files.append(os.path.join(root, f))
    files.sort()

    for path in files:
        try:
            with open(path, "r", encoding="latin-1") as fh:
                raw = fh.read()
        except OSError:
            continue
        text = _strip(raw)
        rel = os.path.relpath(path, ai_dir).replace("\\", "/")
        for head, body, depth, _pos in _lists(text):
            if head != "defrule" or depth != 0:
                continue
            pair = _split_rule(body)
            if pair is None:
                continue
            cond_body, act_body = pair
            conds, acts = [], []
            for h, inner in _sexp_list(cond_body):
                if not h:
                    continue
                conds.append((h, inner))
            for h, inner in _sexp_list(act_body):
                if not h:
                    continue
                acts.append((h, inner))
            if not conds or not acts:
                continue
            tpl = _make_template(conds, acts, vocab, rel)
            if tpl is not None:
                templates.append(tpl)
            if limit and len(templates) >= limit:
                return templates
    return templates


def _make_template(conds, acts, vocab, rel):
    """One rule block -> a template, or None if it uses a name we cannot place."""
    cond_tpls, act_tpls = [], []
    slots = []

    def render(pairs, bucket):
        for head, inner in pairs:
            if not vocab.known(head) and head not in ("or", "and", "not",
                                                      "nor", "nand"):
                return False
            toks = _tokens(inner)
            parts = [toks[0]]
            for t in toks[1:]:
                kind = _slot_kind(t, vocab)
                if kind in ("unit", "number", "const", "sn", "goal", "player",
                            "timer", "cmp", "name"):
                    parts.append("%s")
                    slots.append(kind)
                else:
                    parts.append(t)
            bucket.append("(" + " ".join(parts) + ")")
        return True

    if not render(conds, cond_tpls):
        return None
    if not render(acts, act_tpls):
        return None
    return {"cond": cond_tpls, "act": act_tpls, "slots": slots,
            "verbs": [a[0] for a in acts], "src": rel}


# ---------------------------------------------------------------------------
# Query surface
# ---------------------------------------------------------------------------
class KB(object):
    """The mined templates, indexed by the action verbs they perform."""

    def __init__(self, payload):
        self.templates = payload.get("templates") or []
        self.meta = payload.get("meta") or {}
        self.by_verb = {}
        for t in self.templates:
            for v in t.get("verbs") or ():
                self.by_verb.setdefault(v, []).append(t)

    def verbs(self):
        return sorted(self.by_verb, key=lambda v: -len(self.by_verb[v]))

    def find(self, verb, want_slots=None, max_slots=6):
        """Templates doing ``verb``, cheapest-to-fill first.

        "Cheapest" is a real criterion, not a style choice: a template with a
        `goal` slot needs the script to set that goal somewhere, so a rule built
        from it silently never fires when the player has no goal of that name.
        Preferring fewer slots means preferring rules that stand on their own.
        """
        out = []
        for t in self.by_verb.get(verb) or ():
            if want_slots_ok(want_slots, t.get("slots") or ()):
                if len(t.get("slots") or ()) <= max_slots:
                    out.append(t)
        out.sort(key=lambda t: (len(t.get("slots") or ()), t.get("src") or ""))
        return out


def want_slots_ok(want, have):
    if not want:
        return True
    return all(w in have for w in want)


def load(path=None):
    path = path or KB_REL
    with open(path, "r", encoding="utf-8") as fh:
        return KB(json.load(fh))


def build(ai_dir, vocab, out=None):
    """Mine and write the KB.  Returns ``(path, stats)``."""
    tpls = mine(ai_dir, vocab)
    out = out or KB_REL
    stats = {"templates": len(tpls),
             "files": len({t["src"] for t in tpls}),
             "verbs": len({v for t in tpls for v in t["verbs"]})}
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"meta": stats, "templates": tpls}, fh, ensure_ascii=False)
    return out, stats
