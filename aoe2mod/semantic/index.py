# -*- coding: utf-8 -*-
"""Semantic layer: turn "the archer" into unit id 4, in the user's language.

The research phase produced two resolution tables (2,693 unit ids, 1,510 tech
ids) plus a set of hard-won rules about when those names can be trusted.  Those
rules are the whole point of this module:

* **118 unit ids resolve to DIFFERENT names per civilization** -- 57 civs use
  the standard id, and exactly 6 "Chronicles" civs use a 405xxx backup id and
  are genuinely different units.  So a single name->id table is NOT enough;
  the variant map must be exposed.
* **`CivTechTrees`'s `Name` field is stale and must never be used.** 44
  conflicts, and the shipped string table supports our value 44/44 times and
  the JSON value 0 times.  Always use `name_string_id`.
* **Internal code names are NOT names.** Only 310 of 1,651 satisfy
  internal == en, and 51 code names map to multiple different units. They are
  debug labels only.

This module resolves *names*, not bytes; it never touches the .dat.
"""
import json
import os
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "data")

#: Chinese names for the two kinds this index resolves.  Kept here rather than
#: imported from `intent.compiler` (which imports THIS module) so the refusal
#: above cannot become a circular import; an unknown kind falls through as-is,
#: same rule as `compiler.kind_label`.
_KIND_ZH = {"unit": "单位", "tech": "科技", "building": "建筑"}


def _load(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def _norm(s):
    """Fold a display name for matching: casefold, strip accents, collapse
    whitespace and drop punctuation that differs between localisations."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.casefold()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in " _-·・'’.,:;()[]/\\+&":
            out.append(" ")
        else:
            out.append(" ")
    return " ".join("".join(out).split())


class Entity(object):
    """One resolvable unit or technology."""

    __slots__ = ("kind", "id", "internal", "en", "zh", "tw", "name_string_id",
                 "resolved", "reason", "civ_variants", "_extra")

    def __init__(self, kind, uid, raw):
        self.kind = kind
        self.id = uid
        self.internal = raw.get("internal")
        self.en = raw.get("en")
        self.zh = raw.get("zh")
        self.tw = raw.get("tw")
        self.name_string_id = raw.get("name_string_id")
        self.resolved = bool(raw.get("resolved"))
        self.reason = raw.get("unresolved_reason")
        self._extra = raw
        cv = raw.get("civ_variants")
        self.civ_variants = cv if isinstance(cv, dict) else None

    @property
    def display(self):
        """The name to show a user, preferring the current locale's field."""
        return self.zh or self.en or self.internal or ("%s %d" % (self.kind, self.id))

    @property
    def is_visible(self):
        """Should a player-facing UI ever offer this?

        Objects with no name string id are engine internals, eye candy or
        placeholders (1,036 of them).  They exist and are patchable, but a
        "make the archer stronger" UI must not list them.
        """
        return self.resolved

    def __repr__(self):
        return "<%s %d %r%s>" % (self.kind, self.id, self.display,
                                 "" if self.resolved else " (unresolved)")


class SemanticIndex(object):
    """Name/index resolution over the shipped string tables."""

    def __init__(self, units=None, techs=None):
        self._units_raw = units if units is not None else _load("unit_names.json")
        self._techs_raw = techs if techs is not None else _load("tech_names.json")
        self.units = {int(k): Entity("unit", int(k), v)
                      for k, v in self._units_raw.items()}
        self.techs = {int(k): Entity("tech", int(k), v)
                      for k, v in self._techs_raw.items()}
        self._by_name = {}
        for kind, table in (("unit", self.units), ("tech", self.techs)):
            for e in table.values():
                if not e.is_visible:
                    continue
                for field in (e.zh, e.en, e.tw, e.internal):
                    k = _norm(field)
                    if k:
                        self._by_name.setdefault((kind, k), []).append(e)

    # ---- lookup -----------------------------------------------------------
    def get(self, kind, uid):
        return (self.units if kind == "unit" else self.techs).get(uid)

    def find(self, kind, text, limit=25):
        """Resolve a user-typed name to candidate entities, best first.

        Resolution order (strict to loose):
          1. exact normalised match on zh/en/tw/internal
          2. exact numeric id
          3. substring match
        Returns a list; never raises, because the UI needs "did you mean".

        ``text`` may be an int: ``search()`` hands out ``id`` as a number, so a
        UI that echoes one back must not fall into the substring branch and
        come up empty.
        """
        if isinstance(text, bool):
            text = str(text)
        if isinstance(text, int):
            e = self.get(kind, text)
            return [e] if e is not None else []
        t = _norm(text)
        out = []
        seen = set()

        def push(e):
            if e.id not in seen:
                seen.add(e.id)
                out.append(e)

        if t.isdigit():
            e = self.get(kind, int(t))
            if e is not None:
                push(e)

        for e in self._by_name.get((kind, t), ()):
            push(e)

        if not out and t:
            table = self.units if kind == "unit" else self.techs
            for e in table.values():
                if not e.is_visible:
                    continue
                for field in (e.zh, e.en, e.tw, e.internal):
                    if field and t in _norm(field):
                        push(e)
                        break
        return out[:limit]

    def resolve_one(self, kind, text):
        """Resolve to exactly one entity, or raise with a useful message."""
        hits = self.find(kind, text)
        if not hits:
            # This message reaches the screen: `Toolkit.describe` and the intent
            # compiler both funnel a failed lookup through here, and
            # `_probe/tmp_screen_reach.py` showed "no unit matches 999999" was
            # what a player saw.  The KIND is translated because the English
            # words "unit"/"tech" are our vocabulary, not the game's.
            raise LookupError("这个版本里没有叫「%s」的%s"
                              % (text, _KIND_ZH.get(kind, kind)))
        if len(hits) > 1:
            exact = [h for h in hits
                     if _norm(text) in {_norm(h.zh), _norm(h.en),
                                        _norm(h.tw), _norm(h.internal)}]
            if len(exact) == 1:
                return exact[0]
            # Same rule as the miss above: this sentence can be read by a player
            # (the compiler funnels it through `IntentError`), so it says the
            # candidates in the game's own words instead of `ambiguous unit ->`.
            raise LookupError(
                "「%s」这个名字对得上 %d 个%s，说不清要哪一个：%s"
                % (text, len(hits), _KIND_ZH.get(kind, kind),
                   "、".join("%d %s" % (h.id, h.display) for h in hits[:6])))
        return hits[0]

    # ---- statistics the UI needs -----------------------------------------
    def stats(self, kind):
        table = self.units if kind == "unit" else self.techs
        total = len(table)
        vis = sum(1 for e in table.values() if e.is_visible)
        variant = sum(1 for e in table.values() if e.civ_variants)
        return {"kind": kind, "total": total, "resolved": vis,
                "unresolved": total - vis, "with_civ_variants": variant,
                "visible_pct": round(100.0 * vis / total, 1) if total else 0.0}


_CACHE = {}


def index():
    """Process-wide default index (building it parses ~2.3 MB of JSON)."""
    if "idx" not in _CACHE:
        _CACHE["idx"] = SemanticIndex()
    return _CACHE["idx"]
