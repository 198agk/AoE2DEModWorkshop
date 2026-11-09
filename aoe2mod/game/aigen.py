# -*- coding: utf-8 -*-
"""Compose a COMPLETE AI script (`.per`) from a small plan, not line by line.

Why this exists
---------------
`ainl.translate` answers one sentence at a time, and one sentence is not a
script.  A playable AI is a fixed skeleton: phase gates, an economy rule that
sets gatherer percentages, a production rule per unit, an attack rule gated on
army size, and constants that the rules reference.  Writing that skeleton by
hand is where beginners stop -- not because any single line is hard, but because
the pieces have to agree with each other (a production rule that names a goal
nobody sets will never fire, and the game says nothing about it).

So this module emits the whole thing.  Every template below is copied from a
shape that appears in the game's own scripts, and the comment on each block
names the file it came from:

    AiBuilder/phaseUpdate.per      phase gates:  (set-goal current-phase 1)
                                                 (disable-self)
    AiBuilder/economy.per          gatherer split: (up-modify-sn
                                                 sn-food-gatherer-percentage g:= ...)
    AiBuilder/militaryUnits.per    production:   (unit-type-count-total X g:< N)
                                                 (can-train X) => (train X)
    AiBuilder/militaryBehavior.per attack:       (... soldier count ...)
                                                 (attack-now)
                                                 (up-set-timer c: T g: I)
    AiBuilder.per                  load chain:   (load "AiBuilder\\general")

What is deliberately NOT generated
----------------------------------
Anything whose argument order is unknown.  The analysis of the binary found no
dispatch table for `up-*` (18 independent scans; report §8.2), so argument order
for most of them is unverified.  The templates here either use only commands
whose call shape is directly observable in the shipped scripts, or pass
arguments in the order those scripts use.  A plan that asks for something with no
observed shape is rejected with a reason instead of being approximated.

Honesty boundary
----------------
This makes a script that LOADS and RUNS.  It does not make one that is GOOD.
Tuning (how many villagers before ageing up, when to attack) is the player's
call, and the defaults here are the shipped scripts' own numbers, not a
strategy recommendation.
"""
import os
import re

from . import ailang
from . import ainl
from . import aistrat
from . import civnames

#: Unit name -> production line, for the units a beginner actually names.  The
#: right-hand side is what the engine accepts in `(train ...)`, taken from the
#: name table at `.data` 0x040965b0 (135 entries) plus the `-line` forms that
#: appear in shipped scripts (`archer-line`, `skirmisher-line`, `scout-cavalry-line`).
LINES = {
    "archer": "archer-line",
    "步弓": "archer-line",
    "弓手": "archer-line",
    "skirmisher": "skirmisher-line",
    "散兵": "skirmisher-line",
    "spearman": "spearman-line",
    "枪兵": "spearman-line",
    "militia": "militiaman-line",
    "民兵": "militiaman-line",
    "knight": "knight-line",
    "骑士": "knight-line",
    "scout": "scout-cavalry-line",
    "侦察": "scout-cavalry-line",
    "camel": "camel-line",
    "骆驼": "camel-line",
    "mangonel": "mangonel-line",
    "投石": "mangonel-line",
    "ram": "battering-ram-line",
    "攻城锤": "battering-ram-line",
}

#: Age names as the engine spells them in `(current-age >= feudal-age)`.
AGES = ("dark-age", "feudal-age", "castle-age", "imperial-age")

#: Civilisation names as `(civ-selected X)` spells them.  Every one appears at a
#: real call site in the shipped `AI (HD version).per` (208 sites, 54 distinct
#: values); the dat's civ list spells some differently ("britons" vs "briton"),
#: and this fact takes the script's spelling, so this is the list that matters.
CIVS = frozenset("""
achaemenids armenians aztec bengalis berbers bohemians briton bulgarians
burgundians burmese byzantine celtic chinese cumans ethiopian frankish georgians
gothic gurjaras hun incan indian italian japanese jurchens khitans khmer korean
lithuanians magyar malay malian mapuche mayan mongol muisca persian poles
portuguese romans saracen shu sicilians slavic spanish spartans tatars teutonic
tupi turkish vietnamese viking wei wu
""".split())

#: Resource split presets.  Numbers are the shipped AiBuilder defaults, so a
#: generated script behaves like the built-in AI until the player changes them.
SPLITS = {
    "dark": {"food": 55, "wood": 40, "gold": 5, "stone": 0},
    "feudal": {"food": 50, "wood": 35, "gold": 15, "stone": 0},
    "castle": {"food": 45, "wood": 30, "gold": 25, "stone": 0},
    "imperial": {"food": 45, "wood": 30, "gold": 20, "stone": 5},
}


_COUNT_RE = re.compile(r"^([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff\- ]*?)\s*(?:[:：*=x×]|\s)\s*(\d+)$")


def _split_army_text(text):
    """``"archer:20, knight:15"`` -> ``["archer:20", "knight:15"]``.

    A form with one text box hands over one string, and the shape people type is
    ``name:count`` separated by commas, semicolons or newlines.  Splitting here
    keeps `_army_list`'s item loop the single place that reads a pair, instead of
    growing a second grammar in the UI layer.
    """
    out = []
    for chunk in re.split(r"[,;\n\u3001]+", text):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def _army_pair(item):
    """``"knight:15"`` -> ``("knight", 15)``; ``"knight"`` -> ``("knight", 20)``."""
    m = _COUNT_RE.match(item.strip())
    if m:
        return m.group(1).strip(), _num(m.group(2))
    return item.strip(), 20


def _army_list(army):
    """Normalise `army` to ``[(unit_word, count), ...]``.

    Accepts what a UI actually hands over: ``None``, a list of pairs, a list of
    bare names (``["archer", "spearman"]``), a single name, a single text-box
    string (``"archer:20, knight:15"``), or pairs whose count is a string from a
    form field.  Without this, ``Plan(army=["knight-line"])`` exploded inside
    `_constants` with "not enough values to unpack" -- a crash from a shape the
    caller could reasonably pass, not a mistake worth a traceback the player
    would have to read.
    """
    if not army:
        return [("archer", 20)]
    if isinstance(army, str):
        army = _split_army_text(army) if re.search(r"[,;\n\u3001]", army) else [army]
    out = []
    for item in army:
        if isinstance(item, str):
            word, want = _army_pair(item)
        elif isinstance(item, (list, tuple)):
            if not item:
                continue
            word = item[0]
            want = item[1] if len(item) > 1 else 20
        elif isinstance(item, dict):
            word = item.get("unit") or item.get("name") or item.get("word")
            want = item.get("count", item.get("n", 20))
        else:
            continue
        if not word:
            continue
        out.append((str(word), _num(want)))
    return out or [("archer", 20)]


#: Strings a form or a JSON body may use for "no".  `bool()` is wrong for all
#: of them: `bool("0")` and `bool("false")` are both True, so a posted `"0"`
#: used to mean "wall the town".
_FALSE_WORDS = frozenset(("", "0", "false", "no", "off", "none", "null", "n", "f",
                          "假", "否", "不要", "不"))


def _truthy(value):
    """A posted flag, read rather than truthy-tested."""
    if isinstance(value, str):
        return value.strip().lower() not in _FALSE_WORDS
    return bool(value)


def _one_line(value):
    """Collapse a player-typed label to one line of plain text.

    The script's first line is a comment that carries this label
    (``; %(name)s -- generated by aoe2mod``).  A newline anywhere in the label
    ends that comment, and every character after it is parsed as script: a plan
    named ``"MyAI\\n=>\\n\\t(disable-self)"`` emitted a live rule, with
    ``problems`` empty, because nothing between the form and the file looked at
    the string.  A label is a label; keep it one line.
    """
    text = re.sub(r"[\r\n\t\v\f]+", " ", str(value or ""))
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    return " ".join(text.split())


#: The bounds a count must fall inside to describe anything the game can do.
#: Population tops out at 500 in a lobby; a soldier-count trigger above that is
#: a rule that can never fire.  Reporting the clamp is the point: a player who
#: typed -5 must not receive a script that quietly wants -5 villagers.
COUNT_BOUNDS = {"villagers": (1, 500, 30), "attack_at": (1, 500, 20),
                # A per-unit count is the same kind of number: the lobby
                # caps a population at 500, so `knight:0` is a rule that
                # never fires and `knight:99999` is one that never stops.
                "army": (1, 500, 20)}


#: The four gatherer percentages a split carries, and the range the engine's
#: `sn-*-gatherer-percentage` accepts: 0 stops gathering, 100 sends every
#: villager.  Nothing clamps these today -- `Plan(split={"food": -50})` emitted
#: `(set-strategic-number sn-food-gatherer-percentage -50)` and
#: `Plan(split={"food": 300})` emitted 300, both with `problems` empty, and
#: `split={"food": "abc"}` raised `ValueError` from deep inside `aistrat` while
#: composing.  `from_sentences` already guarded its own path
#: (`if 0 < pct <= 100`); this is the same guard where every path meets.
SPLIT_KEYS = ("food", "wood", "gold", "stone")
SPLIT_RANGE = (0, 100)


def _split_checked(split, notes):
    """A split dict with every percentage inside 0..100, or None.

    Returns a new dict; the caller's is never mutated (it may be a preset out of
    `SPLITS`, which is shared module state).
    """
    if not split:
        return None
    if not isinstance(split, dict):
        notes.append({"field": "split", "value": split,
                      "why": "采集比例要写成 {food: 50, wood: 35} 这样；已按默认分配"})
        return None
    out = {}
    for word in sorted(split):
        if word not in SPLIT_KEYS:
            # A key nobody reads is a requirement nobody honours: say so rather
            # than let the player think "wood" was spelled well enough.
            notes.append({"field": "split", "value": word,
                          "why": "这张表只认 food / wood / gold / stone；这一项已略过"})
    for k in SPLIT_KEYS:
        if k not in split:
            continue
        raw = split[k]
        try:
            n = int(raw)
        except (TypeError, ValueError):
            notes.append({"field": "split", "value": "%s:%s" % (k, raw),
                          "why": "采集比例要是整数；已按默认分配"})
            continue
        lo, hi = SPLIT_RANGE
        if n < lo or n > hi:
            notes.append({"field": "split", "value": "%s:%d" % (k, n),
                          "why": "采集比例要在 %d..%d 之间；已按 %d 生成"
                                 % (lo, hi, min(max(n, lo), hi))})
            n = min(max(n, lo), hi)
        out[k] = n
    return out or None


def _bounded(value, field, notes):
    """`int(value)` kept inside COUNT_BOUNDS, with the clamp recorded in notes."""
    lo, hi, default = COUNT_BOUNDS[field]
    try:
        n = int(value)
    except (TypeError, ValueError):
        notes.append({"field": field, "value": value,
                      "why": "这里要一个整数；已按 %d 生成" % default})
        return default
    if n < lo or n > hi:
        notes.append({"field": field, "value": n,
                      "why": "要 %d..%d 之间的数；已按 %d 生成"
                             % (lo, hi, min(max(n, lo), hi))})
        return min(max(n, lo), hi)
    return n


class Plan(object):
    """What the player wants, in the tool's own terms.

    Kept as plain attributes rather than a dict so a caller in `ui/` can build it
    field by field from a form without inventing key names.
    """

    def __init__(self, name="MyAI", civ=None, army=None, villagers=30,
                 attack_at=20, age="feudal-age", split=None, wall=False):
        # A label, not script.  See `_one_line`: this string is interpolated
        # into the file's first comment line, so a newline in it used to end
        # the comment and let the rest of the label run as code.
        self.name = _one_line(name) or "MyAI"
        # Same boundary rule as `army` below: resolve to the engine's own
        # spelling HERE and keep the player's word when it does not resolve, so
        # `check()` can report it instead of emitting a token the engine reads
        # as nothing.  Until this existed the line was
        # `self.civ = (civ or "").strip().lower()` and the value went straight
        # into `(civ-selected %(civ)s)`: 「不列颠」 put Chinese into the file and
        # "british" (the .dat's spelling) is not the token the engine's name
        # table holds ("briton").  Both produced a script that loads and whose
        # civilisation rule never fires, with `problems` empty.
        self.civ = None
        self.civ_unresolved = None
        want_civ = (civ or "").strip() if isinstance(civ, str) else (civ or "")
        if want_civ:
            resolved = civnames.engine_name(want_civ)
            if resolved:
                self.civ = resolved
            else:
                self.civ_unresolved = str(want_civ)
        # Resolve to the engine's own names HERE, not at the emission sites.
        # `_production` used to call `_unit_line` per unit, but `compose` builds
        # its rules from `aistrat`, so that function is not on the path: the
        # player's word went straight into `(train knight)`, which loads, runs,
        # and trains nothing.  Resolving once at the boundary means every
        # consumer (aistrat's production table, its counter table, the emitted
        # defconst) sees a name the engine accepts.
        self.army = []
        self.army_unresolved = []
        self.notes = []
        for word, want in _army_list(army):
            line = _unit_line(word)
            if line:
                # Bounded like every other count, and reported under `army`
                # with the player's own words in the row: "knight:0" is what
                # they typed, and "0" alone would not say which unit.
                bounded = _bounded(want, "army", [])
                if bounded != want:
                    self.notes.append({
                        "field": "army", "value": "%s:%d" % (word, want),
                        "why": "要 %d..%d 之间的数；已按 %d 生成"
                               % (COUNT_BOUNDS["army"][0], COUNT_BOUNDS["army"][1],
                                  bounded)})
                self.army.append((line, bounded))
            else:
                self.army_unresolved.append(word)
        # Bounded, and the clamp is reported through `notes` -> `problems`.
        # `int()` alone let -5 become `(defconst desired-villagers -5)`.
        # (`self.notes` is created above, before the army loop, which clamps
        # its own per-unit counts.)
        self.villagers = _bounded(villagers, "villagers", self.notes)
        self.attack_at = _bounded(attack_at, "attack_at", self.notes)
        # Same rule as the counts above.  `space-age` used to become
        # `feudal-age` with `problems` empty: a player who typed it got a
        # castle-age plan that researches in the wrong order and no sentence
        # anywhere saying the word was not a phase.
        if age in AGES:
            self.age = age
        else:
            self.age = "feudal-age"
            if age:
                self.notes.append({
                    "field": "age", "value": age,
                    "why": "引擎没有这个时代；已按 封建时代 生成"
                           "（可选：%s）" % " / ".join(AGES)})
        # Same boundary rule, for the four numbers a split carries.  Also the
        # reason composing can no longer raise: `aistrat` does `int(...)` on
        # each value, and a posted "abc" reached it unchanged.
        self.split = _split_checked(split, self.notes)
        self.wall = _truthy(wall)

    def as_dict(self):
        return dict(name=self.name, civ=self.civ, army=[list(a) for a in self.army],
                    villagers=self.villagers, attack_at=self.attack_at,
                    age=self.age, split=self.split, wall=self.wall,
                    civ_unresolved=self.civ_unresolved)


def _num(n):
    """The engine takes integers for these; a float would be a silent no-op."""
    try:
        return int(round(float(n)))
    except (TypeError, ValueError):
        return 0


_TRAIN_NAMES = None
_VOCAB = None


def _vocab():
    """The shared `ailang.Vocab`, so `ainl.train_name` and this module agree.

    `ainl` needs the payload object, not just the train-name set; building it
    once here means the two modules cannot drift onto different snapshots of
    `aoe2mod/data/ai_xs_lang.json`.
    """
    global _VOCAB
    if _VOCAB is None:
        try:
            _VOCAB = ailang.Vocab(ailang.load())
        except (OSError, ValueError):
            return None
    return _VOCAB


def _train_names():
    """The engine's train name domain, loaded once from the shipped payload.

    Why this is not a regex any more: the first version of `_unit_line` passed any
    word matching ``^[a-z][a-z0-9-]*$`` straight through, so ``not-a-unit`` became
    ``(train not-a-unit)``.  That file loads -- `train` is a known command with the
    right arity -- and trains nothing, and neither the checker nor the page can
    tell.  The domain is a closed list in the executable's name table (113 names,
    mined to `ai_train_names`), so the only honest test is membership in it.
    """
    global _TRAIN_NAMES
    if _TRAIN_NAMES is None:
        try:
            _TRAIN_NAMES = frozenset(ailang.load().get("ai_train_names") or ())
        except (OSError, ValueError):
            _TRAIN_NAMES = frozenset()
    return _TRAIN_NAMES


def _unit_line(word, vocab=None):
    """Map a player's word onto a name in the engine's train domain, or None.

    This is a thin alias layer over `ainl.train_name`, which is the ONE place the
    domain rules live.  Keeping a second copy here is what produced the bug this
    docstring is about: `ainl.train_name('militiaman')` correctly answered
    `militiaman-line`, while this function answered None, so the generator told
    the player "the engine has no unit named militiaman" for a name it accepts
    two different spellings of.

    Only the player's own vocabulary (`LINES` -- 步弓, 骑士, 枪兵) is local; the
    domain judgement is delegated.
    """
    w = (word or "").strip().lower()
    if not w:
        return None
    if w in LINES:
        return LINES[w]
    from . import ainl
    vocab = vocab or _vocab()
    if vocab is None:
        return None
    got, _why = ainl.train_name(w, vocab)
    if got and got in _train_names():
        return got
    return None


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
def _constants(plan):
    """The constants the rules below reference.

    Emitting them as `defconst` instead of inline numbers is what makes the
    script editable afterwards: a player changes `desired-villagers` in one place
    and every rule follows, which is the same reason the shipped scripts do it.

    Two of these are not free choices.  `attack-timer` and `defend-timer` are NOT
    names in the engine's own pool (measured: absent from `ai_pool_names`, while
    `timer-running` / `timer-disabled` are present), so `(enable-timer attack-timer
    45)` is only meaningful if this file defines it first -- which is exactly what
    the shipped scripts do (`(defconst defend-timer 7)`, `(defconst attack-timer
    4)`).  Omitting the definition is the quiet kind of broken: the file loads and
    the timer never arms.
    """
    out = ["; ---- constants ----",
           "(defconst desired-villagers %d)" % plan.villagers,
           "(defconst attack-soldier-count %d)" % plan.attack_at,
           "(defconst attack-interval 45)",
           "(defconst defend-soldier-count %d)" % max(4, plan.attack_at // 2),
           "",
           "; timer handles: engine pool does not carry these, so they are declared here",
           "(defconst defend-timer 29)",
           "(defconst attack-timer 4)",
           ""]
    for word, want in plan.army:
        out.append("(defconst desired-%s %d)" % (_slug(word), _num(want)))
    out.append("")
    return out


def _slug(text):
    return re.sub(r"[^a-z0-9-]", "-", (text or "").lower()).strip("-")


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------
HEADER = """\
; %(name)s -- generated by aoe2mod from a plan, not typed by hand.
;
; Every rule below is a shape copied from the game's own scripts:
;   phase / age gate   AiBuilder/phaseUpdate.per
;   gatherer split     AiBuilder/economy.per
;   production         AiBuilder/militaryUnits.per
;   attack             AiBuilder/militaryBehavior.per
;
; Tuning is yours.  The numbers are the shipped scripts' defaults, not advice.
"""


def compose(plan):
    """Plan -> the text of one complete `.per` file.

    The rule bodies come from :mod:`aistrat`, which keeps "which situation, which
    unit" as a table instead of code.  That indirection is the whole point: the
    player edits a table entry (or a UI row) and the emitted script follows, and
    every entry carries a shipped-script citation, so nothing here is invented.

    A single file rather than the shipped `(load "sub\\file")` chain: a chain is
    what a 40 000-line AI needs, and it makes a hand-edited script fail with
    "cannot find file" when one part is renamed.  One file has no such failure
    mode, and the engine loads it the same way.
    """
    parts = [HEADER % {"name": plan.name}]
    parts += _constants(plan)
    parts += [r for r in aistrat.rules(plan)]
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def check(plan, vocab=None):
    """Compose, then validate with the same checker the editor uses.

    Returns ``(text, diagnostics, problems)``.  ``problems`` is the list of plan
    entries this generator could not express -- reported, never silently dropped,
    because a player who asked for camel archers and got no camel archers needs to
    be told.
    """
    vocab = vocab or ailang.Vocab(ailang.load())
    problems = []
    for word in plan.army_unresolved:
        problems.append({"field": "army", "value": word,
                         "why": "引擎没有这个单位名；已跳过（可用：%s）"
                                % "、".join(sorted(set(LINES.values())))})
    if plan.civ_unresolved:
        problems.append({"field": "civ", "value": plan.civ_unresolved,
                         "why": "引擎不认识这个文明名；已跳过（可以写中文名，"
                                "例如 不列颠 / 印加 / 达罗毗荼）"})
    problems.extend(plan.notes)
    text = compose(plan)
    return text, ailang.validate_ai(text, vocab), problems


def write(plan, path, vocab=None):
    """Write the script to ``path``.  Returns ``(path, diagnostics, problems)``."""
    text, diags, problems = check(plan, vocab)
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path, diags, problems


def from_sentences(sentences, name="MyAI"):
    """Best-effort plan from Chinese sentences.

    Only the fields a sentence can actually pin down are read; anything absent
    keeps the shipped default.  This is the bridge from `ainl` to a whole script:
    the player describes the game plan, not the syntax.
    """
    plan = Plan(name=name)
    army = []
    for s in sentences or []:
        r = ainl.understand(s, ailang.Vocab(ailang.load()))
        if r.action == "train" and r.entity:
            army.append((r.entity, r.number or 10))
        elif r.action == "count" and r.entity and r.number:
            plan.attack_at = _num(r.number)
        elif r.action == "gather" and r.number:
            pct = _num(r.number)
            if 0 < pct <= 100:
                merged = dict(SPLITS["feudal"])
                merged["food"] = pct
                # Through the same guard the constructor uses: this path builds
                # the dict itself, so it used to be the one place a bad number
                # could still reach `aistrat`'s `int()`.
                plan.split = _split_checked(merged, plan.notes)
        for age in AGES:
            if age.replace("-", " ") in (s or "") or age in (s or ""):
                plan.age = age
    if army:
        plan.army = army
    return plan
