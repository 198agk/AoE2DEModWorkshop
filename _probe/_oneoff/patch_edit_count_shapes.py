"""Give every builder an `edit_count`.

`preview.rs` reads `edit_count` off the builder's report (`num("edit_count")`).
Only the unit-family shapes emitted it, so a tech/sprite/toggle/card sentence
previewed as "0 处改动" while the build actually wrote bytes -- the page then
prints a card that promises nothing.

Measured against the reference (`dump_ref_plans.py`):
  tech.research_time  织布机研究时间 -5    edit_count 1   <- one location
  tech.cost           织布机黄金成本 -10   edit_count 1
  tech.effect         织布机第1条效果改成100 edit_count 1
  tech.toggle_group   两个科技做成互斥       edit_count 1
  unit.sprite         村民→绵羊             edit_count 20 (= records)
  unit.card_move      把民兵放在第5格        plan empty, but the move is 1

Each count is the number of separate places the edit lands, which is what the
sentence "N 处改动" means.  The numbers already exist in each report; this only
names them the way the preview looks for them.
"""
import io

ROOT = "D:/Software/AI/帝国项目/"
P = ROOT + "desktop/aoe2mod-serve/src/stat_edit.rs"
s = io.open(P, encoding="utf-8").read()
orig = s


def sub(old, new, what):
    global s
    n = s.count(old)
    assert n == 1, "%s: expected 1, found %d" % (what, n)
    s = s.replace(old, new, 1)


# tech.research_time / tech.cost: one row per research location.
sub(
    '''        "{{\\"ok\\":true,\\"intent\\":\\"{}\\",\\"tech\\":{},\\"locations\\":{},\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{}",
        crate::server::json_escape(intent),
        tech,
        offsets.len(),
        old,
        new_value,
        diffs
    );''',
    '''        "{{\\"ok\\":true,\\"intent\\":\\"{}\\",\\"tech\\":{},\\"locations\\":{},\\"edit_count\\":{},\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{}",
        crate::server::json_escape(intent),
        tech,
        offsets.len(),
        // Every copy is written, so the reach IS the location count.  A tech
        // with one location says "1 处", which is what the reference says.
        offsets.len(),
        old,
        new_value,
        diffs
    );''',
    "tech edit_count",
)

# tech.effect: one command, one field.
sub(
    '''        "{{\\"ok\\":true,\\"tech\\":{},\\"effect\\":{},\\"command\\":{},\\"field\\":\\"{}\\",\\"field_kind\\":\\"{}\\",\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{}",
        tech,
        effect_id,
        command,''',
    '''        "{{\\"ok\\":true,\\"tech\\":{},\\"effect\\":{},\\"command\\":{},\\"edit_count\\":1,\\"field\\":\\"{}\\",\\"field_kind\\":\\"{}\\",\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{}",
        tech,
        effect_id,
        command,''',
    "effect edit_count",
)

# unit.sprite: one per renamed record.
sub(
    '''        "{{\\"ok\\":true,\\"intent\\":\\"unit.sprite\\",\\"mode\\":\\"rename\\",\\"records\\":{touched}"''',
    '''        "{{\\"ok\\":true,\\"intent\\":\\"unit.sprite\\",\\"mode\\":\\"rename\\",\\"records\\":{touched},\\"edit_count\\":{touched}"''',
    "sprite edit_count",
)

# tech.toggle_group: one linkedTechs entry, however many members it names.
sub(
    '''        "{{\\"ok\\":true,\\"intent\\":\\"tech.toggle_group\\",\\"entry\\":{},\\"entries\\":{},\\"files\\":2,\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        entry,
        total,''',
    '''        // One entry, not one per member: the array it lands in is keyed by
        // group, and 「2 项做成一组」 changes that array once.  The reference
        // reports edit_count 1 for the same sentence.
        "{{\\"ok\\":true,\\"intent\\":\\"tech.toggle_group\\",\\"entry\\":{},\\"entries\\":{},\\"edit_count\\":1,\\"files\\":2,\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        entry,
        total,''',
    "toggle edit_count",
)

# unit.card_move: however many units actually moved.
sub(
    '''        "{{\\"ok\\":true,\\"building\\":{},\\"offset\\":{},\\"before\\":{},\\"after\\":{},\\"moved\\":[{}],\\"bytes_changed\\":{}",
        building,
        report.offset,
        report.before,
        report.after,
        moved.join(","),
        diffs
    );''',
    '''        "{{\\"ok\\":true,\\"building\\":{},\\"offset\\":{},\\"before\\":{},\\"after\\":{},\\"moved\\":[{}],\\"edit_count\\":{},\\"bytes_changed\\":{}",
        building,
        report.offset,
        report.before,
        report.after,
        moved.join(","),
        // A move that rearranged nothing is still one card slot changed, but
        // reporting 0 would read as "nothing will happen" for a sentence that
        // does something.  The moved list already tells the true story.
        report.moved.len().max(1),
        diffs
    );''',
    "card_move edit_count",
)

assert s != orig
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("edit_count added to five builders")
