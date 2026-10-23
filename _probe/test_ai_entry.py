# -*- coding: utf-8 -*-
"""The AI entry point writes SENTENCES, and the reader judges them.

Why this nail exists at all
---------------------------
"AI 走 API" is in the objective, and the easy version of it -- let a model emit
intents -- would quietly delete every guarantee this project has paid for.  The
sentence layer refuses what it cannot read, `plan()` refuses what the build
cannot do, and `test_plan_build_agreement` asserts those two say the same thing.
A model writing intents re-enters BELOW all three.

So the nail asserts the shape rather than the intelligence:

  A. with no configuration the route is honest -- `available: false`, and asking
     for sentences gives a Chinese refusal, not a stack trace;
  B. the grammar the endpoint is told is built FROM the loaded schema, so an
     intent that exists cannot be missing from it and an intent a sentence cannot
     reach is named as API-only instead of hidden;
  C. `ask()` returns sentences and nothing else -- no intent, no plan, no bytes;
  D. a model that ignores the prompt (numbered list, code fence, bullets) still
     yields bare sentences, because stripping markers is cheaper than another
     round of instructions.

C is the one worth writing down: if `ask()` ever returned an intent, a future
caller could skip the reader, and every refusal this project developed would
become dead code for that path.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod import ai as AI                     # noqa: E402
from aoe2mod.ui import server as S               # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    """NOTE the argument order: label first.

    Most nails in this project take `check(ok, label, ...)`.  Getting that
    backwards once already produced three assertions that were always true
    (`check("some label", ...)` binds the string to `ok`), so this file states
    its own order and every call below reads as a sentence.
    """
    print(("  ok   " if ok else "  FAIL ") + label
          + (("  :: " + str(detail)) if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def main():
    app = S.App()

    print("=== A. no configuration is an honest state, not a broken button")
    for name in (AI.KEY_ENV, AI.BASE_ENV, AI.MODEL_ENV):
        os.environ.pop(name, None)
    got = app.ai_meta()
    check("the meta route answers at all", got.get("ok") is True, got)
    check("the screen is told not to draw the box", got.get("available") is False,
          got.get("available"))
    check("and to call a model nothing", got.get("model") in (None, ""),
          got.get("model"))
    check("it says what the model would be asked to write",
          got.get("writes") == "sentences", got.get("writes"))
    try:
        app.ai_sentences("把村民血量改高一点")
        refused = ""
    except Exception as exc:
        refused = str(exc)
    check("asking anyway refuses in Chinese", "AI" in refused or "接口" in refused,
          refused)
    # A refusal that leaks the variable VALUES would print a key when one is set.
    check("the refusal names the variables, never their values",
          "AOE2MOD_AI_KEY" in refused and "=" not in refused.split("AOE2MOD_AI_MODEL")[0],
          refused)
    # The route wrapper prefixes unexpected exceptions with their class name so a
    # player can quote it in a bug report.  AIError is not unexpected: it is this
    # product refusing in Chinese, and "AIError: 这个版本没有配 AI 接入口…" is an
    # English word glued to the front of a sentence written for a player.  This
    # was caught through the live route, which is the only place it shows.
    check("the surfaced refusal carries no English class name",
          S._sentence(AI.AIError("这个版本没有配 AI 接入口")) == "这个版本没有配 AI 接入口",
          S._sentence(AI.AIError("这个版本没有配 AI 接入口")))
    check("...while an unexpected exception still says which class it was",
          "ZeroDivisionError:" in S._sentence(ZeroDivisionError("boom")),
          S._sentence(ZeroDivisionError("boom")))

    print()
    print("=== B. the grammar comes from the schema, and admits what it cannot reach")
    meta = app.meta()
    brief = [{"id": i["id"], "title": i["title"], "fields": i["fields"],
              "by_sentence": i["by_sentence"]} for i in meta["intents"]]
    text = AI.grammar(brief)
    by_sentence = [i["id"] for i in brief if i["by_sentence"]]
    api_only = [i["id"] for i in brief if not i["by_sentence"]]
    check("every intent a sentence can reach is described",
          all(i in text for i in by_sentence), by_sentence)
    check("each described intent carries its fields",
          all(("（字段：" in l) for l in text.splitlines() if l.startswith("· ")
              and "——" in l), text[:400])
    check("an intent no sentence can reach is named as API-only, not hidden",
          (not api_only) or ("只能用接口" in text), api_only)
    check("the examples are sentences the reader really parses",
          "村民血量改成 1000" in text and "做成只能选一个" in text, text[-400:])
    check("no example is a bare intent id",
          not any(l.strip("· ") in by_sentence for l in text.splitlines()),
          [l for l in text.splitlines() if l.strip("· ") in by_sentence])

    # The raw schema is the OTHER shape a caller will hand this, and it is the
    # shape that used to crash: `for one in schema_intents` iterates the keys of
    # a dict and then calls .get on a string.  Normalising only one shape keeps
    # that mistake one refactor away, so both are pinned here -- and so is the
    # worse failure next to it, a bare mapping that silently produced an EMPTY
    # grammar (a model told nothing answers nothing, and it looks like the model
    # being unhelpful rather than like this function dropping its input).
    import aoe2mod.intent.compiler as _C
    _schema, _bindings = _C.load_schema()
    _raw_intents = _schema.get("intents") or {}
    _raw_text = AI.grammar(_raw_intents)
    check("the raw schema shape produces the same grammar, not a crash",
          "unit.stat" in _raw_text and "（字段：" in _raw_text,
          _raw_text[:200])
    check("...and it is the whole grammar, not an empty one",
          len(_raw_text.splitlines()) > len(by_sentence),
          [len(_raw_text.splitlines()), len(by_sentence)])
    # A schema spec has no `by_sentence`; that is a property of the reader, so it
    # must be derived from ui/nl.py rather than assumed true.  Defaulting to true
    # would advertise plugin intents as reachable by a sentence.
    _fake = {"intents": {"unit.stat": {"title": "改数值"},
                         "plugin.only": {"title": "插件意图"}}}
    _fake_text = AI.grammar(_fake)
    check("a spec with no flag is judged by the reader, not assumed reachable",
          "plugin.only" in _fake_text and "只能用接口" in _fake_text,
          _fake_text)
    check("...while one the reader does cover is described normally",
          "unit.stat" in _fake_text, _fake_text)

    print()
    print("=== C. ask() returns sentences, and only sentences")
    # A local endpoint, so this exercises the real HTTP path without a network.
    import http.server
    import threading
    seen = {}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            seen["body"] = body
            seen["auth"] = self.headers.get("Authorization")
            seen["path"] = self.path
            # A deliberately disobedient answer: numbered, bulleted, fenced.
            content = ("1. 村民血量改成 1000\n"
                       "```\n"
                       "- 弓箭手攻击力加 2\n"
                       "* 织布机研究时间减 5\n"
                       "\n"
                       "# 说明\n"
                       "  · 印加不能造蔷琵侦察兵  \n")
            payload = {"choices": [{"message": {"content": content}}]}
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % httpd.server_address[1]
    os.environ[AI.BASE_ENV] = base
    os.environ[AI.KEY_ENV] = "sk-test-not-a-real-key"
    os.environ[AI.MODEL_ENV] = "some-model"
    try:
        got = app.ai_meta()
        check("with the three variables set the box becomes available",
              got.get("available") is True, got.get("available"))
        check("and the model name is reported, not guessed",
              got.get("model") == "some-model", got.get("model"))

        out = app.ai_sentences("让村民更耐打，顺手让弓手更凶")
        ai = out.get("ai") or {}
        lines = ai.get("sentences") or []
        check("the answer is a list of sentences",
              isinstance(lines, list) and len(lines) == 4, lines)
        check("numbered, fenced, bulleted and blank lines are stripped",
              lines == ["村民血量改成 1000", "弓箭手攻击力加 2",
                        "织布机研究时间减 5", "印加不能造蔷琵侦察兵"], lines)
        # THE assertion of this file: nothing but text crosses back.  An intent
        # here would let a caller skip the reader, and every refusal developed in
        # this project would be dead code for that path.
        check("and nothing but text crosses back -- no intent, no plan, no bytes",
              set(ai) == {"ok", "sentences", "model"}, sorted(ai))
        check("the request went to the OpenAI-shaped path",
              seen.get("path") == "/chat/completions", seen.get("path"))
        check("the key travelled as a bearer token",
              seen.get("auth") == "Bearer sk-test-not-a-real-key", seen.get("auth"))
        sent = seen.get("body") or {}
        system = ((sent.get("messages") or [{}])[0].get("content") or "")
        check("the endpoint was told the grammar, not just the wish",
              "这个工具能听懂的意图" in system, system[:200])
        check("temperature is pinned, so a re-run cannot silently differ",
              sent.get("temperature") == 0, sent.get("temperature"))
        check("the player's wish is the user turn, verbatim",
              ((sent.get("messages") or [{}, {}])[1].get("content"))
              == "让村民更耐打，顺手让弓手更凶",
              (sent.get("messages") or [{}, {}])[1].get("content"))

        print()
        print("=== D. a broken endpoint is a sentence, not a traceback")
        os.environ[AI.BASE_ENV] = "http://127.0.0.1:9"
        try:
            app.ai_sentences("村民血量改成 1000")
            msg = ""
        except Exception as exc:
            msg = str(exc)
        check("an unreachable endpoint refuses in Chinese", "连不上接口" in msg, msg)
    finally:
        httpd.shutdown()
        for name in (AI.KEY_ENV, AI.BASE_ENV, AI.MODEL_ENV):
            os.environ.pop(name, None)

    print()
    if FAILS:
        print("AI ENTRY: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("AI ENTRY: A MODEL WRITES SENTENCES, THE READER JUDGES THEM, "
          "AND NOTHING ELSE CROSSES BACK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
