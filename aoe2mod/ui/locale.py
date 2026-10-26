"""Every word the screen says about itself, loaded from a file instead of baked in.

Why this exists
---------------
The screen's Chinese used to live in two languages of record: an HTML file and a
Python module.  This project's most expensive repeated failure is *a sentence
that was true on the day it was written*, and a sentence split across two files
cannot be found by grepping for its translation -- you have to already know both
spellings.  With one table there is one place to look, and one place for a nail
to check.

Design, and what it deliberately is not
---------------------------------------
* **Chinese is the source language.**  The screen is written in Chinese; `en` is
  filled only where a real translation exists.  A half-translated screen is worse
  than a Chinese one, so a missing key falls back to Chinese rather than to the
  key name.  A key that resolves to nothing prints the key itself -- loud on
  screen, which is what you want when a heading is missing.
* **`{name}` placeholders are substituted, not formatted.**  `str.format` would
  explode on a stray brace in a player-facing sentence (there are Chinese
  sentences here with 「」 and braces in examples), and a crash while rendering a
  hint is a blank page.
* **The table merges across plugin roots**, same order and same reason as
  `aoe2mod.ui.compose`: shipped first, plugins after, later wins.  A plugin that
  adds an intent can add its own wording without restating the shipped table.
* **It never raises.**  A broken or missing locale file means "no overrides",
  which is exactly the shipped screen.  Raising here would take the whole page
  down for a wording problem.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SHIPPED = os.path.join(os.path.dirname(HERE), "schema", "locales")
LOCALES_ENV = "AOE2MOD_LOCALES"
DEFAULT_LOCALE = "zh"
_PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


def roots(env=None):
    """Directories to read locale files from, shipped first."""
    env = os.environ if env is None else env
    out = [SHIPPED]
    extra = (env.get(LOCALES_ENV) or "").strip()
    if extra:
        for part in extra.split(os.pathsep):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _read(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict):
        return {}
    strings = doc.get("strings")
    return strings if isinstance(strings, dict) else {}


def load(locale=DEFAULT_LOCALE, env=None):
    """The merged table for one locale: `{key: text}`."""
    table = {}
    for root in roots(env):
        path = os.path.join(root, "%s.json" % locale)
        if not os.path.isfile(path):
            continue
        for key, text in _read(path).items():
            if isinstance(text, str):
                table[key] = text
    return table


def fill(text, values=None):
    """Substitute `{name}` placeholders.  Unknown names are left alone."""
    if not values:
        return text

    def one(m):
        key = m.group(1)
        if key in values and values[key] is not None:
            return str(values[key])
        return m.group(0)

    return _PLACEHOLDER.sub(one, text)


def t(key, values=None, locale=DEFAULT_LOCALE, table=None):
    """One string, substituted.  Falls back to the key itself when absent.

    Returning the key (rather than "") is deliberate: an empty string on screen
    looks like a layout bug, while `mods.heading` in a heading looks like what it
    is -- a missing table entry somebody has to add.
    """
    table = load(locale) if table is None else table
    text = table.get(key)
    if text is None:
        return key
    return fill(text, values)


def keys_missing(table, wanted):
    """Which of `wanted` are not in `table`.  For nails, not for the screen."""
    return [k for k in wanted if k not in table]


def placeholders(text):
    """The placeholder names in one string, so a nail can compare two languages."""
    return sorted(set(_PLACEHOLDER.findall(text or "")))
