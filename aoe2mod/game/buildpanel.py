"""The build-panel cache layer: `resources/_common/dat/futuravailableunits.json`.

WHY THIS MODULE EXISTS
----------------------
An in-game test on 2026-10-14 rewrote `CivTechTrees/<CIV>.json` (two ways: adding
a row and flipping a `NotAvailable` row) and the game offered nothing new.  That
looked like "the tree layer is not read".  It is worse, and more fixable than
that:

    the tree IS read -- by a GENERATOR, whose output is *pre-baked* into
    `futuravailableunits.json`, and it is that BAKED file the game reads.

Three independent generated relations say so (measured over the whole corpus, see
`_probe/probe_fu_derivation_pin.py`):

  * 2812 of 2827 (civ, unit) entries (99.47%) sit under the `Building ID` that
    civ's tree row gives the unit;
  * `RequiredAge` equals the tree row's `Age ID` on 2819 of 2826 (99.75%);
  * all 35 `PrereqTech` entries -- and only those -- are tree `ResearchRequired`
    rows.

And it is not canonical JSON: no `json.dumps(..., indent=2)` rule reproduces it
(a canonical dump differs in 983,313 bytes; only 0.74% of the file is a common
prefix).  A file regenerated at launch would be canonical.  So the shipped copy
was produced by another tool and baked in -- the tree is the SOURCE, this is the
ARTIFACT.

CONSEQUENCE, and the whole reason for the module: an availability edit has to
write BOTH.  Writing only the tree changes a model the game does not consult.
Writing only this file changes what the game shows without changing the model.
`aoe2mod/api.py` writes both -- through `_panel_availability`, on both the
single-intent and the bundle path.  Pinned by `_probe/test_panel_wire.py`, which
asserts that a `unit.availability` build emits the tree file and a panel file
together; if that wiring is ever dropped, that test fails rather than this
sentence quietly becoming a lie (it was one from Round 40's start until the
wiring landed).

THREE HARD FACTS ABOUT THE FORMAT
---------------------------------
1. **It is misnamed.** It carries a `Techs` list on 782 buildings, so it serves
   the TECH id space too (4,882 tech entries, 3,797 of them under the building
   the civ's tree tech row names).  Do not treat it as units-only.
2. **`paphosfutureavailableunits.json` is not a mode-only sibling.** It carries
   the 10 civs the main file omits (Achaemenids, Athenians, Macedonians, Puru,
   Spartans, Thracians, Paphos6..9).  Together the two cover all 62 tree files;
   the main file alone covers 56.
3. **It must not be re-serialised.** No `json.dumps` rule reproduces it, so the
   writer edits the TEXT surgically, exactly like the `.dat` writer patches
   bytes.  A no-op splice returns the file unchanged and an insertion changes
   only the inserted characters (both asserted in the pin).

ids are looked up per SPACE.  Unit ids and tech ids share an integer space (38
overlap), and the same integer also names a *building* here -- building 118
(`Builder`) lists buildings as entries.  Nothing may assume "ID 87" is unique.
"""
import json
import os

PANEL_NAME = "futuravailableunits.json"
PAPHOS_PANEL_NAME = "paphosfutureavailableunits.json"
PANEL_REL = os.path.join("resources", "_common", "dat", PANEL_NAME)
PAPHOS_PANEL_REL = os.path.join("resources", "_common", "dat", PAPHOS_PANEL_NAME)

ENTRY_KEYS = ("ID", "Name", "RequiredAge")          # observed minimum
GATE_KEYS = ("PrereqTech", "PrereqIconSet", "PrereqIconIndex", "PrereqStyle",
             "PrereqStringID")
BUILDINGS_KEY = "Buildings"
UNITS_KEY = "Units"
TECHS_KEY = "Techs"


class PanelError(Exception):
    """Raised when the cache file cannot be edited the way it was asked to be."""


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------
def panel_paths(game_root):
    """``(main_path, paphos_path)``; either may be ``None`` if absent."""
    main = os.path.join(game_root, PANEL_REL)
    pap = os.path.join(game_root, PAPHOS_PANEL_REL)
    return (main if os.path.isfile(main) else None,
            pap if os.path.isfile(pap) else None)


def load_panel(path):
    """``(text, obj)`` for one cache file.  `text` keeps the exact bytes.

    Read as UTF-8 with a BOM tolerated; the BOM is NOT part of `text`, so
    `text.encode("utf-8")` is not the file -- use `serialize_bytes`.
    """
    raw = open(path, "rb").read()
    text = raw.decode("utf-8-sig")
    return text, json.loads(text)


def serialize_bytes(text):
    """The exact bytes to write back for a `text` produced by this module."""
    return text.encode("utf-8")


def load_all(game_root):
    """``{key: {"text", "obj", "path", "sources", "ambiguous"}}`` over both files.

    Keys are the file's own civ display names (`Britons`).  Use
    `civ_key_for` to get from a `.dat`/tree name to one.

    **The two files share keys, and they are NOT copies of each other.**
    `FullTechCiv` appears in both with different contents (31 units only in the
    main file, 22 only in the paphos one).  A plain dict merge would drop the
    main file's version with no trace, so every record carries ``sources`` (all
    files that define that key) and ``ambiguous`` (more than one).  When
    ``ambiguous`` is true, ``text``/``path`` are the LAST file's -- a choice, not
    a fact.  Callers that intend to WRITE must use :func:`panel_path_for`, which
    answers the question directly instead of relying on load order.
    """
    out = {}
    for path in panel_paths(game_root):
        if path is None:
            continue
        text, obj = load_panel(path)
        for k in obj:
            rec = out.setdefault(k, {"key": k, "sources": []})
            rec["sources"].append(path)
            rec["text"] = text
            rec["obj"] = obj
            rec["path"] = path
    for rec in out.values():
        rec["ambiguous"] = len(rec["sources"]) > 1
    return out


def panel_path_for(game_root, civ_name):
    """The panel file that SHIPS this civilization's entry, or ``None``.

    Answered by looking, not by inferring: the two files are scoped per era
    (``civilizations.json``'s `era` field predicts the split -- 57 `base` civs in
    the main file, 6 `antiquity` civs in the paphos one -- but the prediction is
    corroboration; this function reports which file actually contains the key).

    Returns ``(path, key)``.  Use this before writing: `load_all` merges the
    files and cannot tell you which one a shared key came from.
    """
    for path in panel_paths(game_root):
        if path is None:
            continue
        _text, obj = load_panel(path)
        key = civ_key_for(obj, civ_name)
        if key is not None:
            return path, key
    return None, None


def civ_key_for(panels, civ_name):
    """The cache key for a civilization, or ``None``.

    The cache uses display names (`Britons`, `Magyars`) while the tree uses file
    stems (`BRITONS`, `MAGYAR`), so the bridge is `civtechtrees.civ_file_stem`.
    Imported lazily to keep this module free of a cycle.
    """
    from . import civtechtrees as CT
    if civ_name in panels:
        return civ_name
    want = CT.civ_file_stem(civ_name)
    for k in panels:
        if CT.civ_file_stem(k) == want:
            return k
    return None


def buildings(obj, key):
    return obj.get(key, {}).get(BUILDINGS_KEY, []) or []


def building_block(obj, key, building_id):
    for blk in buildings(obj, key):
        if blk.get("ID") == building_id:
            return blk
    return None


def entries(obj, key, building_id, space):
    """``space`` is ``UNITS_KEY`` or ``TECHS_KEY``."""
    blk = building_block(obj, key, building_id)
    return (blk.get(space) or []) if blk else []


def has_entry(obj, key, building_id, node_id, space):
    return any(e.get("ID") == node_id
               for e in entries(obj, key, building_id, space))


def find_entry(obj, key, node_id, space):
    """``(building_id, entry)`` for the first building listing `node_id`.

    Searches every building because the caller may not know which one; returns
    ``None`` when absent.  Note a node can legitimately appear under exactly one
    building, but this does not assume that.
    """
    for blk in buildings(obj, key):
        for e in blk.get(space) or []:
            if e.get("ID") == node_id:
                return blk.get("ID"), e
    return None, None


# --------------------------------------------------------------------------
# text surgery -- the only way to write it
# --------------------------------------------------------------------------
def _match_bracket(src, i):
    """Index of the ``]``/``}`` matching the bracket at ``src[i]``."""
    assert src[i] in "[{"
    depth = 0
    in_str = False
    esc = False
    while i < len(src):
        c = src[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise PanelError("unbalanced brackets while scanning the cache text")


def _civ_span(text, key):
    """``(start, end)`` of a civ's value object, braces included."""
    marker = '"%s"' % key
    at = text.find(marker)
    while at != -1:
        after = text.find(":", at + len(marker))
        j = text.find("{", after)
        # the colon and brace must belong to this key, not a later one
        if j != -1 and text.find('"', after + 1, j) == -1:
            return j, _match_bracket(text, j)
        at = text.find(marker, at + 1)
    raise PanelError("no civ block %r in the cache text" % key)


def _buildings_span(text, key):
    """``(start, end)`` of a civ's `Buildings` array."""
    lo, hi = _civ_span(text, key)
    at = text.find('"%s"' % BUILDINGS_KEY, lo, hi)
    if at == -1:
        raise PanelError("civ %r has no %s array" % (key, BUILDINGS_KEY))
    arr = text.find("[", at)
    return arr, _match_bracket(text, arr)


def _building_objects(text, key):
    """``[(start, end, id)]`` for each building block of a civ.

    The ONLY reliable way to find a building's arrays: scanning back for the
    nearest `{` before a `"Units":` key lands inside a previous array's entry,
    not on the building object.  Enumerate the top-level objects instead.
    """
    arr, stop = _buildings_span(text, key)
    out = []
    i = arr + 1
    while i < stop:
        if text[i] == "{":
            end = _match_bracket(text, i)
            out.append((i, end, _int_field(text, i, end, "ID")))
            i = end + 1
        else:
            i += 1
    return out


def _int_field(text, lo, hi, name):
    """Read ``"name": <int>`` inside ``text[lo:hi]``; ``None`` if absent."""
    at = text.find('"%s":' % name, lo, hi)
    if at == -1:
        return None
    e = text.find(":", at) + 1
    while e < hi and text[e] in " \r\n\t":
        e += 1
    s = e
    while s < hi and text[s] not in ",\r\n}":
        s += 1
    try:
        return int(text[e:s].strip())
    except ValueError:
        return None


def _array_span(text, key, building_id, space):
    """``(start, end)`` of one building's `Units`/`Techs` array, or ``None``.

    Bounded to the civ block and resolved through the building object, so this
    does not depend on indentation or on `ID` being unique across the file
    (building 118 lists buildings AS entries, so `"ID": 87` occurs twice).
    """
    for b_start, b_end, b_id in _building_objects(text, key):
        if b_id != building_id:
            continue
        at = text.find('"%s":' % space, b_start, b_end)
        if at == -1:
            return None
        arr = text.find("[", at, b_end)
        return arr, _match_bracket(text, arr)
    return None


def _entry_spans(text, arr_lo, arr_hi, node_id):
    """``[(start, end, indent)]`` for every top-level object in the array."""
    out = []
    i = arr_lo + 1
    while i < arr_hi:
        c = text[i]
        if c == "{":
            end = _match_bracket(text, i)
            idat = text.find('"ID":', i, end)
            got = None
            if idat != -1:
                k = text.find(":", idat) + 1
                e = k
                while e < end and text[e] in " \r\n\t":
                    e += 1
                s = e
                while s < end and text[s] not in ",\r\n}":
                    s += 1
                try:
                    got = int(text[e:s].strip())
                except ValueError:
                    got = None
            if got == node_id:
                line = text.rfind("\n", arr_lo, i) + 1
                out.append((i, end + 1, i - line))
            i = end + 1
        else:
            i += 1
    return out


def _indent_of(text, arr_lo, arr_hi):
    """Indentation to use for a new element, copied from the file itself."""
    i = arr_lo + 1
    while i < arr_hi:
        if text[i] == "{":
            line = text.rfind("\n", arr_lo, i) + 1
            return i - line
        i += 1
    # empty array: the file indents elements two past the '[' column
    line = text.rfind("\n", 0, arr_lo) + 1
    return (arr_lo - line) + 2


def entry_text(entry, indent):
    """Render one cache entry the way the file does (2-space steps, CRLF)."""
    keys = [k for k in ENTRY_KEYS if k in entry]
    keys += [k for k in entry if k not in keys]
    pad = " " * indent
    body = []
    for k in keys:
        v = entry[k]
        body.append('%s  "%s": %s' % (pad, k, json.dumps(v, ensure_ascii=False)))
    return "%s{\r\n%s\r\n%s}" % (pad, ",\r\n".join(body), pad)


def insert_entry(text, key, building_id, entry, space=UNITS_KEY):
    """Insert ``entry`` into ``key``'s ``building_id`` ``space`` array.

    Returns the new text.  Raises `PanelError` if the node is already listed or
    the building/array does not exist -- both are caller errors, not conditions
    to paper over.
    """
    node_id = entry.get("ID")
    span = _array_span(text, key, building_id, space)
    if span is None:
        raise PanelError("civ %r building %r has no %s array"
                         % (key, building_id, space))
    arr_lo, arr_hi = span
    if _entry_spans(text, arr_lo, arr_hi, node_id):
        raise PanelError("civ %r building %r already lists %s %r"
                         % (key, building_id, space, node_id))
    indent = _indent_of(text, arr_lo, arr_hi)
    body = entry_text(entry, indent)
    if text[arr_lo + 1:arr_hi].strip():
        # Existing elements: close the last one with a comma, then add ours.
        # `text[inner_end:]` already begins with the newline and indent that lead
        # to the closing `]`, so adding another separator here would leave those
        # characters behind on removal -- insert/remove would not be inverse.
        inner_end = arr_hi
        while text[inner_end - 1] in " \r\n\t":
            inner_end -= 1
        return text[:inner_end] + ",\r\n" + body + text[inner_end:]
    return text[:arr_lo + 1] + "\r\n" + body + "\r\n" + " " * (indent - 2) \
        + text[arr_lo + 1:]


def ensure_array(text, key, building_id, space=UNITS_KEY):
    """Give building `building_id` an empty `space` array if it has none.

    A BUILDING THE FILE ONLY KNOWS AS SOMETHING YOU CAN PUT DOWN has no
    Units/Techs key at all -- building 598 (Outpost) is exactly
    {"ID": 598, "Name": "Outpost", "RequiredAge": 1} in all 68 panels, and so
    are most of the wall/tower/mill blocks.  Asking `insert_entry` for their
    Units array raises "has no Units array", which reads like a refusal but is
    only a missing key: the generator omits an array that would be empty.

    So write the key, empty, in the file's own shape (CRLF, the same indent as
    the other keys of that block), and let `insert_entry` fill it -- that path
    already knows how to expand an empty array into a multi-line element list,
    and the pair stays inverse: removing the last element leaves an empty array
    behind, which is what the generator would have written.

    Returns the text unchanged when the array already exists.
    """
    for b_start, b_end, b_id in _building_objects(text, key):
        if b_id != building_id:
            continue
        at = text.find('"%s":' % space, b_start, b_end)
        if at != -1:
            return text
        first_key = text.find('"', b_start + 1, b_end)
        if first_key == -1:
            raise PanelError("civ %r building %r is an empty object, so there "
                             "is no indentation to copy" % (key, building_id))
        line = text.rfind("\n", b_start, first_key) + 1
        pad = " " * (first_key - line)
        inner_end = b_end
        while text[inner_end - 1] in " \r\n\t":
            inner_end -= 1
        return (text[:inner_end] + ',\r\n%s"%s": []' % (pad, space)
                + text[inner_end:])
    raise PanelError("civ %r has no building %r" % (key, building_id))


def lists_node(text, key, building_id, node_id, space=UNITS_KEY):
    """True when `building_id` already holds `node_id` in that array."""
    span = _array_span(text, key, building_id, space)
    if span is None:
        return False
    return bool(_entry_spans(text, span[0], span[1], node_id))


def remove_entry(text, key, node_id, space=UNITS_KEY):
    """Remove every entry for ``node_id`` from the civ's ``space`` arrays.

    Returns ``(text, removed)``.  Removing nothing is not an error -- the caller
    may be revoking something the panel never listed (287-2827 entries differ).
    """
    removed = 0
    while True:
        hit = None
        for b_start, b_end, b_id in _building_objects(text, key):
            arr = _array_span(text, key, b_id, space)
            if arr is None:
                continue
            spans = _entry_spans(text, arr[0], arr[1], node_id)
            if spans:
                hit = (spans[0][0], spans[0][1], arr[0], arr[1])
                break
        if hit is None:
            return text, removed
        e_start, e_end, arr_lo, arr_hi = hit
        # extend over a preceding or trailing comma
        after = e_end
        while after < arr_hi and text[after] in " \r\n\t":
            after += 1
        before = e_start
        while before > arr_lo and text[before - 1] in " \r\n\t":
            before -= 1
        if after < arr_hi and text[after] == ",":
            text = text[:before] + text[after + 1:]
        elif before > arr_lo and text[before - 1] == ",":
            text = text[:before - 1] + text[e_end:]
        else:
            text = text[:before] + text[e_end:]
        removed += 1


def _building_offsets(text, lo, hi):
    """Deprecated shim: prefer `_building_objects(text, key)`."""
    for k in ():
        pass
    raise PanelError("use _building_objects(text, key)")


def verify_surgical(before_text, after_text, inserted_chars=None):
    """``(ok, info)`` -- the edit touched only the region it was asked to.

    When ``inserted_chars`` is given, the check is that everything outside one
    contiguous insertion of exactly that length is unchanged.  This is the
    cache-layer equivalent of the `.dat` writer's "every changed byte lies inside
    a claimed edit" invariant.

    ``info["inserted"]`` is the NET change, so a removal reports a negative
    number -- a deletion is a contiguous region like any other, and requiring it
    to be positive would call a correct removal a failure.  Use
    ``info["kind"]`` when the direction matters.

    The prefix and the suffix are NOT allowed to overlap: on a deletion they
    otherwise double-count the same characters face to face (the suffix scan must
    be bounded by the SHORTER text), and the net change comes out wrong.
    """
    info = {}
    shorter = min(len(before_text), len(after_text))
    p = 0
    while p < shorter and before_text[p] == after_text[p]:
        p += 1
    s = 0
    while (s < shorter - p
           and before_text[len(before_text) - 1 - s] == after_text[len(after_text) - 1 - s]):
        s += 1
    info["common_prefix"] = p
    info["common_suffix"] = s
    info["inserted"] = len(after_text) - len(before_text)
    info["kind"] = ("none" if info["inserted"] == 0
                    else "insert" if info["inserted"] > 0 else "delete")
    info["outside_is_untouched"] = (
        before_text[:p] == after_text[:p]
        and before_text[len(before_text) - s:] == after_text[len(after_text) - s:])
    # A matching prefix and suffix are TRUE BY CONSTRUCTION (p and s were
    # computed AS the longest common prefix/suffix), so `outside_is_untouched`
    # alone can never fail -- which is exactly the tautology the audit found:
    # `ok = outside_is_untouched` made verify_surgical("aaaa", "bbbb") return
    # ok=True.  The real "one contiguous edit" test is that the prefix and the
    # suffix MEET: the differing middle is a single block only when
    # p + s == shorter.  Two disjoint edits leave p + s < shorter and must be
    # reported as NOT surgical.
    info["contiguous"] = (p + s) == shorter
    ok = info["outside_is_untouched"] and info["contiguous"]
    if inserted_chars is not None:
        info["inserted_as_expected"] = info["inserted"] == inserted_chars
        ok = ok and info["inserted_as_expected"]
    return ok, info


# --------------------------------------------------------------------------
# synthesising an entry that the file does not have yet
# --------------------------------------------------------------------------
def _entry_key(entry):
    """A hashable identity for an entry's VALUES (order-independent)."""
    return tuple(sorted((k, repr(v)) for k, v in entry.items()))


def entries_of(obj, node_id, space=UNITS_KEY):
    """Every ``(civ_key, building_id, entry)`` in one file object."""
    out = []
    for key in obj:
        for blk in buildings(obj, key):
            for e in (blk.get(space) or []):
                if e.get("ID") == node_id:
                    out.append((key, blk.get("ID"), e))
    return out


def synth_entry(civ_key, node_id, building_id, age_id=None, space=UNITS_KEY,
                ready=None, pool=None):
    """A cache entry for a node this civ's file does not list yet.

    **Copy, never invent.**  The rule is measured, not chosen: of the 402
    ``(civ, node)`` entries the shipped files carry for a node their tree calls
    NOT ``ResearchedCompleted``, taking another civ's entry verbatim and setting
    only ``RequiredAge`` from the target's own tree ``Age ID`` reproduces the
    shipped bytes on **400 (99.5%)** (`_probe/probe_panel_entry_synth.py`).

    The two misses are Chronicles renames the file words differently from both
    the tree and the string tables (``Athenians`` calls unit 5 ``Gastraphetes``
    where the semantic index says ``Gastraphetoros``), so no cheaper source is
    better -- R1 (verbatim) scores 399, and adding the index's variant name
    SCORES WORSE at 399 because the panel has its own naming.  Copying is
    therefore not a shortcut; it is the most accurate rule available.

    ``ready(civ_key) -> bool`` should say whether that civ's TREE row for this
    node is ``ResearchedCompleted``.  Donors that pass are preferred (the same
    discipline as :func:`civtechtrees.donor_row`), then the most common entry
    variant, then name order -- so the choice never depends on dict iteration
    order.  Returns ``None`` when no civilization anywhere lists the node.

    ``pool`` lets a caller reuse a prebuilt ``{node_id: [entries]}``; build one
    with :func:`entry_pool`.
    """
    if pool is None:
        raise PanelError("synth_entry needs a pool; call entry_pool(...) first")
    cands = [c for c in pool.get(node_id, []) if c[0] != civ_key]
    if not cands:
        return None
    if ready is not None:
        fit = [c for c in cands if ready(c[0])] or cands
    else:
        fit = cands
    freq = {}
    for c in fit:
        k = _entry_key(c[2])
        freq[k] = freq.get(k, 0) + 1
    donor_key, _donor_bid, donor_entry = min(
        fit, key=lambda c: (-freq[_entry_key(c[2])], c[0]))
    entry = dict(donor_entry)
    # The ONE field the target's own row wins on.  `Name` is deliberately NOT
    # taken from the tree: measured 398/402 with it, 400/402 without.
    if age_id is not None:
        entry["RequiredAge"] = age_id
    return {"entry": entry, "donor": donor_key, "donor_building": building_id,
            "keys": sorted(entry)}


def entry_pool(obj, space=UNITS_KEY):
    """``{node_id: [(civ_key, building_id, entry)]}`` over one file object."""
    pool = {}
    for key in obj:
        for blk in buildings(obj, key):
            for e in (blk.get(space) or []):
                pool.setdefault(e.get("ID"), []).append(
                    (key, blk.get("ID"), e))
    return pool


def panel_rel_for(path):
    """The engine-relative path for an absolute panel path, or ``None``."""
    if path is None:
        return None
    base = os.path.basename(path)
    if base == PANEL_NAME:
        return PANEL_REL
    if base == PAPHOS_PANEL_NAME:
        return PAPHOS_PANEL_REL
    return None


def availability_edit(game_root, civ_key, node_id, action, building_id=None,
                      age_id=None, space=UNITS_KEY, obj=None, ready=None,
                      pool=None, text=None):
    """The PANEL half of "let <civ> build <node>".

    Returns ``(report, {rel_path: bytes})``.  The dict is empty when the panel
    already agrees with the request -- which is the common case, and the reason
    this is called on every availability edit rather than only on "grant":

      * the civ's panel already lists the node -> nothing to do (a grant whose
        tree row was ``NotAvailable`` is exactly this: the panel often lists what
        the tree calls blocked, which is 11 of the 18 shipped disagreements);
      * the request is a REVOKE -> the entry is removed, unless it was absent.

    ``building_id``/``age_id`` come from the civ's TREE row (``Building ID`` and
    ``Age ID``); the shipped file agrees with those on 99.47% / 99.75% of entries,
    so the tree row is the right source rather than a second opinion.

    **The file to edit is chosen by looking, not by era.**  ``panel_path_for``
    reports which file actually ships this civ; inferring from
    ``civilizations.json``'s ``era`` agrees, but agreement is corroboration, not
    the answer.  A civ with no panel entry anywhere is reported, not guessed at.

    ``obj``/``ready``/``pool`` let a caller skip re-reading 1.3 MB per call; pass
    the output of :func:`load_all` / :func:`entry_pool` when doing a bundle.

    ``text`` is the same idea for a bundle that edits ONE FILE twice.  Without
    it every call starts from the SHIPPED text and the caller's
    ``files.update()`` lets the later full-file result overwrite the earlier one,
    so "grant this to the British and revoke it from the Incas" silently ships
    only the revoke.  Pass the text the previous call produced (the caller's
    ``Toolkit._panel_availability`` does this through a ``texts`` map) to make
    the edits chain.
    """
    path, key = panel_path_for(game_root, civ_key)
    if path is None:
        return {"ok": False, "reason": "no build-panel file lists civilization "
                                       "%r, so its menu entry cannot be edited"
                                       % (civ_key,)}, {}
    if text is None:
        text, file_obj = load_panel(path)
    else:
        text, file_obj = load_panel_text(text)
    if obj is not None:
        file_obj = obj
    rep = {"path": path, "rel": panel_rel_for(path), "civ_key": key,
           "panel_name": os.path.basename(path),
           "mode": None, "before_entries": None, "after_entries": None}

    if action == "revoke":
        new_text, removed = remove_entry(text, key, node_id, space=space)
        rep["mode"] = "remove_entry" if removed else "none"
        rep["removed"] = removed
    else:
        if find_entry(file_obj, key, node_id, space)[1] is not None:
            rep["mode"] = "none"
            rep["reason"] = ("the panel already lists this node for %s, so no "
                             "entry is added" % key)
            rep["ok"] = True
            return rep, {}
        if building_id is None:
            return {"ok": False,
                    "reason": "no building is known for this node, so the panel "
                              "entry has nowhere to go"}, {}
        if pool is None:
            pool = entry_pool(file_obj, space=space)
        synth = synth_entry(key, node_id, building_id, age_id=age_id,
                            space=space, ready=ready, pool=pool)
        if synth is None:
            return {"ok": False,
                    "reason": "no civilization anywhere lists this node in its "
                              "menu, so there is no entry to copy"}, {}
        try:
            new_text = insert_entry(text, key, building_id, synth["entry"],
                                    space=space)
        except PanelError as e:
            return {"ok": False, "reason": str(e)}, {}
        rep["mode"] = "add_entry"
        rep["donor"] = synth["donor"]
        rep["entry"] = synth["entry"]

    before = count_entries(file_obj, key, node_id, space)
    ok, info = verify_surgical(text, new_text)
    rep["surgical"] = ok
    rep["surgical_info"] = info
    _t, new_obj = load_panel_text(new_text)
    rep["before_entries"] = before
    rep["after_entries"] = count_entries(new_obj, key, node_id, space)
    rep["ok"] = bool(ok and (new_text != text or rep["mode"] == "none"))
    return rep, {rep["rel"]: serialize_bytes(new_text)}


def count_entries(obj, key, node_id, space=UNITS_KEY):
    """How many entries ANY of this civ's buildings hold for ``node_id``.

    Counted across every building rather than the one the tree names: a revoke
    removes from wherever it is, so "one before, zero after" is the claim that
    actually holds, while a per-building count would read 0/0 when the entry sat
    under a different building.
    """
    return sum(1 for _b, _e in _iter_civ_entries(obj, key, node_id, space))


def _iter_civ_entries(obj, key, node_id, space):
    for blk in buildings(obj, key):
        for e in (blk.get(space) or []):
            if e.get("ID") == node_id:
                yield blk.get("ID"), e


def load_panel_text(text):
    """``(text, obj)`` for panel TEXT already in memory (no file read)."""
    return text, json.loads(text)




# --------------------------------------------------------------------------
# ages -- which era a node is first available in
# --------------------------------------------------------------------------
AGE_NAMES = {1: "黑暗时代", 2: "封建时代", 3: "城堡时代", 4: "帝王时代"}
AGE_SHORT = {1: "黑暗", 2: "封建", 3: "城堡", 4: "帝王"}


def required_age_vote(obj, space=UNITS_KEY):
    """``{(space, node_id): {age: votes}}`` over every civilization in a file.

    ``RequiredAge`` is per ``(civilization, building, node)``, so the same unit
    can be written with two different ages (measured: 13 of 272 unit nodes, e.g.
    the Armenians' Long Swordsman reads 2 where everyone else reads 3).  The
    panel therefore needs one answer per node, and the honest one is the vote:
    a dict of counts, so a caller can say「13 个文明写 2、49 个写 3」instead of
    pretending there is no disagreement.

    Measured cost over the shipped file (58 civs, 1.1 MB): 0.004 s.
    """
    out = {}
    for key in obj:
        for blk in buildings(obj, key):
            for e in (blk.get(space) or []):
                node = e.get("ID")
                age = e.get("RequiredAge")
                if not isinstance(node, int) or not isinstance(age, int):
                    continue
                if not 1 <= age <= 4:
                    continue
                out.setdefault((space, node), {})
                out[(space, node)][age] = out[(space, node)].get(age, 0) + 1
    return out


def age_of(votes):
    """``(age, tie)`` -- the age most civilizations write, or ``(None, False)``."""
    if not votes:
        return None, False
    ranked = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    tie = len(ranked) > 1 and ranked[0][1] == ranked[1][1]
    return ranked[0][0], tie
