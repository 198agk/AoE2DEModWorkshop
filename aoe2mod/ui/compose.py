"""Turn a form into a Chinese sentence the reader already understands.

Why this exists, and why it lives beside the reader rather than in the page:
`aoe2mod/ui/nl.py` is one-directional -- it reads a sentence and returns an
intent.  A page that offers a form has to go the other way, and the only honest
way to do that is to compose a sentence the reader will accept and let the
reader be the judge.  So this module is deliberately small: it renders a
template from `schema/sentences.json` and hands you a string.  It never builds
an intent itself.

The consequence worth stating out loud: a template that composes a sentence the
reader cannot read is a broken template, not a broken test.  That is what
`_probe/test_compose_roundtrip.py` measures, form by form, and the round trip is
the whole reason the two directions can be kept in one file rather than two
drifting ones.

Where the table lives matters.  `schema/sentences.json` sits next to
`intents.json` because it is declaration, not code: a plugin that ships a new
sentence shape ships a template there, exactly like it ships an intent.  It is
read through the same roots the schema loader uses, so a plugin dropped in while
the tool runs is visible here too -- the same bug that made `stat_words()` cache
under a constant (fixed 2026-10-25) would otherwise come back one layer up.
"""

import io
import json
import os

SENTENCES_FILE = "sentences.json"


def schema_roots(plugin_env=None):
    """The directories searched for `sentences.json`, in ascending priority.

    Deliberately mirrors `aoe2mod.intent.compiler._plugin_roots()`: the shipped
    schema directory first, then each plugin root.  Later roots win, so a plugin
    can replace a form the way it can replace an intent.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = [os.path.join(here, "schema")]
    env = plugin_env if plugin_env is not None else os.environ.get("AOE2MOD_PLUGINS")
    if env:
        for part in str(env).split(os.pathsep):
            part = part.strip()
            if not part:
                continue
            roots.append(os.path.join(part, "schema") if os.path.basename(part) != "schema" else part)
    return [r for r in roots if os.path.isdir(r)]


def _merge(into, doc):
    """Merge one `sentences.json` over another.

    Merging rather than replacing per file, because a plugin that wants to add a
    form to `unit.stat` should not have to restate the two that already exist.
    Forms are keyed by `id`; a same-id form from a later root wins outright.
    """
    for key in ("op_choices",):
        if doc.get(key):
            into[key] = list(doc[key])
    for name, spec in (doc.get("intents") or {}).items():
        dst = into["intents"].setdefault(name, {"label": None, "forms": []})
        if spec.get("label"):
            dst["label"] = spec["label"]
        by_id = {f.get("id"): i for i, f in enumerate(dst["forms"])}
        for form in (spec.get("forms") or []):
            fid = form.get("id")
            if fid in by_id:
                dst["forms"][by_id[fid]] = form
            else:
                dst["forms"].append(form)
    return into


def load(plugin_env=None):
    """The merged sentence table.  Empty when no file exists, never raises."""
    doc = {"version": 1, "op_choices": ["改成", "加", "减"], "intents": {}}
    for root in schema_roots(plugin_env):
        path = os.path.join(root, SENTENCES_FILE)
        if not os.path.isfile(path):
            continue
        try:
            with io.open(path, "r", encoding="utf-8-sig") as fh:
                _merge(doc, json.load(fh))
        except (ValueError, OSError):
            # A malformed template must not take the whole page down: the page
            # falls back to the free-text box, which is the older path and is
            # still correct.
            continue
    return doc


def forms(intent=None, table=None):
    """Every form, or just the ones for one intent, in table order."""
    doc = table if table is not None else load()
    out = []
    for name, spec in doc["intents"].items():
        if intent is not None and name != intent:
            continue
        for form in spec.get("forms") or []:
            out.append({"intent": name, "intent_label": spec.get("label"),
                        "id": form.get("id"), "label": form.get("label"),
                        "template": form.get("template"),
                        "slots": form.get("slots") or []})
    return out


def form(intent, form_id, table=None):
    for f in forms(intent, table):
        if f["id"] == form_id:
            return f
    return None


def required(form_spec):
    return [s for s in form_spec["slots"] if s.get("required")]


def missing(form_spec, values):
    """Which required slots have no value.  Empty list means it can compose."""
    out = []
    for s in required(form_spec):
        v = (values or {}).get(s["name"])
        if v is None or (isinstance(v, str) and not v.strip()):
            out.append(s)
    return out


def compose(form_spec, values):
    """Render the template.  Raises KeyError naming the slot that is missing.

    No cleverness here on purpose: if the caller skipped a required slot, the
    sentence would read as a different sentence, and a differently-read sentence
    is worse than an exception because the reader will happily accept it.

    `default` is filled in (an op word that has an obvious default); `sample` is
    NOT.  A sample is a placeholder for a form that is still empty, and using it
    here would quietly build "村民血量改成1000" for a player who typed no number
    at all.  `samples()` exists precisely so the caller can opt into them.
    """
    vals = dict(values or {})
    for s in form_spec["slots"]:
        if vals.get(s["name"]) in (None, ""):
            if s.get("default") is not None:
                vals[s["name"]] = s["default"]
            else:
                raise KeyError(s["name"])
    # The template puts an op word right before the number; a space is allowed
    # by the reader but a missing one reads more like a person typed it.
    return form_spec["template"].format(**vals)


def samples(form_spec, overrides=None):
    """Default values for every slot, for round-trip testing and previews."""
    vals = {}
    for s in form_spec["slots"]:
        if s.get("sample") is not None:
            vals[s["name"]] = s["sample"]
        elif s.get("default") is not None:
            vals[s["name"]] = s["default"]
        elif s["kind"] == "op":
            vals[s["name"]] = "加"
        elif s["kind"] == "number":
            vals[s["name"]] = 10
    vals.update(overrides or {})
    return vals
