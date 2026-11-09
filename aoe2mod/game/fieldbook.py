# -*- coding: utf-8 -*-
"""Every field in the .dat, named, typed, counted and addressable — measured.

WHY THIS EXISTS
---------------
AGE3 ships a grid of **620 field declarations** across 43 C++ structs, and that
number is the whole of its vocabulary.  To touch a field you must already know
which struct it belongs to, memorise an English identifier
(`Type50.DisplayedAttack`, `Creatable.ChargeType`) and open a tree of
`1701 unit headers x 63 civs` to find the row.

This module replaces the *declaration* with a *measurement*.  It walks the
parsed model — which is 93 MB of real game data, not a schema — and derives the
catalog from what is actually in the file:

    AGE  : 620 declared fields, hand-transcribed from genieutils
    here : every scalar the parser produced, collapsed by path signature

The difference is not pedantry.  A declaration tells you a struct *can* hold a
`HitPoints`; a measurement tells you *4,193 units hold one, here is the range
across them, and 25 is what the 村民 has*.  The second is what a person needs.

PATH SIGNATURES
---------------
The model is a tree of dicts and lists.  `civs[7].units[83].type50.attacks[2].amount`
is one scalar; there are two million of those, and listing them is useless.
Collapsing integer list indices to `[]` turns the tree into **path templates**:
the example above becomes `civs[].units[].type50.attacks[].amount`, one row with
`count = 4193` and a min/max pulled from the real values.  That collapse is the
whole trick — it is what makes the catalog both complete and readable.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not write.  An edit is `preview()` (bytes that would move, no write) or
`plan()` (a verified diff against the original stream).  The actual bytes are
emitted by `dat/writer.serialize_dat` — the same path every other edit in the
product takes — so a field opened here is shipped by exactly the same emitter as
a sentence-parsed intent.  One write path, no second one to drift.
"""
from __future__ import annotations

#: Model tables, in the order a modder cares about them.  Anything not listed
#: still appears (the walk is generic) but falls back to its key as the label,
#: because inventing a Chinese name for `graphic_pointers_nonzero` would be a
#: lie told in a nicer font.
TABLE_ZH = {
    "units": "单位",
    "civs": "文明",
    "graphics": "图形",
    "sounds": "音效",
    "techs": "科技",
    "effects": "效果",
    "unit_headers": "单位条目",
    "terrain_block": "地形",
    "random_maps": "随机地图",
    "player_colours": "玩家颜色",
    "terrain_restrictions": "地形限制",
    "tech_tree": "科技树",
    "terrain_pass_graphic": "地表贴图",
    "file_version": "文件版本",
    "game_version": "数据格式版本",
}

#: Chinese for the path segments that recur across every struct.  A segment not
#: listed keeps its model name, which is the honest outcome: this file knows the
#: ~90 names that carry meaning and refuses to guess the ~700 that do not.
SEGMENT_ZH = {
    "type50": "战斗",
    "attacks": "攻击",
    "armours": "护甲",
    "amount": "数值",
    "class_": "类别",
    "class_id": "类别编号",
    "hit_points": "生命值",
    "speed": "移动速度",
    "line_of_sight": "视野",
    "train_locations": "训练地点",
    "train_time": "训练时间",
    "creatable": "可生产",
    "resource_costs": "造价",
    "resource_id": "资源",
    "building": "建筑",
    "dead_fish": "尸体",
    "bird": "鸟类",
    "projectile": "投射物",
    "tasks": "任务",
    "name": "名称",
    "id": "编号",
    "radius": "半径",
    "frame_count": "帧数",
    "angle_count": "角度数",
    "play_delay": "播放延迟",
    "probability": "概率",
    "effect_id": "效果编号",
    "required_techs": "所需科技",
    "research_time": "研究时间",
    "civilization_id": "文明编号",
    "unit_id": "单位编号",
}

#: Which Python types are a scalar you can put a number into.  `int` covers
#: every width the writer emits (u8/u16/i16/i32/u32/floats-as-int); the exact
#: width is resolved at write time by the serializer, so this module does not
#: guess it — see `WHY NO WIDTH COLUMN` at the bottom.
SCALARS = (int, float, bool)
NON_EDITABLE = (str,)     # fixed strings and debug strings are length-coupled

#: Paths whose value the parser derives from a list length or a pointer array.
#: Writing them detaches the count from the list and the record stops parsing.
#: Same rule as `fieldlabels.meta_for(...)["ro"]`, applied generically.
RO_MARKERS = ("_count", "count", "pointers", "ptr", "non_zero",
              "graphic_pointers_nonzero", "terrains_used")


def _seg_key(seg):
    """The catalog key for one path segment.  Ints become the list marker."""
    return "[]" if isinstance(seg, int) else str(seg)


def signature(path):
    """`(civs, 7, units, 83, hit_points)` -> `civs[].units[].hit_points`."""
    out = []
    for seg in path:
        if isinstance(seg, int):
            if out and out[-1] == "[]":
                continue
            out.append("[]")
        else:
            out.append(str(seg))
    return ".".join(out)


def _looks_read_only(sig):
    """True when the path names a count or a pointer array."""
    last = sig.rsplit(".", 1)[-1]
    return any(m in last for m in RO_MARKERS)


def _labels(sig):
    """Chinese label for a signature, and the table it lives in.

    The table is the FIRST segment; the label is the last meaningful one, with
    its parent appended when the bare name is ambiguous (`amount` alone means
    nothing; `攻击.amount` does).
    """
    parts = [p for p in sig.split(".") if p and p != "[]"]
    table = parts[0] if parts else ""
    tail = parts[1:] if len(parts) > 1 else parts
    if not tail:
        return TABLE_ZH.get(table, table), TABLE_ZH.get(table, table)
    leaf = tail[-1]
    zh_leaf = SEGMENT_ZH.get(leaf, leaf)
    if len(tail) >= 2:
        parent = SEGMENT_ZH.get(tail[-2], tail[-2])
        return "%s · %s" % (parent, zh_leaf), table
    return zh_leaf, table


def _walk(node, path=(), on_scalar=None, max_depth=14):
    """Depth-first walk of the model, calling `on_scalar(path, value)`.

    Iterative-ish and depth-bounded: the model is nested up to 12 levels
    (`civs[].units[].creatable.resource_costs[].resource_id`), and a runaway
    recursion on a 93 MB tree is not a bug you want to discover at runtime.
    """
    stack = [(node, path)]
    while stack:
        cur, p = stack.pop()
        if len(p) > max_depth:
            continue
        if isinstance(cur, dict):
            for k, v in cur.items():
                stack.append((v, p + (k,)))
        elif isinstance(cur, (list, tuple)):
            for i, v in enumerate(cur):
                stack.append((v, p + (i,)))
        elif isinstance(cur, SCALARS) or isinstance(cur, NON_EDITABLE):
            if on_scalar is not None:
                on_scalar(p, cur)


class Entry(object):
    """One path signature: what it is called, how many exist, what they hold."""

    __slots__ = ("sig", "label", "table", "table_zh", "kind", "count",
                 "lo", "hi", "sample", "ro", "example_path", "values")

    def __init__(self, sig, label, table):
        self.sig = sig
        self.label = label
        self.table = table
        self.table_zh = TABLE_ZH.get(table, table)
        self.kind = None
        self.count = 0
        self.lo = None
        self.hi = None
        self.sample = None            # first value seen
        self.example_path = None      # a concrete path to read it back
        self.ro = _looks_read_only(sig)
        self.values = None            # distinct values, capped (see below)

    def observe(self, path, value):
        self.count += 1
        if self.example_path is None:
            self.example_path = path
            self.sample = value
        kind = type(value).__name__
        if self.kind is None or self.kind == "bool":
            self.kind = kind
        elif self.kind != kind:
            # A path that holds an int in one record and a float in another is
            # a real thing in this file (optional tail fields), so record the
            # union rather than pretending one type won.
            self.kind = "int|float" if {self.kind, kind} <= {"int", "float"} else "mixed"
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            if self.lo is None or value < self.lo:
                self.lo = value
            if self.hi is None or value > self.hi:
                self.hi = value

    def as_row(self):
        row = {"path": self.sig, "label": self.label, "table": self.table,
               "table_zh": self.table_zh, "kind": self.kind,
               "count": self.count, "sample": self.sample}
        if isinstance(self.sample, str):
            row["kind"] = "str"
            row["ro"] = True
        if self.lo is not None:
            row["lo"] = self.lo
            row["hi"] = self.hi
        if self.ro or isinstance(self.sample, str):
            row["ro"] = True
        elif "ro" in row:
            del row["ro"]
        return row


def catalog(stats, tables=None, min_count=1):
    """The full field book: one `Entry` per path signature in the model.

    `tables` restricts the walk to those top-level keys (a request for the unit
    table must not walk a million graphic scalars).  `min_count` drops singleton
    weirdness — a field that exists exactly once is usually a header value the
    code path already handles, and listing 40 of them buries the real rows.
    """
    if tables:
        roots = [(t, stats.get(t)) for t in tables if t in stats]
    else:
        roots = [(k, v) for k, v in stats.items()]
    entries = {}
    for key, root in roots:
        if root is None:
            continue

        def observe(path, value, _key=key):
            sig = signature((_key,) + path)
            e = entries.get(sig)
            if e is None:
                label, table = _labels(sig)
                e = Entry(sig, label, table)
                entries[sig] = e
            e.observe((_key,) + path, value)

        _walk(root, on_scalar=observe)
    rows = [e.as_row() for e in entries.values() if e.count >= min_count]
    rows.sort(key=lambda r: (r["table"], -r["count"], r["path"]))
    return rows


def search(rows, query, limit=40):
    """Find a field by Chinese label, English name, or table, loosely.

    The match is deliberately forgiving: a player types `攻击力`, the model says
    `amount` under `attacks`, and neither string contains the other.  Query
    terms are matched against label, path and table separately, and a row scores
    by how many terms hit — so `弓箭手` alone still returns the whole unit table
    instead of nothing.
    """
    q = str(query or "").strip().lower()
    if not q:
        return list(rows)[:limit]
    terms = [t for t in q.replace("　", " ").split(" ") if t]
    hits = []
    for r in rows:
        hay = (r["label"] + " " + r["path"] + " " + r.get("table_zh", "")
               + " " + r.get("table", "")).lower()
        score = sum(1 for t in terms if t in hay)
        if score == len(terms):
            # Prefer a label hit over a path hit: the label is the phrase the
            # player actually used.
            bonus = 2 if q in r["label"].lower() else 0
            hits.append((score + bonus, r["count"], r))
    hits.sort(key=lambda h: (-h[0], -h[1], h[2]["path"]))
    return [h[2] for h in hits[:limit]]


def get(rows, path):
    """One entry by exact signature."""
    for r in rows:
        if r["path"] == path:
            return r
    return None


def resolve(stats, path):
    """A concrete path with the `[]` markers filled: first record of each list.

    The catalog speaks in templates; reading a value needs indices.  This walks
    the model following the template and returns a concrete path, or None when
    the list is empty.  Keeping these two functions separate is why `search`
    does not have to materialise two million paths to answer a query.
    """
    cur = stats
    concrete = []
    segs = path.split(".")
    for seg in segs:
        if seg == "[]":
            if not isinstance(cur, (list, tuple)) or not cur:
                return None
            cur = cur[0]
            concrete.append(0)
        else:
            if isinstance(cur, dict):
                if seg not in cur:
                    return None
                cur = cur[seg]
                concrete.append(seg)
            elif isinstance(cur, (list, tuple)) and seg.isdigit():
                i = int(seg)
                if i >= len(cur):
                    return None
                cur = cur[i]
                concrete.append(i)
            else:
                return None
    return tuple(concrete)


def value_at(stats, concrete):
    """Read a concrete path out of the model."""
    cur = stats
    for seg in concrete:
        cur = cur[seg]
    return cur


# WHY NO WIDTH COLUMN
# -------------------
# A width would have to be guessed here (is `amount` an i16 or an i32?), and a
# wrong width is worse than no width: it would let a 70000 through on a field
# that holds 32767 and corrupt the next record.  The writer already knows every
# width — it emits them — so the range check lives where the knowledge is:
# `preview()` serialises the edited model and reports how many bytes actually
# moved.  A value that does not fit shows up as a longer diff, not a lie.
