# -*- coding: utf-8 -*-
"""Where the model endpoint settings live once the app is a double-clicked exe.

The environment contract in `aoe2mod/ai.py` is the right one for a developer and
the wrong one for a player: nobody who unzips a workshop and runs
`AoE2 DE Mod Workshop.exe` is going to set `AOE2MOD_AI_KEY` in a shell first.  So
there are two sources and one precedence rule:

  1. environment variables -- win unconditionally, so a scripted run or a test
     can never be overridden by whatever was last typed into the box;
  2. `%LOCALAPPDATA%\\aoe2de-mod-workshop\\ai.json` -- what the settings panel
     writes.

The key IS written to disk here, in plain text, because there is no other way for
a GUI app to remember it across launches.  That is a real trade and it is stated
on the panel instead of being quietly assumed: this file is per-user, it is
outside the install folder, and it is never included in a mod or a bundle.  What
this module will not do is put the key into any message, log line, or API
response -- `public()` is the only shape that leaves the process.
"""

import json
import os

from .mod.provenance import state_dir

FILE_NAME = "ai.json"

#: Same names `aoe2mod/ai.py` reads.  Kept in one place so the two modules cannot
#: drift into disagreeing about which variable means what.
BASE_ENV = "AOE2MOD_AI_BASE"
KEY_ENV = "AOE2MOD_AI_KEY"
MODEL_ENV = "AOE2MOD_AI_MODEL"

DEFAULT_BASE = "https://api.openai.com/v1"


def path():
    return os.path.join(state_dir(), FILE_NAME)


def _read(path_override=None):
    try:
        with open(path_override or path(), "rb") as fh:
            doc = json.loads(fh.read().decode("utf-8-sig"))
    except (IOError, OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def saved(path_override=None):
    """What the settings panel last wrote, as a plain dict (may be empty)."""
    doc = _read(path_override)
    out = {}
    for key in ("base", "key", "model"):
        val = doc.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out


def effective(path_override=None):
    """The endpoint this build will actually use, or None when unconfigured.

    Precedence is per field, not all-or-nothing: a player who set only the key in
    the box and exports `AOE2MOD_AI_MODEL` for one experiment gets the saved key
    with the exported model, which is what they meant.
    """
    conf = saved(path_override)
    base = (os.environ.get(BASE_ENV) or conf.get("base") or DEFAULT_BASE).rstrip("/")
    key = os.environ.get(KEY_ENV) or conf.get("key") or ""
    model = os.environ.get(MODEL_ENV) or conf.get("model") or ""
    if not key:
        return None
    return {"base": base, "key": key, "model": model or "gpt-4o-mini"}


def save(base, key, model, path_override=None):
    """Write the settings.  An empty key clears them.

    Returns the public view, never the key.  Refusing to write `None` for the key
    while keeping the old one would make "clear the key" impossible from the
    panel, so an explicit empty string is honoured as a delete.
    """
    target = path_override or path()
    doc = {"version": 1}
    base = (base or "").strip()
    key = (key or "").strip()
    model = (model or "").strip()
    if base:
        doc["base"] = base
    if key:
        doc["key"] = key
    if model:
        doc["model"] = model
    if not key:
        # No key means no endpoint; keeping a stale base/model around would make
        # `public()` report "configured" for a build that cannot call anything.
        try:
            os.remove(target)
        except OSError:
            pass
        return public(path_override)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"))
    except (IOError, OSError) as exc:
        raise ValueError("设置存不下来：%s" % exc)
    return public(path_override)


def public(path_override=None):
    """The shape the page may see: no key, ever, in any form.

    `has_key` and `key_tail` are enough for the panel to say "已保存（…a1b2）"
    and let the player recognise which key is in use without the full value
    crossing the wire a second time.
    """
    conf = effective(path_override)
    if conf is None:
        return {"available": False, "base": None, "model": None,
                "has_key": False, "key_tail": "", "source": "none"}
    raw = conf["key"]
    env_key = os.environ.get(KEY_ENV) or ""
    return {"available": True,
            "base": conf["base"],
            "model": conf["model"],
            "has_key": True,
            "key_tail": raw[-4:] if len(raw) >= 8 else "",
            "source": "env" if env_key else "file"}
