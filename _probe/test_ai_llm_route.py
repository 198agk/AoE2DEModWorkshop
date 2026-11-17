# -*- coding: utf-8 -*-
"""The model route writes FILES, so the checker -- not the model -- has the last word.

Why this nail exists
--------------------
`aiwriter.draft` is the only path in the app where bytes produced by a language
model can reach a `.per` or `.xs` file.  The design bets on one thing: the
grammar table learned from 113,987 real call sites decides, and the model only
proposes.  If that bet ever silently inverts -- the model's output accepted
because it looks plausible, the diagnostics dropped because they were noisy --
every guarantee this project paid for is gone while every test still passes.

So the nail asserts the contract, not the model's skill:

  A. with no key the route answers `ok: false` AND `available: false`, and the
     error is a sentence about configuration, not a stack trace;
  B. `draft` refuses to call an endpoint at all when unconfigured -- a fake
     poster that records calls must record zero;
  C. when the model returns code the checker rejects, the repair loop runs, the
     diagnostics are handed back verbatim, and `clean` stays false;
  D. when the model returns code the checker accepts, `clean` is true and the
     code is the model's -- byte for byte, no normalisation;
  E. the response never carries the key, in any field, at any depth.

D is the one worth writing down.  "The model wrote it" must never be reachable
as `ok: true` by a different route (an empty code string, a fallback template);
that would make the panel claim a model draft the model never produced.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.game import aiwriter as W           # noqa: E402
from aoe2mod.ui import server as S               # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label
          + (("  :: " + str(detail)) if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


GOOD = "(defrule\n\t(true)\n=>\n\t(train villager)\n)\n"

BAD = "(defrule\n\t(true)\n=>\n\t(train villager 1 2 3 4)\n)\n"


class Poster:
    """A stand-in for the HTTP call: replays a scripted list of answers."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, messages, timeout=None):
        self.calls.append(messages)
        if not self.answers:
            raise AssertionError("poster called more times than it has answers")
        return self.answers.pop(0)


def main():
    app = S.App()
    saved_env = {}
    for name in ("AOE2MOD_AI_BASE", "AOE2MOD_AI_KEY", "AOE2MOD_AI_MODEL"):
        saved_env[name] = os.environ.pop(name, None)
    from aoe2mod import aisettings as A
    hidden = A.path()
    backup = None
    if os.path.exists(hidden):
        with open(hidden, "rb") as fh:
            backup = fh.read()
        os.remove(hidden)
    try:
        run(app, A, hidden)
    finally:
        for name, val in saved_env.items():
            if val is not None:
                os.environ[name] = val
        if backup is not None:
            with open(hidden, "wb") as fh:
                fh.write(backup)
        elif os.path.exists(hidden):
            os.remove(hidden)


def run(app, A, hidden):
    print("=== A. no key is an honest state")
    got = app.ai_script_draft({"text": "造20个骑士", "dept": "ai"})
    check("ok is false", got.get("ok") is False, got)
    check("available is false", got.get("available") is False, got)
    check("error names the variables",
          "AOE2MOD_AI_KEY" in (got.get("error") or "")
          or "密钥" in (got.get("error") or ""), got.get("error"))

    print("=== B. unconfigured never reaches the wire")
    # An explicit `_poster` is a test seam and is called unconditionally; the
    # config gate lives in `_post`, which is what a real request goes through.
    # So the assertion is on `_post`: no key, no socket, a sentence instead.
    try:
        W._post([{"role": "user", "content": "x"}])
        check("_post refused", False, "returned without raising")
    except W.WriterError as exc:
        check("_post refused", True)
        # The sentence must name the place a player can actually reach.  The
        # environment variable is the fallback, not the instruction: the shipped
        # artifact is an exe, so nobody exports a key before double-clicking one.
        check("refusal points at 设置 -> 模型", "设置" in str(exc) and "模型" in str(exc), str(exc))
        check("...and still names the variable for scripts",
              "AOE2MOD_AI_KEY" in str(exc), str(exc))
    try:
        W.draft("造20个骑士", "ai", app.ailang_vocab())
        check("draft without a poster refused", False, "returned without raising")
    except W.WriterError:
        check("draft without a poster refused", True)

    # Configured from here on, but with a poster instead of a socket.
    os.environ["AOE2MOD_AI_KEY"] = "sk-fake-000000000000"

    print("=== C. a rejected draft is repaired and reported")
    poster = Poster([BAD, BAD, BAD])
    got = W.draft("造20个骑士", "ai", app.ailang_vocab(), _poster=poster)
    check("clean is false", got.get("ok") is False, got.get("ok"))
    check("three rounds", got.get("rounds") == 3, got.get("rounds"))
    check("diagnostics survive", bool(got.get("diagnostics")), got.get("diagnostics"))
    check("code still returned", bool(got.get("code")), repr(got.get("code"))[:80])
    check("three posts", len(poster.calls) == 3, len(poster.calls))
    second = poster.calls[1]
    check("round 2 carries the diagnostics",
          any("参数" in (m.get("content") or "") for m in second),
          [m.get("content", "")[:60] for m in second])

    print("=== D. an accepted draft is the model's bytes, untouched")
    poster = Poster([GOOD])
    got = W.draft("造农民", "ai", app.ailang_vocab(), _poster=poster)
    check("clean is true", got.get("ok") is True, got)
    check("one post", len(poster.calls) == 1, len(poster.calls))
    # `extract_code` strips the outer blank lines (a trailing newline is not part
    # of the program), and does nothing else: no reindent, no command rewriting.
    check("code is the model's, unedited", got.get("code") == GOOD.strip(),
          repr(got.get("code")))
    check("inner newlines preserved",
          got.get("code", "").count("\n") == GOOD.strip().count("\n"),
          repr(got.get("code")))
    check("no diagnostics", got.get("diagnostics") == [], got.get("diagnostics"))

    print("=== D2. the route surfaces the same verdict")
    poster = Poster([GOOD])
    old = W._post
    W._post = poster
    try:
        route = app.ai_script_draft({"text": "造农民", "dept": "ai"})
    finally:
        W._post = old
    check("route ok", route.get("ok") is True, route)
    check("route clean", route.get("clean") is True, route)
    check("route has code", route.get("code") == GOOD.strip(),
          repr(route.get("code")))
    check("route says available", route.get("available") is True, route)

    print("=== E. the key never leaves the process")
    blob = json.dumps(route, ensure_ascii=False)
    check("no key in the draft response", "sk-fake-000000000000" not in blob)
    settings = app.ai_settings_get()
    blob = json.dumps(settings, ensure_ascii=False)
    check("no key in the settings response", "sk-fake-000000000000" not in blob)
    check("settings show a tail", (settings.get("settings") or {}).get("key_tail")
          == "0000", settings.get("settings"))

    print()
    if FAILS:
        print("AI LLM ROUTE: %d FAILED -- %s" % (len(FAILS), "; ".join(FAILS)))
        raise SystemExit(1)
    print("AI LLM ROUTE: ALL OK")


if __name__ == "__main__":
    main()
