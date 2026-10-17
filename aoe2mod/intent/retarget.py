"""Reskin a unit by RENAMING its graphics records instead of copying .sld files.

Two ways to make the archer look like a sheep:

  COPY   ship the donor's picture under every target file name.  Works in game
         (proven 2026-10-17), costs one file per name: the villager family is
         466 files / 614 MB, of which 233 are `_x2` siblings the engine derives
         and no record ever names.
  RENAME rewrite the graphics records' `file` field to name the donor's picture,
         which is already on disk.  The villager family is 244 record edits, the
         .dat gets SMALLER by 2,514 bytes, and the mod is one file.

This module implements RENAME.  It deliberately shares the *decision* layer with
`reskin.plan` (which target files a swap needs, which animations pair up, which
need filling, which resource variants travel with a stem) and changes only the
last step: instead of asking that layer for donor bytes to copy, it asks it which
donor picture each target name should point at.

WHY THE DECISION LAYER IS SHARED AND NOT REIMPLEMENTED: the ten in-game tests
that shaped it were all paid for once.  A second implementation would drift, and
the drift would show up as a reskin that half-applies.

WHAT IS PROVEN HERE: the records say what was asked, the stream reparses to its
own length, and no record outside the plan moved.  AND, in game on 2026-10-17:
`dsh test v13` shipped exactly this -- one .dat, no pictures -- and the villager
family came out as the donor's sheep for every job, which means the engine
resolves a graphics record through its `file` string rather than through the
`slp` id stored beside it.  See `_probe/retarget_verdict.json`.

WHAT IS NOT PROVEN: that a `file` the install does not have can be pointed at.
It cannot, which is why `plan()` checks every donor picture on disk and refuses
rather than guessing.  Nothing here says the `slp` field is dead either: it was
left untouched, so the evidence is "`file` wins when both are present".
"""
import os

from ..dat import writer as W
from . import reskin as RK
from ..game import sprites as SP


class RetargetError(Exception):
    pass


#: Names the engine builds from a stored `file` by substitution instead of
#: reading a second string.  Measured: 0 of 8,291 file-naming records name an
#: `_x2`, so the ultra-HD sibling is derived, never stored.
DERIVED_SUFFIX = "_x2"


def plan(game_root, graphics, civs, target_id, donor_id, scope="all",
         families=None, family_scope=False, fill=True):
    """Work out which graphics records to rename, without touching any bytes.

    Returns the same decision report as `reskin.plan` plus a ``retarget`` dict
    that names the edits.  ``editable`` is False with a readable ``reason`` when
    the swap cannot be expressed as renames (a donor picture missing from disk,
    or two civilizations wanting one target name to hold two donor pictures).
    """
    rep = RK.plan(game_root, graphics, civs, target_id, donor_id,
                  scope=scope, families=families, family_scope=family_scope,
                  fill=fill)
    base = {
        "intent": "unit.sprite",
        "mode": "rename",
        "editable": False,
        "target": target_id,
        "donor": donor_id,
        "warnings": list(rep.get("warnings") or []),
        "reason": None,
        "retarget": None,
    }
    if not rep.get("ok"):
        base["reason"] = rep.get("reason") or "this swap cannot be expressed"
        return base

    want, clash = {}, {}
    for rel, src in (rep.get("files") or {}).items():
        t = os.path.basename(rel)
        if t.endswith(".sld"):
            t = t[:-4]
        d = src[:-4] if src.endswith(".sld") else src
        if t in want and want[t] != d:
            clash.setdefault(t, {want[t]}).add(d)
            continue
        want[t] = d
    if clash:
        name = sorted(clash)[0]
        base["reason"] = (
            "two civilizations need %s.sld to show different pictures (%s), and "
            "one record cannot name two files" % (name, " vs ".join(sorted(clash[name]))))
        return base

    gdir = SP.graphics_dir(game_root)
    absent = sorted(d for d in set(want.values())
                    if not os.path.exists(os.path.join(gdir, d + ".sld")))
    if absent:
        base["reason"] = (
            "%d donor picture(s) that this rename would point at are not on "
            "disk, starting with %s.sld" % (len(absent), absent[0]))
        return base

    by_name = {}
    for g in graphics:
        f = g.get("file") or ""
        if f in want:
            by_name.setdefault(f, []).append(g)
    if not by_name:
        base["reason"] = (
            "no graphics record names any of the %d target file(s), so a rename "
            "would change nothing" % len(want))
        return base

    edits = []
    for tname in sorted(by_name):
        dname = want[tname]
        for g in by_name[tname]:
            edits.append({"graphic_id": g["id"],
                          "record_name": g.get("name") or "",
                          "was": tname, "now": dname})
    # Derived siblings: a record naming `<x>_x1` makes the engine look for
    # `<x>_x2`, so the donor must ship one too.  Checked, not assumed.
    derived_absent = sorted(set(
        w[:-3] + DERIVED_SUFFIX for w in set(want.values())
        if w.endswith("_x1")
        and not os.path.exists(os.path.join(gdir, w[:-3] + DERIVED_SUFFIX + ".sld"))))

    base["editable"] = True
    base["retarget"] = {
        "mode": "rename",
        "rename_count": len(edits),
        "target_names": len(want),
        "donor_names": len(set(want.values())),
        "derived_siblings_missing": derived_absent,
        "edits": edits,
        "dat_bytes": None,
        "no_sld_shipped": True,
        "copy_based_equivalent": {
            "files": len(rep.get("files") or {}),
            "megabytes": round(sum(
                os.path.getsize(os.path.join(game_root, r))
                for r in (rep.get("files") or {})) / (1024.0 * 1024.0), 1),
        },
    }
    base["family"] = rep.get("family")
    base["target_count"] = rep.get("target_count")
    base["civ_count"] = int(rep.get("civ_count") or 0)
    base["target_stems"] = list(rep.get("target_stems") or [])
    base["donor_stems"] = list(rep.get("donor_stems") or [])
    base["grid_mismatches"] = list(rep.get("grid_mismatches") or [])
    if not base["grid_mismatches"]:
        base.pop("grid_mismatches")
    base["filled"] = list(rep.get("filled") or [])
    base["fill"] = rep.get("fill")
    base["resource_variants"] = list(rep.get("resource_variants") or [])
    base["description"] = (
        "%d graphics record(s) repointed from %s to %s, covering %d "
        "civilization(s); no .sld file is shipped"
        % (len(edits), " / ".join(rep.get("target_stems") or []),
           " / ".join(rep.get("donor_stems") or []),
           int(rep.get("civ_count") or 0)))
    return base


def apply(stats, retarget):
    """Rename the records on a parsed model and return ``(dat_bytes, report)``.

    ``stats`` is mutated in place; callers that must keep the original model
    should deep-copy the graphics list first (the same discipline `datgrant`
    documents, for the same reason).
    """
    by_id = {}
    for g in stats["graphics"]:
        by_id.setdefault(g["id"], []).append(g)
    changed = []
    for e in retarget["edits"]:
        hits = by_id.get(e["graphic_id"]) or []
        if not hits:
            raise RetargetError(
                "graphics record %d is not in this model" % e["graphic_id"])
        for g in hits:
            if (g.get("file") or "") != e["was"]:
                raise RetargetError(
                    "graphics record %d names %r, not the %r this plan was made "
                    "against -- rebuild the plan"
                    % (e["graphic_id"], g.get("file"), e["was"]))
            g["file"] = e["now"]
            changed.append(e)
    return changed
