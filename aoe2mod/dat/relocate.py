"""Move the parsed model after the bytes underneath it changed length.

WHY THIS EXISTS.  Adding one record splices bytes into the middle of the .dat,
so every offset the model recorded -- 136,861 unit records, their field marks,
their cost and attack lists, the tail pointer -- lands on the wrong byte.
The honest fix is to parse the 93 MB again: `Parser.parse` 5.12 s plus
`locate.locate` 5.33 s on 2026-11-06, so a single "duplicate this unit" click
cost the player ten seconds before the twelve-second index scan even started.

But a splice does not invalidate *what* the model says, only *where* it says it.
An insertion of N bytes at offset A moves every offset >= A by N and leaves the
records before A untouched; a deletion of N bytes does the same with -N.  So the
model can be carried across the edit by adding one number to each offset
(measured 0.28 s for all of them) and re-walking only the one civilisation whose
own record run was rewritten (0.07 s).

The proof that this is not wishful thinking: `locate.walk_civ` consumes the civ
block end to end, so `chain_ok()` re-checks the invariant `scan()`'s `leftover`
was standing in for -- every unit record starts where the previous one ended,
every civilisation starts where the previous one ended, and the last one ends
exactly at the tail pointer.  If that fails, the caller falls back to the full
parse instead of trusting a shifted guess.

`shift` is applied to ORIGINAL coordinates, so `splice_rules()` first unfolds
the applied writes back into the coordinates they had before any of them ran.
"""

# The offsets `locate.walk_unit` records besides the `_offs` mark dictionary.
_UNIT_SPOT_KEYS = ("_creatable_start", "_creatable_end",
                   "_creatable_head_end", "_off_displayed_pierce_armour")

# Six keys `parser.read_unit` keeps, i.e. what `stats["civs"][i]["units"]`
# holds.  That list is a SECOND copy of the same records (a different set of
# dicts, not the ones `walk_civ` built), so it has to be resynchronised by hand.
_STATS_UNIT_KEYS = ("class", "hit_points", "id", "name", "type",
                    "task_swap_group")


def splice_rules(writes, undo=False):
    """`[(at, delta)]` in ORIGINAL coordinates, ascending.

    `apply_steps` records each write's `off` in the coordinates of the buffer as
    it was when THAT write ran, so the second write of a plan is already looking
    at a buffer the first one moved.  Walking the list forwards and subtracting
    the movement accumulated so far recovers the original address -- which is
    the only coordinate system in which a single monotone "shift everything
    after A" rule is correct.
    """
    rules = []
    moved = 0
    for w in writes:
        before = len(w.get("before") or b"")
        after = len(w.get("after") or b"")
        at = int(w["off"]) - moved
        delta = after - before
        moved += delta
        if delta:
            rules.append((at, delta))
    rules.sort()
    if not undo:
        return rules
    # AN UNDO IS APPLIED TO THE EDITED BUFFER, SO ITS THRESHOLDS LIVE THERE.
    # A rule says "everything at or after `at` moves by `delta`", which is a
    # statement about the buffer it is applied to.  For the forward edit that is
    # the original buffer, which is what the unfold above recovered.  The undo
    # runs on the edited buffer, where every splice after the first has already
    # been pushed forward by the deltas before it, so its threshold moves too.
    # Keeping `at` and only flipping the sign subtracts at the wrong address for
    # every rule but the first -- and the four-splice case in
    # `_probe/_tmp/t_relocate.py` never caught it because it carries no undo.
    out = []
    pre = 0
    for at, delta in rules:
        out.append((at + pre, -delta))
        pre += delta
    out.sort()
    return out


def shift(rules, value):
    """`value` after the splices described by `rules`, or `value` if None.

    COMPARE AGAINST A MOVED THRESHOLD, NOT AGAINST `at`.  `at` is an ORIGINAL
    coordinate while `value` is already being moved, so after the first rule the
    two numbers live in different spaces: a position 10 bytes short of the second
    insertion point would be pushed past it by a 20-byte first insertion and then
    collect the second insertion's bytes as well.  Measured 2026-11-06: the four
    splice cases in `_probe/_tmp/t_relocate.py` all passed with the naive
    comparison only because the deltas were small next to the gaps, and any
    offset inside `[at_next - delta, at_next)` was silently off.

    `acc` is the movement the rules already applied, so `at + acc` is where that
    splice sits in the coordinates `value` is currently in.
    """
    if value is None or not rules:
        return value
    acc = 0
    for at, delta in rules:
        if value >= at + acc:
            value += delta
            acc += delta
        else:
            break                       # ascending: nothing later can apply
    return value


def shift_unit(u, rules):
    """Move every byte offset one unit record remembers."""
    for key in ("_start", "_end"):
        if u.get(key) is not None:
            u[key] = shift(rules, u[key])
    offs = u.get("_offs")
    if offs:
        for key in offs:
            offs[key] = shift(rules, offs[key])
    for key in _UNIT_SPOT_KEYS:
        if u.get(key) is not None:
            u[key] = shift(rules, u[key])
    # The display-name id's address.  Not part of `_UNIT_SPOT_KEYS` because that
    # tuple is about the type-dependent tail; this one sits three bytes into
    # every record, so a splice anywhere earlier moves it like everything else.
    if u.get("_off_dll_name") is not None:
        u["_off_dll_name"] = shift(rules, u["_off_dll_name"])
    for c in u.get("costs") or ():
        if c.get("_off_amount") is not None:
            c["_off_amount"] = shift(rules, c["_off_amount"])
    for d in u.get("train_locations") or ():
        if d.get("_off_train_time") is not None:
            d["_off_train_time"] = shift(rules, d["_off_train_time"])
    t50 = u.get("type50")
    if isinstance(t50, dict):
        for group in ("attacks", "armors"):
            for a in t50.get(group) or ():
                for key in ("_off_class", "_off_amount"):
                    if a.get(key) is not None:
                        a[key] = shift(rules, a[key])


def shift_civs(civs, rules):
    """Move every civ and every record in it.  Returns nothing; mutates."""
    for c in civs:
        if c.get("_start") is not None:
            c["_start"] = shift(rules, c["_start"])
        if c.get("_end") is not None:
            c["_end"] = shift(rules, c["_end"])
        for u in c.get("units") or ():
            shift_unit(u, rules)


def units_contiguous(civ):
    """True if this civ's records are back to back and end where the civ ends."""
    units = civ.get("units") or ()
    end = civ.get("_end")
    if not units:
        return True
    prev = None
    for u in units:
        if u.get("_start") is None or u.get("_end") is None:
            return False
        if prev is not None and u["_start"] != prev:
            return False
        prev = u["_end"]
    return prev == end


def chain_ok(civs, civs_start, tail):
    """The invariant `unitfields.scan` calls `leftover == 0`.

    `walk_civ` reads a civilisation's flag array and then one record per non-zero
    flag, so consecutive records touch.  If the first civ starts at the block
    start, every later civ starts where the previous ended, and the last ends at
    the tail pointer, then the walk accounted for every byte of the civ block --
    which is exactly what makes the recorded offsets trustworthy.
    """
    if not civs:
        return False
    if civs[0].get("_start") != civs_start:
        return False
    for a, b in zip(civs, civs[1:]):
        if a.get("_end") != b.get("_start"):
            return False
    if civs[-1].get("_end") != tail:
        return False
    return all(units_contiguous(c) for c in civs)


def re_walk_civ(civs, raw, gv, civ_index):
    """Re-read one civilisation out of the new bytes, in place.

    The other 62 civs only MOVED (their bytes are untouched), so they are carried
    across by `shift_civs`.  This one had its flag array resized and its record
    run rewritten, so its spans have to come out of the buffer itself.
    """
    from aoe2mod.dat import locate as L
    c = civs[civ_index]
    start = c.get("_start")
    if start is None:
        raise ValueError("第 %d 号文明没有起点，没法只重走一个文明" % (civ_index,))
    r = L.Orec(raw, start, gv=gv)
    civs[civ_index] = L.walk_civ(r, civ_index)
    return civs[civ_index]


def stats_units(civ):
    """`stats["civs"][i]["units"]` shape for a walked civ."""
    out = []
    for u in civ.get("units") or ():
        row = {}
        for key in _STATS_UNIT_KEYS:
            row[key] = u.get(key)
        out.append(row)
    return out


def sync_stats_civ(stats, civ_index, civ):
    """Keep the parser's瘦身 copy of the civ in step with the walked one."""
    rows = stats.get("civs") or []
    if civ_index >= len(rows):
        return False
    row = rows[civ_index]
    row["units"] = stats_units(civ)
    row["unit_pointers_total"] = civ.get("unit_pointers_total",
                                         row.get("unit_pointers_total"))
    row["unit_pointers_nonzero"] = len(row["units"])
    return True
