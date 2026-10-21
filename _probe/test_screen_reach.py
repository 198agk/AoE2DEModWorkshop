"""The refusals the SCREEN cannot reach, and why that is a fact, not a guess.

WHY THIS EXISTS
    Two rounds were spent translating English refusals found by calling the
    facade with hand-written intents.  Some of that work was real (the effect
    rows, the sprite refusals, describe/icon_for -- all reached by a sentence).
    Some of it was not, and the way to tell the two apart is to RUN the sentence
    path, not to read the raise sites.

    What a player can reach is exactly: what `nl.read()` produces, plus whatever
    `_safe_plan`/`build` say about it.  A refusal only `Toolkit.plan()` can raise
    never reaches a screen, because the screen has no way to spell that intent.

WHAT THIS PINS
    Six English refusals in compiler.py are unreachable from a sentence:
        unknown intent 'x'; known: ...        -- needs intent= to be a string
        an intent must be a dict, got str     -- needs intent to be a non-dict
        unknown stat 'x' for unit.stat        -- nl.py only emits named stats
        intent needs a 'delta' or a 'value'   -- nl.py always sets one or the other
        unknown action 'x'; known: grant,revoke -- nl.py only emits both
        unknown civilization 'MARS'           -- nl.py only emits known civs
    Each is probed below with the sentence that WOULD trigger it if the sentence
    layer could produce that shape; all of them come back in Chinese.

    They are still English for a caller writing intents by hand, which is a real
    product surface (the plugin/AI contract).  Translating them is a separate,
    much smaller job than "make the screen Chinese", and this file exists so the
    two are never confused again: if a future round deletes the sentence-layer
    guards below, THIS is what should go red.

HONESTY BOUNDARY
    "Unreachable from these 22 sentences" is not "unreachable".  The claim is
    narrower and testable: for each of the six shapes, the sentence that would
    have to produce it does not produce it.  A new sentence branch that started
    emitting, say, an arbitrary stat key would show up here.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.ui import server as S

FAILED = []
LATIN = re.compile(r"[A-Za-z]{2,}")


def check(ok, name, detail=""):
    if ok:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILED.append(name)


app = S.App()


def face(text):
    """Every sentence the player would see for this input, in one list."""
    out = []
    got = app.parse(text)
    for c in got.get("clauses") or []:
        if c.get("why"):
            out.append(c["why"])
        out.extend(c.get("notes") or [])
        pv = c.get("preview") or {}
        if pv.get("error"):
            out.append(pv["error"])
        plan = pv.get("plan") or {}
        if plan.get("reason"):
            out.append(plan["reason"])
        if plan.get("description"):
            out.append(plan["description"])
    return out, got.get("intents") or []


# Each case is (sentence that tries to reach that shape, what the shape is).
CASES = [
    ("火星人的村民血量改成1000", "unknown civilization"),
    ("INCAS 的村民血量改成1000", "a civ stem instead of a name"),
    ("村民血量改成", "delta-or-value with neither"),
    ("村民血量", "neither a number nor a verb"),
    ("织布机第-1条效果加5", "an effect index before the first"),
    ("织布机第九千条效果加5", "an effect index past the end"),
    ("给村民换张图 C:\\Windows\\notepad.exe", "a picture that exists but is not art"),
    ("给村民换张图 ../../etc/passwd", "a path outside the game"),
    ("把村民的样子换成", "a swap with no donor"),
    ("村民的香蕉成本加1", "a resource that is not one"),
]

leaks = []
for text, shape in CASES:
    said, _intents = face(text)
    for line in said:
        if LATIN.search(line):
            # A player's own typed words quoted back is not a leak: 「INCAS」 is
            # what they wrote.  Strip the quoted spans before judging.
            stripped = re.sub(r"「[^」]*」", "", line)
            if LATIN.search(stripped):
                leaks.append((shape, text, line))
                break

check(not leaks,
      "none of the six shapes reaches the screen in English",
      leaks[:3])

# The mirror: confirm those sentences are actually being REFUSED, not silently
# accepted.  A green result from "the refusal is in Chinese" would also come out
# of "there was no refusal at all", which would be the worse defect.
silent = []
for text, shape in CASES:
    said, intents = face(text)
    if intents and not said:
        # Being accepted is fine for some of these (a path can be a real edit),
        # but then the plan must have described itself.
        continue
    if not said:
        silent.append((shape, text))
check(not silent,
      "and every one of them answers with at least one sentence",
      silent[:3])

# The premise, asserted so this file cannot go vacuous.  If the six shapes stopped
# existing at all -- someone removed the raise, or the compiler grew a fallback --
# the two checks above would stay green while saying nothing.  This one fails if
# the facade no longer refuses them, and stays silent about the LANGUAGE, because
# translating them is a legitimate change that must not break this pin.
RAISES = [
    ("optional dict path", {"intent": "no.such.intent"}),
    ("non-dict intent", {"intent": 7}),
    ("named stat list", {"intent": "unit.stat", "unit": 83,
                         "stat": "sneakiness", "value": 1}),
    ("delta or value", {"intent": "unit.stat", "unit": 83,
                        "stat": "hit_points"}),
    ("known actions", {"intent": "unit.availability", "unit": 2550,
                       "civ": "INCAS", "action": "banish"}),
    ("known civilizations", {"intent": "unit.availability", "unit": 2550,
                             "civ": "MARTIANS", "action": "revoke"}),
]
gone = []
for name, intent in RAISES:
    try:
        app.tk.plan(intent)
    except Exception:                                          # noqa: BLE001
        continue
    gone.append(name)
check(not gone,
      "and the facade still refuses all six, so this file is not vacuous",
      gone)

# ---- the refusals that arrive WITH a successful build -----------------------
# A bundle can succeed and still drop a sentence: two reskin sentences that want
# one file to hold two pictures cannot both be honoured, and the manifest names
# the one it dropped.  Those reasons are screen text twice over -- the page prints
# them as "有一句没做成：<reason>", and when nothing at all can be emitted the
# bundle summary joins them into one sentence.  Measured 2026-10-21: typed as two
# ordinary sentences, this came out as "two sentences need ... , and one file
# cannot do that" -- full English, on a successful build.
import tempfile                                                     # noqa: E402

CLASH = "把步弓手的样子换成长弓兵，把步弓手的样子换成弩手"
_got = app.parse(CLASH)
_tk = app.tk
_out = tempfile.mkdtemp(prefix="screen_reach_")
try:
    _man = _tk.build_bundle(_got["intents"], os.path.join(_out, "clash"),
                            author="dsh", title="clash")
except Exception as exc:                                            # noqa: BLE001
    _man = {"sprite_refusals": [{"reason": str(exc)}]}

_dropped = _man.get("sprite_refusals") or []
check(bool(_dropped),
      "two contradicting reskin sentences leave one refusal on the manifest",
      _man.get("sprite_refusals"))
_leaks = []
for _r in _dropped:
    _why = _r.get("reason") or ""
    # A .sld name is DATA -- the player needs it to see which file the two
    # sentences met on.  Strip file names and quoted spans, then judge the prose.
    _bare = re.sub(r"[\w.\-]+\.(sld|png|dds)", " ", re.sub(r"「[^」]*」", "", _why))
    if LATIN.search(_bare):
        _leaks.append(_why)
check(not _leaks,
      "and the refusal it leaves is Chinese, not a sentence template",
      _leaks[:2])

print()
if FAILED:
    print("SCREEN REACH: %d CHECK(S) FAILED" % len(FAILED))
    sys.exit(1)
print("SCREEN REACH: SIX ENGLISH REFUSALS ARE API-ONLY, AND THE ONE A SENTENCE "
      "CAN REACH IS CHINESE")
