# -*- coding: utf-8 -*-
r"""sprites.py -- which .sld files draw a unit or building.

THE CHAIN (measured, not assumed)

    unit record -> standing_graphic[0] -> graphics[id] -> `file` + ".sld"
                                        -> resources/_common/drs/graphics/

`standing_graphic[0]` indexes the graphics array BY THE RECORD'S OWN `id`
FIELD, not by array position: 2,271 of 2,528 units land on a real .sld that
way, against 1,458 by position.  That 32-point gap is the whole reason this
field had to be recovered from the parser rather than guessed at.

ONE ANIMATION IS NOT ONE FILE

A unit walks, attacks and dies with different art, and those are SEPARATE
graphics records -- `u_arc_archer_{attackA,deathA,decayA,idleA,walkA}_x1` are
five records.  They are NOT at a fixed offset from the standing one, and the
unit record does not name them (`Unit.h` carries only StandingGraphic,
DyingGraphic and UndeadGraphic).  The engine groups them by the record's own
`name` field:

    u_arc_archer_attackA_x1   name = "Archer (Attack)"
    u_arc_archer_idleA_x1     name = "Archer (Idle)"
    -> the group is the name with its parenthesised suffix removed: "Archer"

So `files_of` groups by that stem.  What looks like the obvious alternative --
"every .sld whose filename starts with the standing file minus its last token"
-- is REFUTED, and the counter-example is worth keeping in view:

    prefix rule : unit 15 (Junk) -> u_shp_{canoe,caravel,dreki,dromon,junk}
    name rule   : unit 15 (Junk) -> u_shp_junk_x1

`u_shp_canoe_x1` (51,540 B), `u_shp_caravel_x1` (243,180 B) and
`u_shp_junk_x1` (85,988 B) are three different units' art with different bytes;
merging them is not a naming quirk, it is a wrong answer.  The prefix rule also
merges 7,743 base names that nest (`b_misc_waypoint_flag` would swallow all 57
civilization flags).

WHAT A SWAP MOVES

A reskin copies the donor's files over the target's, matched by ANIMATION
(`walk` -> `walk`), where the animation name comes from the graphics record's own
`name` field -- the engine's label -- rather than from the filename suffix.  The
filenames are not consistent: the Bowman's walk file is `u_arc_bowman_walk_x1`
and the Longbowman's is `u_arc_longbowman_walkA_x1`, and keying on the suffix
made those two look like they had no animation in common.  See `anim_of`.
Animations the donor does not have are reported, never silently dropped: the
target keeps its original art for those, which is a visible difference (a unit
that attacks with a different sprite than it walks with) and the caller has to be
able to say so.

HONESTY BOUNDARY

Proven: the chain resolves, by-id beats by-position, the group rule reproduces
the engine's own names, and every file is present on disk paired x1/x2.
NOT proven: that overwriting these files changes what the running game draws.
That needs an in-game test, the same one every other layer in this toolkit is
waiting on.  Nothing here claims the game re-reads a loose .sld.
"""
import collections
import os
import re

GRAPHICS_DIR_REL = ("resources", "_common", "drs", "graphics")

#: The only two animations whose art depends on WHAT is being carried, so the only
#: two a resource-variant stem may own.  A stem outside this set that merely looks
#: like a sibling (a snow variant, a damage state, a gate part) is not one.
_RESOURCE_ANIMS = frozenset(("carry", "work"))


class SpriteError(Exception):
    """Raised when a sprite question cannot be answered from the data."""


def graphics_dir(game_root):
    return os.path.join(game_root, *GRAPHICS_DIR_REL)


def disk_files(game_root):
    """The .sld basenames actually shipped, without the extension."""
    d = graphics_dir(game_root)
    if not os.path.isdir(d):
        raise SpriteError("no sprite directory at %s" % d)
    return set(fn[:-4] for fn in os.listdir(d) if fn.endswith(".sld"))


def _text(rec, key):
    if not isinstance(rec, dict):
        return None
    v = rec.get(key)
    if not isinstance(v, str):
        return None
    v = v.strip()
    return v if v and v != "None" else None


def stem_of_name(name):
    """'Archer (Attack)' -> 'Archer';  'JUNKX_FN' -> 'JUNKX_FN'."""
    if not name:
        return None
    i = name.find(" (")
    s = (name[:i] if i > 0 else name).strip()
    return s or None


def token_of(name):
    """The filename animation token: 'u_arc_archer_walkA' -> 'walkA'.

    Only meaningful for names that end in `_x1`, which is how the shipped files
    are named; anything else returns None rather than a fabricated token.

    This is NOT the key a swap should match on -- see `anim_of`.
    """
    if not name:
        return None
    if name.endswith("_x1"):
        name = name[:-3]
    elif name.endswith("_x2"):
        name = name[:-3]
    else:
        return None
    return name.rpartition("_")[2] or None


_PAREN = re.compile(r"\(([^)]*)\)\s*$")


def anim_keys(filename, record_names):
    """Every animation a file serves, per the records that point at it.

    A file can serve more than one: the engine labels one sheep file both
    `Sheep (Attack)` and `Sheep (Idle)`.  Returning the SET rather than one name
    is what keeps the second label from being lost depending on record order.
    """
    keys = set()
    for n in record_names or ():
        k = anim_of(filename, n)
        if k:
            keys.add(k)
    if not keys:
        k = token_of(filename)
        if k:
            keys.add(k)
    return keys


def anim_label(filename, record_name=None):
    """The engine's spelling of this animation, for user-visible text.

    `anim_of` lowercases so that records disagreeing only in case still match;
    this keeps what the record actually says, so a warning reads "IdleC" (the
    game's word) instead of the lowercased key that exists only to be compared.
    """
    if record_name:
        m = _PAREN.search(record_name)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return token_of(filename) or ""


def anim_of(name, record_name=None):
    """What the ENGINE calls this animation -- 'Archer (Walk)' -> 'walk'.

    The filename token is a naming CONVENTION and it is not stable across
    entities that plainly share an animation.  The Bowman's walk file is
    `u_arc_bowman_walk_x1` while the Longbowman's is `u_arc_longbowman_walkA_x1`,
    so keying on the filename reported the Bowman as having no `walk` when the
    Longbowman was the donor -- and it said exactly that for the six Chronicles
    civilizations (whose archer is the Bowman) on the first end-to-end reskin,
    inventing a warning that three of the unit's animations would not be
    replaced when all of them would be.

    The graphics record's own `name` field says `Bowman (Walk)` and
    `Longbowman (Walk)`: the same word, because that field is the engine's
    animation label rather than a filename suffix.  It is the better key, and it
    is the engine's own vocabulary rather than an inference from spelling.

    Falls back to the filename token when the record carries no parenthesised
    label -- buildings, mines and other single-animation art are named without
    one (`Barracks DARK Age1`, `GoldMine`).
    """
    if record_name:
        m = _PAREN.search(record_name)
        if m and m.group(1).strip():
            return m.group(1).strip().lower()
    return token_of(name)


class SpriteIndex(object):
    """Answers 'which .sld files draw this entity' for one game install."""

    def __init__(self, graphics, files):
        self.graphics = graphics or []
        self.files = set(files or ())
        self._by_id = {}
        for g in self.graphics:
            if isinstance(g, dict) and g.get("id") is not None:
                self._by_id.setdefault(g["id"], g)
        self._stem_files = collections.defaultdict(list)
        self._stem_names = collections.defaultdict(set)
        # (stem, file) -> every raw record name that points at that file.  A file
        # can serve SEVERAL animations: the engine names one sheep file both
        # `Sheep (Attack)` and `Sheep (Idle)`.  Looking up a single name per file
        # and taking whichever record came first made the sheep's idle file
        # register as an ATTACK, which then made the sheep look like a donor with
        # no idle animation at all.
        self._file_labels = collections.defaultdict(set)
        # file -> every (frame_count, angle_count) that ANY record claims for it.
        # The grid is normally a property of the file (7,602 of 7,618 shipped
        # .sld files have all their claimants agreeing), but 16 do not -- the
        # ibex's idle art is claimed as both (30, 16) and (60, 16) -- so the
        # disagreement is recorded and reported rather than resolved by luck.
        self._file_grids = collections.defaultdict(set)
        # file -> every stem that names it.  One file can belong to two stems: the
        # stone miner's work file is literally the gold miner's work file, which
        # is the evidence that those two stems are the same entity in two states.
        self._file_stems = collections.defaultdict(set)
        for g in self.graphics:
            f, n = _text(g, "file"), _text(g, "name")
            if f:
                self._file_grids[f].add((g.get("frame_count"), g.get("angle_count")))
            if not f or not n:
                continue
            s = stem_of_name(n)
            if s:
                self._file_labels[(s, f)].add(n)
                self._file_stems[f].add(s)
                self._stem_files[s].append(f)
                self._stem_names[s].add(n)
        self._groups = {}
        for s, names in self._stem_files.items():
            have = sorted(set(n for n in names if n in self.files))
            if have:
                self._groups[s] = have

    # -- single records ------------------------------------------------------
    def record(self, gid):
        return self._by_id.get(gid)

    def file_of(self, gid):
        return _text(self.record(gid), "file")

    def name_of(self, gid):
        return _text(self.record(gid), "name")

    def stem_of(self, gid):
        return stem_of_name(self.name_of(gid))

    def group(self, stem):
        """The on-disk .sld names (no extension) the engine groups under `stem`."""
        return list(self._groups.get(stem, ()))

    def group_names(self, stem):
        return sorted(self._stem_names.get(stem, ()))

    def grid(self, file_name):
        """The ``(frame_count, angle_count)`` shipped records claim for a file.

        Returns a SET, because the grid is normally a property of the FILE but
        not always a promise: 16 of the 7,618 shipped ``.sld`` files are named by
        records that disagree (``a_hunt_ibex_idleA_x1`` is claimed as both
        ``(30, 16)`` and ``(60, 16)``).  A caller comparing two arts must report a
        disagreement rather than pick one, and an empty set means nothing shipped
        names this file at all.
        """
        return set(g for g in self._file_grids.get(file_name, ())
                   if g[0] is not None and g[1] is not None)

    def resource_variants(self, stem):
        """Orphan art stems that draw the SAME entity while it carries something else.

        A villager art set has a hidden companion.  ``GoldMiner Male`` has six
        files, but the shipped game also contains ``StoneMiner Male`` with just
        TWO -- one of which is literally one of ``GoldMiner Male``'s files.  The
        engine picks the second stem by the resource being carried and NO unit
        record names it, so walking ``standing_graphic`` alone never reaches it.

        That is not a guess: in game on 2026-10-17 ``dsh test v11`` replaced the
        whole villager family and every job came out a sheep EXCEPT the stone
        miner while carrying, which stayed a human -- exactly the two files this
        stem owns and the family does not.

        Returns ``[(variant_stem, [files only the variant names]), ...]``, the
        files being basenames without ``.sld``.  The rule is deliberately narrow,
        because looser ones match hundreds of unrelated pairs (snow variants,
        damage states, gate parts):

          1. the variant's animation labels are a PROPER SUBSET of `stem`'s
          2. the two share at least one file name
          3. their stem word bags differ by exactly one word on EACH side
          4. the variant's animations are all resource-dependent (carry/work)

        On the shipped install this matches exactly four pairs -- the stone and
        gold miner, in both the base and the Antiquity art sets -- and nothing
        else, which is what makes it safe to act on automatically.
        """
        out = []
        if not stem:
            return out
        mine = set(self._stem_files.get(stem) or ())
        if not mine:
            return out
        my_anims = self._anims_of(stem)
        if not my_anims:
            return out
        my_words = set(stem.lower().split())
        for f in mine:
            for other in sorted(self._file_stems.get(f, ())):
                if other == stem:
                    continue
                other_files = set(self._stem_files.get(other) or ())
                if not other_files:
                    continue
                other_anims = self._anims_of(other)
                if not other_anims or not (other_anims < my_anims):
                    continue
                if not other_anims <= _RESOURCE_ANIMS:
                    continue
                other_words = set(other.lower().split())
                if (len(other_words - my_words) != 1
                        or len(my_words - other_words) != 1):
                    continue
                extra = [n for n in sorted(other_files) if n not in mine]
                if not extra:
                    continue
                item = (other, extra)
                if item not in out:
                    out.append(item)
        return sorted(out)

    def _anims_of(self, stem):
        out = set()
        for f in self._stem_files.get(stem) or ():
            for nm in self._file_labels.get((stem, f)) or ():
                a = anim_of(f, nm)
                if a:
                    out.add(a)
        return out

    # -- per unit ------------------------------------------------------------
    def art(self, unit):
        """Describe the art of one unit record.

        Returns None when the record names no graphic at all, otherwise a dict
        whose `kind` says how far the chain resolved:

          none    -- the graphics record has no usable `file` string
          legacy  -- it names a file that is not shipped (pre-DE SLP naming,
                     e.g. file "W"); the art cannot be found by name
          loose   -- resolved to real .sld files; `files` holds their names
        """
        sg = unit.get("standing_graphic")
        if not sg:
            return None
        gid = sg[0]
        rec = self.record(gid)
        if rec is None:
            return {"kind": "missing", "graphic_id": gid, "files": [],
                    "reason": "no graphics record carries id %r" % (gid,)}
        f = self.file_of(gid)
        if not f:
            return {"kind": "none", "graphic_id": gid, "files": [],
                    "reason": "the graphics record has no file string"}
        stem = self.stem_of(gid)
        files = self.group(stem) if stem else []
        if (f not in self.files) and not files:
            return {"kind": "legacy", "graphic_id": gid, "file": f, "files": [],
                    "reason": "no shipped .sld is named %r" % (f + ".sld",)}
        # Key each file by the engine's own animation labels.  A file can serve
        # SEVERAL animations (the sheep's idle file carries both "Sheep (Attack)"
        # and "Sheep (Idle)"), so a file may legitimately appear under two keys.
        # Two files in ONE unit's art can still carry the same label (the hero
        # Themistocles ships an infantry `..._idle` and a naval `..._idleA`, both
        # named "Themistocles (Idle)"), and a dict would drop one silently.  The
        # first file in sorted order wins -- deterministically, so a plan is
        # reproducible -- and the drop is REPORTED rather than swallowed.
        tokens, labels, collisions = {}, {}, []
        for n in sorted(files):
            names = sorted(self._file_labels.get((stem, n)) or ())
            keys = anim_keys(n, names)
            if not keys:
                continue
            for k in sorted(keys):
                owner = tokens.get(k)
                if owner is not None and owner != n:
                    collisions.append({"animation": k, "kept": owner, "dropped": n})
                    continue
                # One file can serve several animations (the sheep's idle art is
                # also what the engine plays for its attack), so the same name may
                # legitimately appear under two keys.
                tokens[k] = n
            for nm in names:
                k = anim_of(n, nm)
                if k and k not in labels:
                    labels[k] = anim_label(n, nm)
            if keys and not any(k in labels for k in keys):
                labels[keys[0]] = anim_label(n, None)
        return {
            "kind": "loose",
            "graphic_id": gid,
            "file": f,
            "stem": stem,
            "name": self.name_of(gid),
            "files": files,
            # the second int16 of the pair is the unit's ALTERNATE IDLE: 13,092
            # of 13,470 set values point into the same group, 378 elsewhere.
            "alternate_idle": self.file_of(sg[1]) if len(sg) > 1 and sg[1] >= 0 else None,
            "tokens": tokens,
            # The engine's own spelling of each animation key, for anything the
            # user reads.  The KEY is lowercased so a labelled record ("Walk")
            # and an unlabelled one ("walkA") still match, but printing the key
            # would show "idlec" where the game says "IdleC".
            "token_labels": labels,
            "token_collisions": collisions,
            # animation key -> the grids its target file is claimed with, so a
            # swap can tell the caller when it is about to put a 60-frame idle
            # where a 45-frame one was.  Nothing here opens a file.
            "grids": dict((k, sorted(self.grid(n))) for k, n in tokens.items()),
            # Art this entity uses ONLY while carrying a particular resource.  No
            # unit record points at it, so it has to travel with the stem or it
            # stays human: the stone miner did exactly that in game on 2026-10-17.
            "resource_variants": self._variants_for(stem, tokens),
        }

    def _variants_for(self, stem, tokens):
        """Each resource variant as ``{stem, files: {animation: file}}``."""
        out = []
        for vstem, extra in self.resource_variants(stem):
            files = {}
            for f in extra:
                for nm in sorted(self._file_labels.get((vstem, f)) or ()):
                    a = anim_of(f, nm)
                    if a:
                        files[a] = f
            if files:
                out.append({"stem": vstem, "files": files})
        return out

    def units_sharing(self, unit_id, civs):
        """Every unit id whose art resolves to the same group as `unit_id`."""
        stem = None
        for c in civs:
            for u in c.get("units", ()):
                if u.get("id") == unit_id:
                    a = self.art(u)
                    if a and a.get("stem"):
                        stem = a["stem"]
                    break
            if stem:
                break
        if stem is None:
            return []
        out = set()
        for c in civs:
            for u in c.get("units", ()):
                a = self.art(u)
                if a and a.get("stem") == stem:
                    out.add(u["id"])
        return sorted(out)


def art_index(game_root, graphics):
    """Build a SpriteIndex for an installed game."""
    return SpriteIndex(graphics, disk_files(game_root))


# ---------------------------------------------------------------------------
# swapping
# ---------------------------------------------------------------------------

# -- filling a gap, when the donor simply does not have that animation -------
#
# A unit whose art changes with its JOB (a villager) needs its family rewritten,
# but no single entity in the game supplies all ten of those animations: `seed`
# exists on 4 unit ids, `task` on 6, `work` on 61, `carry` on 36.  So "make the
# villager look like a sheep" cannot be answered by copying alone -- five of the
# family's animations have no sheep picture to copy, and the engine then draws the
# villager's own human art the moment it starts chopping.  That is what happened
# in game on 2026-10-17.
#
# The answer is not to refuse and not to invent art: it is to let a NEARBY
# animation of the same donor stand in, chosen by what the animation is FOR and
# only when the two frame grids agree.  `carry` is a walk; `work` and `seed` are a
# repeated swing; `idlec` is an idle.  A substitution whose grid does not match is
# rejected, because that is the silent-garbage case this file exists to prevent.
FILL_PREFERENCE = {
    "idlec": ("idle", "attack", "walk", "death"),
    "carry": ("walk", "idle", "attack", "death"),
    "work": ("attack", "idle", "walk", "death"),
    "task": ("work", "attack", "idle", "walk", "death"),
    "seed": ("work", "attack", "walk", "idle", "death"),
    "move": ("walk", "idle"),
    "shift": ("walk", "idle"),
}
FILL_DEFAULT = ("idle", "walk", "attack", "decay", "death")


def _grid_fits(target_grid, donor_grid):
    """Whether a donor frame grid can stand in for a target one.

    Returns ``"exact"``, ``"truncated"`` or ``None``.

    The engine indexes a sprite as ``frame * angle_count + angle``, where the
    counts come from the graphics RECORD, not from the file.  So a donor with the
    same angle count and at least as many frames is structurally safe: the extra
    frames are simply never asked for, and the animation reads as a shorter
    version of the donor's.  A donor with FEWER frames is not safe, because the
    engine will ask for frame indices the file does not contain -- that is the
    garbage case, and it is why this is a rule about counts rather than taste.
    """
    tf, ta = target_grid
    df, da = donor_grid
    if ta != da:
        return None
    if df == tf:
        return "exact"
    if df > tf:
        return "truncated"
    return None


def fill_for(target, donor, token):
    """Which donor animation may stand in for a target animation it lacks.

    Returns ``(donor_token, grid, reason)`` or ``None``.

    Two passes.  The first looks for the animations that are the same KIND of
    movement (`carry` is a walk, `work` is a repeated swing, `idlec` is an idle)
    and accepts one whose grid fits exactly.  The second falls back to ANY donor
    animation whose grid fits, because when the donor simply has no comparable
    movement -- a sheep has no work animation at all -- the alternative to a
    stand-in is not the right frames, it is the WRONG SPECIES on screen.
    """
    dt = donor.get("tokens") or {}
    dg = donor.get("grids") or {}
    want = [tuple(g) for g in ((target.get("grids") or {}).get(token) or ())]
    if not want:
        return None

    def _try(cand, allow_truncated):
        for tg in want:
            for hg in (dg.get(cand) or ()):
                hg = tuple(hg)
                how = _grid_fits(tg, hg)
                if how is None or (how == "truncated" and not allow_truncated):
                    continue
                why = ("the donor has no %s animation, so its %s animation stands "
                       "in" % (token, cand))
                if how == "truncated":
                    why += (" (the stand-in has %d frames where %s has %d, so the "
                            "last %d are simply not played)"
                            % (hg[0], token, tg[0], hg[0] - tg[0]))
                return cand, hg, why
        return None

    for cand in FILL_PREFERENCE.get(token, FILL_DEFAULT):
        if cand in dt:
            got = _try(cand, allow_truncated=False)
            if got:
                return got
    for cand in sorted(dt):
        if cand == token:
            continue
        got = _try(cand, allow_truncated=True)
        if got:
            return got
    return None


def plan_swap(target, donor, fill=False):
    """Match a donor's art onto a target entity's, animation by animation.

    `target` and `donor` are the dicts `SpriteIndex.art` returns.

    Returns (pairs, unmapped, extra):

      pairs     [(target_sld, donor_sld)] -- copy donor over target
      unmapped  [(token, target_sld)]     -- the target has this animation and
                                             the donor does not, so the target
                                             keeps its own picture for it
      extra     [(token, donor_sld)]      -- the donor has an animation the
                                             target has nowhere to put

    Both leftovers are reported rather than dropped.  An unmapped animation is
    the failure the player will actually notice -- a unit that walks as one
    creature and attacks as another -- so it has to reach the caller.

    ``fill=True`` additionally pairs an unmapped animation with a NEARBY donor
    animation whose frame grid matches (see `fill_for`).  It is off by default
    because it is a judgement call, but it is the only way to reskin a unit whose
    art changes with its job: no entity in the game supplies all ten animations a
    villager's family needs, so without filling, the villager stays a human every
    time it works.  Substituted pairs appear in `pairs` and the animation they
    stand in for is absent from `unmapped`, so a caller can tell a copy from a
    stand-in by re-running with `fill=False`.
    """
    if not target or target.get("kind") != "loose":
        raise SpriteError(
            "the target has no loose art to replace (%s)"
            % (target.get("reason") if target else "no standing graphic"))
    if not donor or donor.get("kind") != "loose":
        raise SpriteError(
            "the donor has no loose art to copy (%s)"
            % (donor.get("reason") if donor else "no standing graphic"))

    dt = donor.get("tokens") or {}
    tt = target.get("tokens") or {}
    if not tt:
        raise SpriteError(
            "the target's art (%r) names no animation this toolkit can match, "
            "so there is nothing to replace"
            % (target.get("file") or target.get("stem"),))

    pairs, unmapped, filled = [], [], []
    for tk_, tn in sorted(tt.items()):
        if tk_ in dt:
            pairs.append((tn, dt[tk_]))
        elif fill:
            got = fill_for(target, donor, tk_)
            if got is None:
                unmapped.append((tk_, tn))
            else:
                cand, _grid, why = got
                pairs.append((tn, dt[cand]))
                filled.append({"animation": tk_, "source": cand,
                               "target": tn, "donor": dt[cand], "reason": why})
        else:
            unmapped.append((tk_, tn))
    extra = [(k, v) for k, v in sorted(dt.items()) if k not in tt]

    # An EMPTY pair list is not "nothing to do" -- it means these two entities
    # have no animation in common at all, so copying the donor would produce no
    # files while the caller reads an empty result as success.  That is
    # reachable, not theoretical: a Dark Age Barracks (`tokens={'age1'}`) has no
    # token in common with 2,260 of the 2,280 other loose arts, Feudal Age
    # Barracks (`age2`) among them.  A building's token is its AGE, so the
    # obvious "reskin the Barracks with the next age's Barracks" is exactly the
    # case that silently produced nothing.
    if not pairs:
        raise SpriteError(
            "these two have no animation in common: the target has %s and the "
            "donor has %s, so copying would change nothing"
            % (", ".join(sorted(tt)) or "none",
               ", ".join(sorted(dt)) or "none"))
    return pairs, unmapped, extra


def plan_swap_full(target, donor, fill=False):
    """`plan_swap`, plus the list of animations that were stood in for.

    Returns ``(pairs, unmapped, extra, filled)``.  Kept separate from
    `plan_swap` so the long-standing three-tuple contract -- which the reskin
    layer and several probes unpack -- does not grow a fourth element and start
    raising `ValueError` at every existing call site.
    """
    pairs, unmapped, extra = plan_swap(target, donor)
    if not fill:
        return pairs, unmapped, extra, []
    # Recompute with filling, then diff against the plain answer to name exactly
    # which animations were substituted.  Doing it this way keeps ONE
    # implementation of the matching rule; duplicating the loop here is how the
    # two answers would drift.
    pairs2, unmapped2, _e2 = plan_swap(target, donor, fill=True)
    filled = []
    base = dict((tn, dn) for tn, dn in pairs)
    for tn, dn in pairs2:
        if base.get(tn) == dn:
            continue
        tk_ = next((k for k, n in (target.get("tokens") or {}).items() if n == tn),
                   None)
        src = next((k for k, n in (donor.get("tokens") or {}).items() if n == dn),
                   None)
        filled.append({"animation": tk_, "source": src, "target": tn,
                       "donor": dn,
                       "reason": "the donor has no %s animation, so its %s "
                                 "animation stands in" % (tk_, src)})
    return pairs2, unmapped2, _e2, filled


def grid_mismatches(target, donor, pairs=None):
    """Which swapped animations change the frame grid.

    The engine pairs an animation with the art by ``frame_count`` and
    ``angle_count``, and this layer's survey found that a frame-count mismatch
    "plays the wrong frames rather than erroring".  So a reskin that puts a
    60-frame idle where a 45-frame one was is exactly the silent failure this
    toolkit exists to report.

    It is not a corner case: of the reskin pairs that share an animation at all,
    85.7% (74,109 of 86,468 sampled) differ on the grid of at least one of them.
    A copy whose grids agree renders identically; one that does not is reported.

    Returns a list of ``{"animation", "target", "donor"}`` dicts, where each grid
    is a sorted list of ``[frame_count, angle_count]``.  A grid is a list and not
    a pair because 16 of the 7,618 shipped files are named by records that
    disagree about it -- reporting both is honest, picking one is a guess.
    """
    if pairs is None:
        pairs, _unmapped, _extra = plan_swap(target, donor)
    tg = target.get("grids") or {}
    dg = donor.get("grids") or {}
    tt = target.get("tokens") or {}
    dt = donor.get("tokens") or {}
    out = []
    for tn, dn in pairs:
        k = None
        for key, name in tt.items():
            if name == tn:
                k = key
                break
        if k is None:
            continue
        a, b = list(tg.get(k) or ()), list(dg.get(k) or ())
        if a and b and a != b:
            out.append({"animation": k, "target": a, "donor": b})
    return out


def variant_files(target, donor, pairs=None, fill=False):
    """Files the entity uses ONLY while carrying something, mapped to the donor.

    Walking ``standing_graphic`` cannot reach these, because no unit record
    names them: the engine picks them by the resource being carried.  In game on
    2026-10-17 a whole-family villager reskin came out a sheep for every job
    except the stone miner while carrying, which stayed human -- the one file
    this function exists to export.

    Returns ``({target_basename: donor_basename}, [unmatched])``.  Each variant
    animation is resolved by the SAME rule the parent stem used for that token,
    so a variant never invents a second opinion; a variant animation the parent
    has no answer for goes to `unmatched` rather than being guessed.
    """
    if pairs is None:
        pairs, _unmapped, _extra = plan_swap(target, donor, fill=fill)
    tt = target.get("tokens") or {}
    by_target = dict((tn, dn) for tn, dn in pairs)
    out, unmatched = {}, []
    for v in target.get("resource_variants") or ():
        for anim, fname in sorted((v.get("files") or {}).items()):
            src = None
            own = tt.get(anim)
            if own:
                src = by_target.get(own)
            if src is None:
                got = fill_for(target, donor, anim)
                if got is not None:
                    src = (donor.get("tokens") or {}).get(got[0])
            if src is None:
                unmatched.append((v.get("stem"), anim, fname))
                continue
            out[fname] = src
    return out, unmatched


def swap_files(target, donor, game_root=None, fill=False, variants=True):
    """The {target_relpath: donor_basename} map a reskin has to write.

    Returns `(files, unpaired, missing)` -- ALWAYS three lists, whether or not a
    `game_root` was passed.  It used to return two when the caller omitted the
    game root, which meant the same call had two different shapes and a caller
    that forgot the argument got a silent `ValueError` at unpack time rather than
    a disc.

    `unpaired` names any target entry that was already an `_x2` name (which has
    no derivable partner) so the caller is not told a complete map was produced
    when it was not.  `missing` lists pairs whose donor file is absent from the
    install; it is empty when no `game_root` was given, because then nothing was
    checked -- the caller asked no question.

    Keys are paths RELATIVE TO THE GAME ROOT, because that is what the mod
    emitter wants: a mod mirrors the game root, so the target's own filename is
    its path under resources/_common/drs/graphics.  Values are donor basenames,
    to be read from the same directory.

    x1 and x2 are BOTH included.  Every shipped .sld is paired (7,743 and
    7,743), so writing only the x1 would leave the unit showing original art
    whenever the game runs in the high-resolution mode.  The companion name is
    derived by swapping the `_x1` suffix, and an unpaired companion is reported
    rather than assumed: a reskin that half-applies by resolution is exactly the
    kind of silent difference this toolkit is built to avoid.
    ``variants=False`` leaves out the art an entity uses only while carrying a
    resource.  It defaults to True because that art is otherwise invisible to
    every caller: it is named by no unit record, so a "whole family" reskin that
    skips it still leaves one job looking untouched.
    """
    pairs, unmapped, extra = plan_swap(target, donor, fill=fill)
    rel_dir = "/".join(GRAPHICS_DIR_REL)
    out, unpaired = {}, []
    for tn, dn in pairs:
        out[rel_dir + "/" + tn + ".sld"] = dn + ".sld"
        if tn.endswith("_x1"):
            out[rel_dir + "/" + tn[:-3] + "_x2.sld"] = dn[:-3] + "_x2.sld"
        elif tn.endswith("_x2"):
            unpaired.append(tn)
    if variants:
        vfiles, _vun = variant_files(target, donor, pairs=pairs, fill=fill)
        for tn, dn in sorted(vfiles.items()):
            out[rel_dir + "/" + tn + ".sld"] = dn + ".sld"
            if tn.endswith("_x1"):
                out[rel_dir + "/" + tn[:-3] + "_x2.sld"] = dn[:-3] + "_x2.sld"
            elif tn.endswith("_x2"):
                unpaired.append(tn)
    if game_root is None:
        return out, unpaired, []
    have = disk_files(game_root)
    missing = []
    for tgt, src in sorted(out.items()):
        if src[:-4] not in have:
            missing.append((tgt, src))
    return out, unpaired, missing


def missing_companions(game_root, relnames):
    """Which of these target names has no `_x2` companion on disk.

    Returns a list of x1 names whose high-resolution partner is absent.  A
    non-empty result means a reskin would apply at one resolution only, so the
    caller must decide rather than discover it in game.
    """
    have = disk_files(game_root)
    out = []
    for n in relnames:
        base = n[:-4] if n.endswith(".sld") else n
        if base.endswith("_x1") and (base[:-3] + "_x2") not in have:
            out.append(base)
    return sorted(out)
