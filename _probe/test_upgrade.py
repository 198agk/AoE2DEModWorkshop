# -*- coding: utf-8 -*-
"""Does `aoe2mod/mod/upgrade.py` really carry a mod across an official patch?

THE PROBLEM THIS PROBE IS BUILT FOR
-----------------------------------
A .dat mod is a snapshot of one day's `empires2_x2_p1.dat`.  When the game ships
a new one, the mod's whole 93 MB snapshot is stale: install it and every field
the patch changed is silently reverted, and every field it ADDED is missing.  The
merge engine is supposed to replay the author's EDITS onto the new file; the only
question worth asking is whether it replays them faithfully.

That question cannot be answered by reading the engine.  It is answered by
building files where the right answer is already known -- `make_upgrade_fixtures.py`
does that, and writes the answer into each case's `expect.json` -- and then
checking three separate things per case:

  1. `analyze()` survives, is READ-ONLY (the fixture bytes must be untouched
     afterwards), and reports the conflict count the case is built around.  A
     merge that produces the right file while reporting zero conflicts is still
     lying to the player who has to click 应用.
  2. `upgrade(install=False)` writes a mod folder and hands back a `.dat`, and it
     does not install anything.
  3. The produced `.dat` carries every value `expect.json` asks for, read back
     through the same readers the rest of the product uses.

VOCABULARY
----------
`expect.json` speaks the vocabulary the merge spec was written in (`strategy`
"field"/"records", edit rows carrying `layer/key/field/from/to/status`,
conflicts carrying `base/mod/new`).  The engine grew its own, older vocabulary
(`verdict`, `structural`, edit rows carrying `space/civ/unit/index/at/base_hex/
mod_hex/official_changed`, conflicts carrying `base_was/official_now/mod_wants`).
Both are read here through `normalize_report()`, which is the ONLY place that
knows about either.  When the engine answers in its own words, the probe says so
once, in a `NOTE:` line, and keeps checking the semantics -- a shape mismatch is
worth reporting, not worth hiding the merge result behind.

RUNNING IT BEFORE THE ENGINE EXISTS
-----------------------------------
The engine was written in parallel with this probe, so a probe that crashes on
import is useless: it reports "there is no engine" as if it were "the engine is
broken".  Every missing piece therefore prints

    SKIP: upgrade module has no <name> yet

and exits 2 -- distinguishable from 0 (all cases pass) and 1 (a case failed).

    python -X utf8 _probe/test_upgrade.py              # whole corpus
    python -X utf8 _probe/test_upgrade.py --only name  # one case
    python -X utf8 _probe/test_upgrade.py -v           # every check, not just failures
"""
import contextlib
import hashlib
import inspect
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aoe2mod.dat.locate as L
import aoe2mod.dat.parser as P
import aoe2mod.dat.techfields as TF
import aoe2mod.dat.unitfields as UF

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "_out", "_upgrade_fixtures")
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")

#: Build order, so a run reads like the corpus the builder printed.  A fixture
#: directory that is not listed here is still run -- it is appended -- because a
#: case someone adds by hand must not be silently ignored.
ORDER = ["mod_touches_a", "same_field_conflict", "same_field_agree",
         "mod_untouched_follows_official", "tech_field", "tech_added_by_official",
         "unit_added_by_mod", "unit_removed_by_mod", "byte_identical",
         "cross_generation"]

FAILS = []
NOTES = []
VERBOSE = False
_SAID = set()


def check(ok, label, detail=""):
    if VERBOSE or not ok:
        print(("  ok   " if ok else "  FAIL ") + label
              + ((" :: " + str(detail)) if detail else ""))
    if not ok:
        FAILS.append(label)
    return ok


def note(once, text):
    """Say something once, on stderr-ish stdout, without failing the case."""
    if once in _SAID:
        return
    _SAID.add(once)
    NOTES.append(text)
    print("  NOTE " + text)


def skip(what):
    """The engine is not finished.  Say which piece, and leave with rc=2."""
    print("SKIP: upgrade module has no %s yet" % (what,))
    sys.exit(2)


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _inflated(path):
    """Inflated bytes of a fixture .dat (fixtures are stored as bare deflate)."""
    raw, _how = P.load_dat(path)
    return raw


def _field(value, name):
    """`fields_at[name]["value"]`, or KeyError with the field list attached."""
    if name in value:
        return value[name]["value"]
    raise KeyError("%s is not a field here (have: %s)"
                   % (name, ", ".join(sorted(value)[:12])))


# ---------------------------------------------------------------------------
# one report, in the documented words
# ---------------------------------------------------------------------------
def _hexval(v):
    """`b"\\x00\\x01"` -> `1`; anything already scalar is passed through."""
    if isinstance(v, (bytes, bytearray)):
        return int.from_bytes(v, "big")
    if isinstance(v, str) and v and all(c in "0123456789abcdef" for c in v.lower()) \
            and len(v) % 2 == 0:
        try:
            return int(v, 16)
        except ValueError:
            return v
    return v


def _edit_rows(rep):
    """Every edit row, in the documented shape, from either vocabulary."""
    rows = []
    for e in rep.get("edits") or ():
        if not isinstance(e, dict):
            rows.append(e)
            continue
        if "layer" in e:                                   # documented already
            rows.append(e)
            continue
        note("edit-vocab",
             "analyze() edit rows use space/civ/unit/index/at/base_hex/mod_hex/"
             "official_changed, not layer/key/field/from/to/status")
        status = "conflict" if e.get("official_changed") else "carry"
        rows.append({"layer": e.get("space"),
                     "key": e.get("key") or e.get("unit") or e.get("index"),
                     "field": e.get("field"),
                     "from": _hexval(e.get("base_hex")),
                     "to": _hexval(e.get("mod_hex")),
                     "status": status})
    return rows


def _conflict_rows(rep):
    rows = []
    for c in rep.get("conflicts") or ():
        if not isinstance(c, dict):
            rows.append(c)
            continue
        if "layer" in c:
            rows.append(c)
            continue
        note("conflict-vocab",
             "analyze() conflict rows use space/civ/unit/index/base_was/"
             "official_now/mod_wants, not layer/key/field/base/mod/new")
        rows.append({"layer": c.get("space"),
                     "key": c.get("key") or c.get("unit") or c.get("index"),
                     "field": c.get("field"),
                     "base": _hexval(c.get("base_was")),
                     "mod": _hexval(c.get("mod_wants")),
                     "new": _hexval(c.get("official_now"))})
    return rows


def _strategy(rep):
    """`"field"` or `"records"` -- which of the two engines did the work.

    The documented word when the engine says it; otherwise derived from what the
    report actually contains, because a report that lists added or removed
    records HAS to be a records merge no matter what it calls itself.
    """
    s = rep.get("strategy")
    if s in ("field", "records"):
        return s
    if rep.get("structural"):
        return "records"
    added = rep.get("added") or {}
    removed = rep.get("removed") or {}
    counts = rep.get("counts") or {}
    if any(added.get(k) for k in ("units", "techs")) \
            or any(removed.get(k) for k in ("units", "techs")) \
            or counts.get("units_replaced"):
        return "records"
    return "field"


def _verdict(rep):
    return rep.get("verdict")


def _refused(rep):
    """Did this report refuse to merge?"""
    if rep.get("ok") is False:
        return True
    return _verdict(rep) == "impossible"


def _message(rep):
    """Everything the report says in words, for a version-mismatch assertion."""
    bits = []
    for key in ("message", "error", "why", "reason"):
        if rep.get(key):
            bits.append(str(rep[key]))
    for key in ("notes", "warnings"):
        v = rep.get(key)
        if isinstance(v, (list, tuple)):
            bits.extend(str(x) for x in v)
        elif v:
            bits.append(str(v))
    if not bits:
        bits.append(json.dumps(rep, ensure_ascii=False, default=str)[:2000])
    return " | ".join(bits)


def _explain(name, exc, UP, mod_p, base_p, new_p, keep):
    """Make a failed `upgrade()` say WHY, in the engine's own words.

    `UpgradeError` is raised bare -- it carries no payload -- so the only way to
    learn what its self-check objected to is to ask again with `force=True`,
    which returns the report instead of raising.  That report holds the verify
    block (which record it believes is missing or extra) and the records block
    (which of its own walks it distrusted).  Without this the probe can print
    only "upgrade() raised", which is not a bug report.
    """
    if exc is None:
        return
    spare = tempfile.mkdtemp(prefix="explain_%s_" % (name,), dir=keep)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rep = UP.upgrade(mod_dat=mod_p, out_dir=spare, title="explain",
                             base_dat=base_p, new_dat=new_p, install=False,
                             official_wins=False, force=True)
    except Exception as exc2:
        note("explain-" + name, "force=True also raised %s: %s"
             % (type(exc2).__name__, str(exc2)[:200]))
        return
    finally:
        shutil.rmtree(spare, ignore_errors=True)
    if not isinstance(rep, dict):
        return
    v = rep.get("verify")
    if isinstance(v, dict):
        for key in ("units_missing", "units_extra", "added_bad", "stray_count",
                    "civs", "written_bytes"):
            if v.get(key):
                note("verify-" + key,
                     ("engine self-check %s = %r" % (key, v[key]))[:340])
    r = rep.get("records")
    if isinstance(r, dict):
        for row in (r.get("refused") or ())[:2]:
            if isinstance(row, dict) and row.get("why"):
                note("refused-" + row["why"][:40],
                     ("engine refused the structural edit: " + row["why"])[:300])


def _out_of(got):
    """`(mod_dir, dat_path)` from either return shape."""
    out = got.get("out") or {}
    if not isinstance(out, dict):
        out = {}
    return (got.get("mod_dir") or out.get("mod_dir"),
            got.get("dat_path") or out.get("dat"))


# ---------------------------------------------------------------------------
# reading the produced file
# ---------------------------------------------------------------------------
class Merged(object):
    """One inflated merged .dat, with the walks the checks need, done lazily.

    Both walks here are expensive on 93 MB (`locate` ~10 s, `techfields.scan`
    ~9.5 s) and neither is needed by every case, so neither runs until a check
    asks.  A case that only compares bytes pays nothing.
    """

    def __init__(self, path):
        self.path = path
        self.raw, how = P.load_dat(path)
        self.how = how
        self._loc = None
        self._techs = None

    def located(self):
        if self._loc is None:
            p = P.Parser(self.raw)
            with contextlib.redirect_stdout(io.StringIO()):
                p.parse()
            self._loc = L.locate(self.raw, p)
        return self._loc

    def techs(self):
        if self._techs is None:
            with contextlib.redirect_stdout(io.StringIO()):
                self._techs = TF.scan(self.raw, self.gv, light=True)[0]
        return self._techs

    @property
    def gv(self):
        return self.located()[2]

    @property
    def civs(self):
        return self.located()[0]


def _unit_values(merged, unit_id, field=None, civ=None):
    """`[(civ_index, value)]` for every record of `unit_id` (or one civ).

    `field=None` asks only whether the record is there, and skips the field walk
    -- a presence check has no business paying for a 136 k-record scan.
    """
    out = []
    for c in merged.civs:
        if civ is not None and c["index"] != civ:
            continue
        for u in c["units"]:
            if u["id"] != unit_id:
                continue
            if field is None:
                out.append((c["index"], None))
                continue
            f = UF.fields_at(merged.raw, merged.gv, u["_start"])
            out.append((c["index"], _field(f, field)))
    return out


# ---------------------------------------------------------------------------
# the checks in `expect.json`
# ---------------------------------------------------------------------------
def run_check(chk, merged, rep, sources):
    """Apply one `expect.json` check.  Returns True/False, prints the detail."""
    kind = chk["kind"]

    if kind == "identical_to":
        which = chk["which"]
        want = sources[which]
        if merged is None:
            return check(False, "merged == %s (after inflate)" % (which,),
                         "no merged file was produced")
        same = merged.raw == want
        return check(same, "merged == %s (after inflate)" % (which,),
                     "" if same else "sizes %d vs %d" % (len(merged.raw), len(want)))

    if kind == "conflicts":
        if rep is None:
            return check(False, "analyze() reports conflicts", "no report")
        got = _conflict_rows(rep)
        # Counted per logical field, not per civ record.  The engine emits one row
        # per civ -- editing unit 83 in 63 civilizations is 63 rows -- because a
        # row is a byte range it has to write.  The question `expect.json` asks is
        # "how many distinct things do the author and the patch disagree about",
        # and that answer is the deduplicated count.  Both numbers go in the
        # label so neither reading is hidden.
        seen = []
        for c in got:
            k = (c.get("layer"), c.get("key"), c.get("field"))
            if k not in seen:
                seen.append(k)
        n, raw = len(seen), len(got)
        label = "analyze() reports %d conflict(s)" % (chk["count"],)
        if raw != n:
            label += " [%d row(s) / %d field(s)]" % (raw, n)
        return check(n == chk["count"], label,
                     "" if n == chk["count"] else
                     "got %d field(s) over %d row(s): %r" % (n, raw, seen[:6]))

    if kind == "unit_field":
        if merged is None:
            return check(False, "unit %d %s" % (chk["unit"], chk["field"]),
                         "no merged file was produced")
        uid = chk["unit"]
        civ = chk.get("civ")
        vals = _unit_values(merged, uid, chk["field"],
                            None if chk.get("civ_any") else civ)
        label = "unit %d %s = %r%s" % (uid, chk["field"], chk["value"],
                                       " (every civ)" if chk.get("civ_any")
                                       else ("" if civ is None else " (civ %d)" % (civ,)))
        if not vals:
            return check(False, label, "unit %d is not in the merged file at all"
                         % (uid,))
        got = sorted({v for _ci, v in vals})
        if chk.get("civ_any"):
            ok = got == [chk["value"]]
        else:
            ok = all(v == chk["value"] for _ci, v in vals)
        return check(ok, label, "" if ok else "got %r across %d record(s)"
                     % (got, len(vals)))

    if kind == "tech_field":
        if merged is None:
            return check(False, "tech %d %s" % (chk["index"], chk["field"]),
                         "no merged file was produced")
        techs = merged.techs()
        idx = chk["index"]
        label = "tech %d %s = %r" % (idx, chk["field"], chk["value"])
        if idx >= len(techs):
            return check(False, label, "the merged file has only %d techs"
                         % (len(techs),))
        f = TF.fields_at(merged.raw, merged.gv, techs[idx]["start"])
        try:
            got = _field(f, chk["field"])
        except KeyError as exc:
            return check(False, label, exc)
        return check(got == chk["value"], label,
                     "" if got == chk["value"] else "got %r" % (got,))

    if kind == "tech_count":
        if merged is None:
            return check(False, "merged file tech count", "no merged file")
        techs = merged.techs()
        return check(len(techs) == chk["count"],
                     "merged file has %d techs" % (chk["count"],),
                     "" if len(techs) == chk["count"] else "got %d" % (len(techs),))

    if kind in ("present", "absent"):
        if merged is None:
            return check(False, "%s %s" % (kind, chk.get("kind_detail")),
                         "no merged file was produced")
        want = kind == "present"
        if chk["kind_detail"] == "unit":
            uid, civ = chk["unit"], chk.get("civ")
            vals = _unit_values(merged, uid, None, civ)
            ok = bool(vals) == want
            return check(ok, "unit %d %s%s" % (uid, "present" if want else "absent",
                                               "" if civ is None
                                               else " in civ %d" % (civ,)),
                         "" if ok else "found in civs %r" % ([c for c, _v in vals],))
        idx = chk["index"]
        techs = merged.techs()
        ok = (idx < len(techs)) == want
        return check(ok, "tech #%d %s" % (idx, "present" if want else "absent"),
                     "the file has %d techs" % (len(techs),))

    if kind == "refuse_message":
        if rep is None:
            return check(False, "the refusal names the version", "no report")
        msg = _message(rep)
        words = chk.get("contains_any") or []
        ok = any(w in msg for w in words)
        return check(ok, "the refusal names the version (%s)" % ("|".join(words),),
                     msg[:200] if not ok else "")

    return check(False, "unknown check kind %r" % (kind,),
                 "expect.json and this probe disagree about the vocabulary")


# ---------------------------------------------------------------------------
# one case
# ---------------------------------------------------------------------------
def run_case(name, UP, keep):
    case_dir = os.path.join(ROOT, name)
    with open(os.path.join(case_dir, "expect.json"), "r", encoding="utf-8") as fh:
        exp = json.load(fh)
    base_p = os.path.join(case_dir, "base", DAT_REL)
    mod_p = os.path.join(case_dir, "mod", DAT_REL)
    new_p = os.path.join(case_dir, "new", DAT_REL)
    print("--- %s  (%s)" % (name, exp["mode"]))

    before = {p: _sha_file(p) for p in (base_p, mod_p, new_p)}
    out_dir = tempfile.mkdtemp(prefix="upgrade_%s_" % (name,), dir=keep)
    try:
        # The engine prints its own stage banners; the probe's output contract is
        # PASS/FAIL lines, so anything it says is captured and only shown when a
        # case fails.
        chatter = io.StringIO()
        with contextlib.redirect_stdout(chatter):
            try:
                rep = UP.analyze(mod_dat=mod_p, base_dat=base_p, new_dat=new_p)
            except Exception as exc:
                rep = {"ok": False, "raised": "%s: %s" % (type(exc).__name__, exc),
                       "message": str(exc)}
        if rep.get("raised") and exp["mode"] != "refuse":
            check(False, "analyze() did not raise", rep["raised"])

        if not isinstance(rep, dict):
            return check(False, "analyze() returned a dict", type(rep))

        if exp["mode"] == "refuse":
            # A refusal and a crash both stop the merge, and only one of them is
            # the answer.  The engine is supposed to notice the generation
            # mismatch and say so; if it instead walks a 7.8 header over an 8.9
            # body, the parser dies inside it and what comes back is a
            # struct.error.  That is a different bug from "merged the wrong
            # thing", so it gets its own line instead of hiding inside the
            # message assertion.
            words = ("7.8", "8.9", "VER")
            crashed = bool(rep.get("raised")) and not any(
                w in _message(rep) for w in words)
            if crashed:
                check(False, "analyze() refuses this file instead of dying on it",
                      rep["raised"])
            ok = _refused(rep)
            check(ok, "analyze() refused the cross-generation file",
                  "" if ok else "verdict=%r ok=%r" % (_verdict(rep), rep.get("ok")))
            for chk in exp["checks"]:
                run_check(chk, None, rep, {})
            return

        if rep.get("raised"):
            for chk in exp["checks"]:
                if chk["kind"] == "conflicts":
                    run_check(chk, None, rep, {})
            return

        # A report with holes is a shape this probe cannot judge; the engine is
        # still being written at that point, so say which key and leave rc=2
        # rather than fail ten cases for one missing field.
        for key in ("edits", "conflicts"):
            if key not in rep:
                skip("analyze()['%s']" % (key,))
        if not check(isinstance(rep.get("edits"), list), "edits is a list",
                     type(rep.get("edits"))):
            return
        check(rep.get("ok") is not False, "analyze() says ok",
              "" if rep.get("ok") is not False else repr(rep.get("ok")))

        st = _strategy(rep)
        want = exp.get("strategy")
        want = want if isinstance(want, list) else ([want] if want else [])
        check(not want or st in want, "strategy is %s" % ("|".join(map(str, want)),),
              "got %r" % (st,))

        # Half of the contract is "the merge is reported": an edit the engine
        # applied but did not list cannot be reviewed, undone, or trusted.
        rows = _edit_rows(rep)
        for e in rows:
            if not isinstance(e, dict):
                check(False, "every edit is a dict", type(e))
                break
            miss = [k for k in ("layer", "key", "field", "from", "to", "status")
                    if k not in e]
            if miss:
                check(False, "every edit carries layer/key/field/from/to/status",
                      miss)
                break
            if e["status"] not in ("carry", "conflict", "follow", "drop"):
                check(False, "every edit status is one of the four",
                      repr(e["status"]))
                break
        else:
            check(True, "edit records carry the documented keys")
        for c in _conflict_rows(rep):
            if not isinstance(c, dict):
                continue
            miss = [k for k in ("layer", "key", "field", "base", "mod", "new")
                    if k not in c]
            if miss:
                check(False, "every conflict carries base/mod/new", miss)
                break
        else:
            check(True, "conflict records carry base/mod/new")

        # Read-only: analyze() may not rewrite the three files it was given.
        after = {p: _sha_file(p) for p in before}
        check(after == before, "analyze() left the fixture bytes untouched",
              "" if after == before else
              [os.path.basename(os.path.dirname(p)) for p, h in before.items()
               if after[p] != h])

        if _refused(rep):
            check(False, "the merge was possible", _message(rep)[:300])
            for chk in exp["checks"]:
                if chk["kind"] == "conflicts":
                    run_check(chk, None, rep, {})
            return

        with contextlib.redirect_stdout(chatter):
            try:
                # official_wins=False on purpose: this suite is about the
                # author's edits surviving the patch.  Which value wins a
                # genuine conflict is the UI's call, and since m23827 the
                # engine defaults to the official one.
                got = UP.upgrade(mod_dat=mod_p, out_dir=out_dir, title="fixture",
                                 base_dat=base_p, new_dat=new_p, install=False,
                                 official_wins=False)
            except Exception as exc:
                got = {"ok": False, "raised": "%s: %s" % (type(exc).__name__, exc),
                       "message": str(exc), "exc": exc}
        if got.get("raised"):
            check(False, "upgrade() wrote the merged mod", got["raised"])
            _explain(name, got.get("exc"), UP, mod_p, base_p, new_p, keep)
            return
        if not isinstance(got, dict):
            return check(False, "upgrade() returned a dict", type(got))
        check(got.get("ok") is not False, "upgrade() says ok",
              "" if got.get("ok") is not False else repr(got.get("ok")))
        check(not got.get("installed"), "install=False installed nothing",
              repr(got.get("installed")))
        mod_dir, dat_path = _out_of(got)
        if not dat_path:
            return check(False, "upgrade() says where the .dat went", sorted(got))
        if not os.path.isfile(dat_path):
            return check(False, "the produced .dat is there", dat_path)
        check(bool(mod_dir) and os.path.isdir(mod_dir), "the mod folder is there",
              mod_dir)

        merged = Merged(dat_path)
        sources = {"base": _inflated(base_p), "mod": _inflated(mod_p),
                   "new": _inflated(new_p)}
        for chk in exp["checks"]:
            run_check(chk, merged, rep, sources)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def _engine():
    """Import the engine and prove the two entry points are callable."""
    try:
        import aoe2mod.mod.upgrade as UP
    except Exception as exc:
        print("  (import aoe2mod.mod.upgrade failed: %s: %s)"
              % (type(exc).__name__, exc))
        skip("module aoe2mod.mod.upgrade")
    for name in ("analyze", "upgrade"):
        if not callable(getattr(UP, name, None)):
            skip(name)
    try:
        params = inspect.signature(UP.upgrade).parameters
    except (TypeError, ValueError):
        params = {}
    need = [p for p in ("mod_dat", "base_dat", "new_dat", "out_dir", "install")
            if params and p not in params]
    if need:
        skip("upgrade(%s)" % (", ".join(need),))
    try:
        aparams = inspect.signature(UP.analyze).parameters
    except (TypeError, ValueError):
        aparams = {}
    need = [p for p in ("mod_dat", "base_dat", "new_dat")
            if aparams and p not in aparams]
    if need:
        skip("analyze(%s)" % (", ".join(need),))
    return UP


def main(argv):
    global VERBOSE
    VERBOSE = "-v" in argv or "--verbose" in argv
    only = []
    args = argv[1:]
    for i, a in enumerate(args):
        if a == "--only" and i + 1 < len(args):
            only.append(args[i + 1])
        elif a.startswith("--only="):
            only.append(a.split("=", 1)[1])

    if not os.path.isdir(ROOT):
        print("FAIL: the fixture corpus is not there: %s" % (ROOT,))
        print("      build it first: python -X utf8 _probe/make_upgrade_fixtures.py")
        print("FAIL")
        return 1
    names = [n for n in ORDER if os.path.isdir(os.path.join(ROOT, n))]
    names += sorted(set(d for d in os.listdir(ROOT)
                        if os.path.isfile(os.path.join(ROOT, d, "expect.json")))
                    - set(names))
    if only:
        names = [n for n in names if n in only]
    if not names:
        print("FAIL: no case directories under %s" % (ROOT,))
        print("FAIL")
        return 1

    UP = _engine()
    print("upgrade engine: %s" % (getattr(UP, "__file__", "?"),))
    print("%d case(s) under %s\n" % (len(names), ROOT))

    keep = tempfile.mkdtemp(prefix="upgrade_out_")
    try:
        for name in names:
            n_fails = len(FAILS)
            try:
                run_case(name, UP, keep)
            except SystemExit:
                raise
            except Exception as exc:
                import traceback
                traceback.print_exc()
                check(False, "%s raised instead of reporting" % (name,),
                      "%s: %s" % (type(exc).__name__, exc))
            if len(FAILS) == n_fails:
                print("PASS %s" % (name,))
            else:
                print("FAIL %s: %s" % (name, "; ".join(FAILS[n_fails:])))
            sys.stdout.flush()
    finally:
        shutil.rmtree(keep, ignore_errors=True)

    print()
    if FAILS:
        print("UPGRADE: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        print("FAIL")
        return 1
    if NOTES:
        print("UPGRADE: %d NOTE(S) -> %s" % (len(NOTES), NOTES))
    print("UPGRADE: THE MOD'S EDITS SURVIVED THE PATCH, EVERY CASE")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
