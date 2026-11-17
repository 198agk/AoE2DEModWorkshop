"""Carry one record from one DAT generation byte layout into another.

WHY THIS EXISTS.  `dat/writer.py` copies bytes through `Writer.op(n)`, which
reads them out of the `raw` buffer it was handed -- so it can only re-emit the
stream it already has.  With `raw=None` every `op(n)` writes n zero bytes, and
a 128,725-record "round trip" through it looked perfect while silently zeroing
every byte the model does not name (measured: 93.1 percent of a 93 MB stream is
`opaque`).  That is the wrong tool for a generation change.

This module replays `unitfields.read_unit_fields` / `techfields.read_tech_fields`
-- the two functions that already know every named field and every generation
guard -- against a *tape* that pulls each value out of the source record BY
NAME and appends it in the TARGET generation order.  The field order stays
single-copy: the copy the parser is already tested against.

Every named field a unit record contains is on the tape.  That used to leave one
gap: the six-byte `Building.LootingTable` run, which `parser.read_unit` skips
and which `unitfields._building` only marked with a `raw` placeholder.  It is
now six named `Building.LootingTable.0..5` u8 fields, so the tape carries them
by name like everything else and a generation change can no longer drop them
back to zeros.

Verified by round trip: decode at one generation and re-encode at the SAME
generation must reproduce the record byte for byte.  `_probe/test_portgen.py`
asserts that over every record of every archived generation.
"""

import struct

from ..dat import parser as P
from ..dat import unitfields as UF
from ..dat import techfields as TF

__all__ = ["Tape", "encode_unit", "encode_tech", "ID_FIELDS", "is_id_field",
           "folded_name"]

_FMT = {"u8": "<B", "i16": "<h", "u16": "<H", "i32": "<i", "u32": "<I",
        "f32": "<f"}

#: Field names whose value is another unit id.  Renumbering an added record
#: has to rewrite these or the new unit trains the old id and the old id now
#: belongs to the game.  Matched by suffix where the slot index varies.
ID_FIELDS = frozenset((
    "ID", "CopyID", "BaseID", "DeadUnitID", "BloodUnitID", "StackUnitID",
    "HeadUnit", "TransformUnit", "PileUnit", "ProjectileUnitID",
    "ChargeProjectileUnit", "SecondaryProjectileUnit",
))

_ID_SUFFIX = (".UnitID", ".DropSites", ".ProjectileUnit")

#: The hotkey a creatable unit carries when the author never set one.  Measured
#: on both sides of the split: `Creatable.HotKeyFromUnit` in 8.4 and
#: `Creatable.TrainLocations.0.HotKeyID` in 8.9 are the same numbering space
#: (distinct 330 vs 351, top value 16000 on both, 7521 vs 308 records), so the
#: value moves across untouched and 16000 is what "no hotkey" looks like.
NO_HOTKEY = 16000


def is_id_field(name):
    return name in ID_FIELDS or name.endswith(_ID_SUFFIX)


# -- the name folds ---------------------------------------------------------
#
# Two generations can hold the SAME information under DIFFERENT names, and a
# tape that reads strictly by name then defaults a field the source has a
# perfectly good answer for.  Measured over every archived generation, there
# are exactly three such pairs -- and leaving any of them alone is silent data
# loss, not a missing nicety:
#
#   gv < 53 (8.4)                                  gv >= 53 (8.9)
#   ------------------------------------------------------------------------
#   ResearchLocation (i16)                         ResearchLocations.N.LocationID
#   ResearchTime (i16)                             ResearchLocations.N.ResearchTime
#   ButtonID (u8)                                  ResearchLocations.N.ButtonID
#   HotKey (i32)                                   ResearchLocations.N.HotKeyID
#   (absent)                                       ResearchLocationCount
#
#   gv < 51                                        gv >= 51
#   ------------------------------------------------------------------------
#   one fixed train location                       Creatable.TrainLocationsCount
#   Creatable.HotKeyFromUnit (i32)                 Creatable.TrainLocations.N.HotKeyID
#
#   gv < 50                                        gv >= 50
#   ------------------------------------------------------------------------
#   (absent)                                       Bird.Tasks.N.Enabled
#
# The 209785 report -- "训练点全空" in AGE -- is the second group biting.  8.4 has
# no name called `Creatable.TrainLocationsCount`, so the count went out as 0, the
# target-side `for i in range(n)` never ran, and a record that trained something
# in 8.4 trained nothing in 8.9.  The tech side had the same hole: 3,030 techs
# re-encoded to 8.9, every one of them with `ResearchLocationCount = 0`, so the
# author's own techs had no research building in the output.
#
# NOT folded, because the two sides already agree on the name: Type50.Attacks /
# Armours, Bird.DropSites, Bird.Tasks, DamageGraphics, ResourceStorages.  Those
# groups are count-prefixed but exist under the same names at both ends.

#: One-to-one renames that need nothing but a source name and a default.
#: BOTH directions are listed: `_raw` consults the source dict first, so only
#: the side that is actually absent is ever rebuilt, and the table stays one
#: readable pair per line instead of two directional tables that can drift.
_SIMPLE_FOLD = {
    # tech, 8.9 -> 8.4: the folded group goes back to four scalars
    "ResearchLocation": ("ResearchLocations.0.LocationID", -1, "i16"),
    "ResearchTime": ("ResearchLocations.0.ResearchTime", 0, "i16"),
    "ButtonID": ("ResearchLocations.0.ButtonID", 0, "u8"),
    "HotKey": ("ResearchLocations.0.HotKeyID", -1, "i32"),
    # tech, 8.4 -> 8.9: the four scalars become slot 0 of the group
    "ResearchLocations.0.LocationID": ("ResearchLocation", -1, "i16"),
    "ResearchLocations.0.ResearchTime": ("ResearchTime", 0, "i16"),
    "ResearchLocations.0.ButtonID": ("ButtonID", 0, "u8"),
    "ResearchLocations.0.HotKeyID": ("HotKey", -1, "i32"),
    # unit: the pre-8.9 hotkey lived on the unit, the post-8.9 one on its first
    # train location.  Same numbering space on both sides (measured: distinct
    # 330 vs 351, top value 16000 on both), so the value moves untouched.
    "Creatable.HotKeyFromUnit":
        ("Creatable.TrainLocations.0.HotKeyID", NO_HOTKEY, "i32"),
    "Creatable.TrainLocations.0.HotKeyID":
        ("Creatable.HotKeyFromUnit", NO_HOTKEY, "i32"),
}


def _synth(value, kind):
    """A source slot that the fold built.  `offset` is -1: there is no byte."""
    return {"offset": -1, "kind": kind, "value": value}


def folded_name(name):
    """The name the OTHER generation uses for `name`, or None when unchanged.

    Exported because the fold is not only the tape's business: upgrade.py's
    planner diffs two files byte by byte and addresses the difference by the
    BASE file's field name.  When the target generation renamed that field, the
    planner's own lookup finds nothing, reports "the new version has no such
    field", and the author's value is dropped even though the tape knows exactly
    where it belongs.  Measured on 209785 (8.4 -> 8.9): 54 author edits of
    `Creatable.HotKeyFromUnit` were classified as deleted fields while 8.9
    holds the same number one level down, at
    `Creatable.TrainLocations.0.HotKeyID` -- every one of them silently
    reverted to the official value.
    """
    pair = _SIMPLE_FOLD.get(name)
    return pair[0] if pair is not None else None


#: Fields the NEWER generation has and the older one cannot: there is no source
#: value to carry, so the tape has to write a number anyway -- and the number it
#: writes decides how the ported unit behaves.  Zero is a REAL value in every one
#: of these (graphic 0, icon 0, tooltip 0, frame 0, action 0), so "the source had
#: no such field" must not be answered with zero by reflex; each entry is the
#: value the official file actually uses.  Measured over all 90,190 Type50
#: records and 79,480 Creatable records of the installed 8.9 data:
#:
#:   Type50.FriendlyFireDamage          1.0   (90,064 of 90,190; 0.0 would mean
#:                                            the ported unit deals NO friendly
#:                                            fire, which is a gameplay change,
#:                                            not a default)
#:   Type50.InterruptFrame             -1     (88,492)
#:   Type50.AttackGraphic2             -1     (85,849)
#:   Creatable.IdleAttackGraphic       -1     (77,089)
#:   Creatable.ChargeProjectileUnit    -1     (78,094)
#:   Creatable.ButtonIconID            -1     (78,472)
#:   Creatable.ButtonShortTooltipID    -1     (78,472)
#:   Creatable.ButtonExtendedTooltipID -1     (78,472)
#:   Creatable.ButtonHotkeyAction      -1     (78,598)
#:
#: The rest of what 8.9 added really is zero: Type50.DamageReflection (90,190 of
#: 90,190), Creatable.ChargeTarget (77,653), Creatable.AttackPriority (79,165),
#: Creatable.InvulnerabilityLevel (79,354), Type50.GarrisonFirepower (70,156).
_ABSENT_DEFAULT = {
    "Type50.FriendlyFireDamage": (1.0, "f32"),
    "Type50.InterruptFrame": (-1, "i16"),
    "Type50.AttackGraphic2": (-1, "i16"),
    "Creatable.IdleAttackGraphic": (-1, "i16"),
    "Creatable.ChargeProjectileUnit": (-1, "i32"),
    "Creatable.ButtonIconID": (-1, "i16"),
    "Creatable.ButtonShortTooltipID": (-1, "i32"),
    "Creatable.ButtonExtendedTooltipID": (-1, "i32"),
    "Creatable.ButtonHotkeyAction": (-1, "i16"),
    # These five really are zero -- the official file's most common value is 0 on
    # every one (DamageReflection 90,190 of 90,190; ChargeTarget 77,653 of 79,480;
    # AttackPriority 79,165; InvulnerabilityLevel 79,354; GarrisonFirepower 70,156
    # of 90,190).  Listed anyway, so the report counts them as "8.9 added this and
    # its official value is 0" instead of "the tape gave up and wrote 0".
    "Type50.DamageReflection": (0.0, "f32"),
    "Type50.GarrisonFirepower": (0.0, "f32"),
    "Creatable.ChargeTarget": (0, "i16"),
    "Creatable.AttackPriority": (0, "u8"),
    "Creatable.InvulnerabilityLevel": (0.0, "f32"),
}


def _count_fold(t, probe):
    """`1` when the source really carries the single fixed slot `probe`.

    A count of 1 is the honest answer, not a guess: pre-count generations stored
    exactly one train location / research location, unconditionally, so any
    record whose replay reached the group has exactly one entry.  The probe
    guards the other case -- a record whose replay never reached the group at
    all (units below type 70 have no Creatable section) must not have a count
    invented for it.
    """
    return _synth(1, "i16") if probe in t.f else None


def _folded(t, name):
    """The rebuilt source slot for `name`, or None when there is no mapping."""
    pair = _SIMPLE_FOLD.get(name)
    if pair is not None:
        src, dflt, kind = pair
        slot = t.f.get(src)
        v = slot["value"] if slot else None
        return _synth(dflt if v is None else v, kind)
    if name == "Creatable.TrainLocationsCount":
        return _count_fold(t, "Creatable.TrainLocations.0.TrainTime")
    if name == "ResearchLocationCount":
        return _count_fold(t, "ResearchLocation")
    if name.startswith("Bird.Tasks.") and name.endswith(".Enabled"):
        # 8.9 added per-task `Enabled`; the official file writes -1 (enabled) on
        # every task of every record sampled (58,331 of them, Gaia 83/4 included).
        return _synth(-1, "i16")
    return None


class Tape(object):
    """A `unitfields.Rec`-shaped writer: reads by name, writes in call order.

    `fields` is what `UF.fields_at` / `TF.fields_at` returned for the source
    record.  Every accessor looks its name up there, appends the value in the
    format the TARGET generation uses, and returns the value so that the
    replay code can keep driving its own loops and guards.

    Three different things can happen to a name, and they are kept apart:

    `synth`   the source has the fact under another name (`_SIMPLE_FOLD`), or
              the target's count can be derived from the source's fixed slot.
              The value is CARRIED.
    `absent`  the source generation has no such field at all (`_ABSENT_DEFAULT`).
              A measured value is written, so the ported record behaves like an
              official one instead of behaving like zero.
    `missing` the tape could not find out -- neither table covers the name.  It
              writes 0 and says so, because a report that claims a clean port
              while zeroing a field is worse than the zero.

    Only `missing` means the number written is a guess.
    """

    __slots__ = ("f", "gv", "src", "base", "out", "missing", "idmap",
                 "mapped", "fields", "synth", "folded", "absent")

    def __init__(self, fields, gv, src=b"", idmap=None, base=0):
        self.f = fields or {}
        self.gv = gv
        self.src = src
        # The replay records absolute offsets (that is what `Rec` does), while
        # `src` is one record; `base` is where that record begins.
        self.base = base
        self.out = bytearray()
        self.missing = []
        self.idmap = idmap or {}
        self.mapped = 0
        # `_building` appends its LootingTable marker to `r.fields` directly.
        # The tape keeps the list so that call keeps working; nothing reads it.
        self.fields = []
        # Target-generation names this module rebuilt from their source-side
        # equivalent (see `_synth`).  Separate from `missing` because the value
        # is carried, not defaulted: 8.9's `Creatable.TrainLocationsCount` has no
        # 8.4 counterpart by name, yet 8.4's fixed slot-0 train location carries
        # exactly what it counts.
        self.synth = []
        # Multi-slot groups the target generation can only hold one of.  8.9
        # techs can name up to three research buildings; 8.4 has one
        # `ResearchLocation`.  Slot 0 survives and the rest are reported here
        # rather than silently dropped.
        self.folded = []
        # Target-generation names with NO source counterpart at all: 8.9 added
        # fields 8.4 never had.  They are written from `_ABSENT_DEFAULT`, a
        # measured value per field, so they are neither `missing` (the tape could
        # not find out and wrote 0) nor `synth` (a value was carried across).
        # Kept apart so a report can say which of the three actually happened.
        self.absent = []

    @property
    def pos(self):
        return len(self.out)

    # -- pull one value ------------------------------------------------------
    def _raw(self, name, kind):
        slot = self.f.get(name) if name else None
        if slot is None and name:
            slot = _folded(self, name)
            if slot is not None:
                self.synth.append(name)
        if slot is None and name:
            pair = _ABSENT_DEFAULT.get(name)
            if pair is not None:
                slot = _synth(pair[0], kind)
                self.absent.append(name)
        if slot is None:
            self.missing.append(name)
            return 0.0 if kind == "f32" else 0
        v = slot["value"]
        if v is None:
            return 0.0 if kind == "f32" else 0
        if kind != "f32" and self.idmap and name and is_id_field(name):
            new = self.idmap.get(int(v))
            if new is not None:
                self.mapped += 1
                return new
        return v

    def _put(self, name, kind):
        v = self._raw(name, kind)
        try:
            self.out += struct.pack(_FMT[kind], v)
        except struct.error:
            # Out of range for the target width.  Clamping is wrong (it
            # changes the value silently); the caller sees the name in
            # `missing` and the record is reported as not carried.
            self.missing.append("%s!range" % name)
            self.out += struct.pack(_FMT[kind], 0)
            return 0
        return v

    # -- the Rec surface, one method per call the replays make --------------
    def u8(self, name=None):
        return self._put(name, "u8")

    def i16(self, name=None):
        return self._put(name, "i16")

    def i32(self, name=None):
        return self._put(name, "i32")

    def u32(self, name=None):
        return self._put(name, "u32")

    def f32(self, name=None):
        return self._put(name, "f32")

    def i16_n(self, name, n):
        vals = []
        for i in range(n):
            if n == 1 and (name in self.f or _folded(self, name) is not None):
                slot = name
            else:
                slot = "%s.%d" % (name, i)
            vals.append(self._put(slot, "i16"))
        return vals

    def s(self, name):
        """Copy the string verbatim: marker, stored length, and the bytes.

        Re-encoding the text would be a lie twice over.  The stored bytes are
        whatever codepage the authoring tool used (the 310130 mod carries GBK
        unit names that decode to mojibake and would not survive a UTF-8
        round trip), and `parser.debug_string` trusts the length word, not the
        text, so the only faithful answer is the original run.
        """
        mk = self.f.get(name + ".marker")
        ln = self.f.get(name + ".len")
        if mk is None or ln is None:
            self.missing.append(name)
            self.out += struct.pack("<HH", P.DEBUG_STRING_MARKER, 0)
            return ""
        stored = int(ln["value"] or 0)
        body_at = int(ln["offset"]) + 2 - self.base
        body = self.src[body_at:body_at + stored]
        if len(body) != stored:
            self.missing.append(name + "!truncated")
            body = body + bytes(stored - len(body))
        self.out += struct.pack("<HH", int(mk["value"] or 0), stored) + body
        slot = self.f.get(name)
        return slot["value"] if slot else ""

    def skip(self, n):
        if n <= 0:
            return
        tail = self.src[-n:] if len(self.src) >= n else bytes(n)
        if len(tail) != n:
            tail = tail + bytes(n - len(tail))
        self.out += tail

    def debug_string(self):
        # Only reached if a replay calls it directly; `s()` is what the two
        # field readers use.
        self.missing.append("<debug_string>")
        self.out += struct.pack("<HH", P.DEBUG_STRING_MARKER, 0)
        return (P.DEBUG_STRING_MARKER, "")


def _note_truncated_slots(t, group, count_name, slots_to):
    """Record the slots a narrower target generation cannot hold.

    `gv >= 53` techs may name three research buildings and `gv >= 51` units may
    name any number of train locations; the generations below them hold exactly
    one.  Slot 0 survives, the rest are genuinely unrepresentable -- so they are
    listed here instead of vanishing, which is the difference between "the tool
    carried what it could" and "the tool quietly ate it".
    """
    if slots_to > 1:
        return
    try:
        n = int((t.f.get(count_name) or {}).get("value") or 0)
    except (TypeError, ValueError):
        return
    for i in range(max(0, n - 1)):
        t.folded.append("%s.%d" % (group, i + 1))


def encode_unit(src, start, end, gv_from, gv_to, idmap=None):
    """One unit record, re-laid-out for `gv_to`.  Returns `(bytes, tape)`."""
    fields = UF.fields_at(src, gv_from, start)
    t = Tape(fields, gv_to, src=src[start:end], idmap=idmap, base=start)
    UF.read_unit_fields(t)
    if gv_to < P.GV_C29:
        _note_truncated_slots(t, "Creatable.TrainLocations",
                              "Creatable.TrainLocationsCount", 1)
    return bytes(t.out), t


def encode_tech(src, start, end, gv_from, gv_to, idmap=None):
    """One technology record, re-laid-out for `gv_to`."""
    fields = TF.fields_at(src, gv_from, start)
    t = Tape(fields, gv_to, src=src[start:end], idmap=idmap, base=start)
    TF.read_tech_fields(t)
    if gv_to < P.GV_C31:
        _note_truncated_slots(t, "ResearchLocations",
                              "ResearchLocationCount", 1)
    return bytes(t.out), t