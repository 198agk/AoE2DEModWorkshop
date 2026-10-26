"""Named recipes: the three sentences a player actually types, saved once.

Why this exists
---------------
Every sentence the tool accepts has to be typed again tomorrow.  A player who
works on one mod types the same three lines for a week; a player who comes back
in a month types them from memory or gives up.  MaaEnd solves this with
``instances[]`` in its config -- a name, a task list, and the option values that
were chosen -- and the shape is right: **the thing you save is the input, not the
output.**  Saving a built mod would freeze a stale ``.dat``; saving the sentences
that produced it means the recipe can be rebuilt against whatever data the game
has on the day you run it.

Why sentences and not intents
-----------------------------
The reader is the only thing that decides what a sentence means, and it is the
only thing whose answer is tested (``_probe/test_compose_roundtrip.py``).  A
recipe that stored resolved intents would be a second interpretation of the
player's words, kept in sync by hand.  Storing the sentences means a recipe is
exactly as correct as the reader on the day it runs -- and if the reader gets
stricter, the recipe fails loudly at parse time instead of quietly building
something else.

Where it lives
--------------
The same state directory ``aoe2mod/mod/provenance.py`` already uses, because both
answer the same question ("what did this player do on this machine") and both must
survive the game being updated underneath them.  ``recipes.json`` beside
``builds.json``.  A corrupt file reads as empty for the same reason a corrupt
record does: the worst it can cost is that names disappear, and saying "no
recipes" is the truth in that case.
"""
import io
import json
import os
import time

from ..mod import provenance as _PV

FILE_NAME = "recipes.json"
VERSION = 1

# A name has to survive being shown in a list and being used as a lookup key.
# These are the same limits the mod Title has to respect, minus the ones that only
# matter for a folder name.
MAX_NAME = 60


class RecipeError(Exception):
    """A recipe cannot be saved or read back, in words the player can act on."""


def path():
    return os.path.join(_PV.state_dir(), FILE_NAME)


def _clean_name(name):
    text = (name or "").strip()
    if not text:
        raise RecipeError("配方要有个名字，不然下次没法叫它出来。")
    if len(text) > MAX_NAME:
        raise RecipeError("配方名最多 %d 个字，现在有 %d 个。" % (MAX_NAME, len(text)))
    return text


def _clean_sentences(sentences):
    if isinstance(sentences, str):
        sentences = [sentences]
    if not isinstance(sentences, (list, tuple)):
        raise RecipeError("要保存的是一串句子，收到的是%s。" % type(sentences).__name__)
    out = []
    for item in sentences:
        if not isinstance(item, str):
            raise RecipeError("配方里只能放句子，收到的是%s。" % type(item).__name__)
        text = item.strip()
        if text and text not in out:
            out.append(text)
    if not out:
        raise RecipeError("这个配方一句都没有，存下来也没有东西可以重建。")
    return out


def load(file_path=None):
    """Read the file.  Missing, unreadable or corrupt all read as no recipes."""
    target = file_path or path()
    try:
        raw = io.open(target, encoding="utf-8-sig", newline="").read()
    except (OSError, UnicodeDecodeError):
        return {"version": VERSION, "recipes": {}}
    try:
        doc = json.loads(raw)
    except ValueError:
        try:
            doc = json.loads(raw, strict=False)
        except ValueError:
            return {"version": VERSION, "recipes": {}}
    if not isinstance(doc, dict) or not isinstance(doc.get("recipes"), dict):
        return {"version": VERSION, "recipes": {}}
    out = {}
    for name, item in doc["recipes"].items():
        if not isinstance(item, dict):
            continue
        sentences = [s for s in (item.get("sentences") or []) if isinstance(s, str) and s.strip()]
        if not sentences:
            continue
        out[str(name)] = {
            "sentences": sentences,
            "saved_at": item.get("saved_at") or "",
            "note": item.get("note") or "",
        }
    return {"version": VERSION, "recipes": out}


def save(doc, file_path=None):
    target = file_path or path()
    folder = os.path.dirname(target)
    if folder:
        try:
            os.makedirs(folder)
        except OSError:
            if not os.path.isdir(folder):
                raise RecipeError("存不进这个目录：%s" % folder)
    body = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = target + ".tmp"
    # Write then rename: a half-written file is a file that reads as empty, which
    # would silently drop every name the player saved.
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(body)
    os.replace(tmp, target)
    return target


def rows(file_path=None):
    """Every recipe, oldest name first, in the shape a screen can print."""
    doc = load(file_path)
    out = []
    for name in sorted(doc["recipes"]):
        item = doc["recipes"][name]
        out.append({
            "name": name,
            "sentences": list(item["sentences"]),
            "count": len(item["sentences"]),
            "saved_at": item.get("saved_at") or "",
            "note": item.get("note") or "",
        })
    return out


def get(name, file_path=None):
    return load(file_path)["recipes"].get((name or "").strip())


def remember(name, sentences, note="", file_path=None):
    """Save or replace one recipe.  Returns the stored row."""
    clean = _clean_name(name)
    doc = load(file_path)
    doc["recipes"][clean] = {
        "sentences": _clean_sentences(sentences),
        "saved_at": time.strftime("%Y-%m-%d %H:%M"),
        "note": (note or "").strip(),
    }
    save(doc, file_path)
    return doc["recipes"][clean]


def forget(name, file_path=None):
    """Remove one recipe.  Returns True if something was removed."""
    clean = (name or "").strip()
    doc = load(file_path)
    if clean not in doc["recipes"]:
        return False
    del doc["recipes"][clean]
    save(doc, file_path)
    return True
