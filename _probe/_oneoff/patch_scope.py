"""One-off: add the civilization filter to both target loops in stat_edit.rs.

There are two loops with the same body: `apply` (the `/api/stat` live-preview
path, around line 81) and `build_one` (the `/api/build` path, around line 278).
They must scope identically or the preview and the build describe different
edits -- the exact disagreement this project has paid for repeatedly.

`apply` takes a value and has no request object, so it takes an extra parameter.
"""
import io

p = 'desktop/aoe2mod-serve/src/stat_edit.rs'
s = io.open(p, encoding='utf-8').read()

LOOP = '''    let mut targets = Vec::new();
    for (ci, c) in s810.civs.iter().enumerate() {
        for u in c.units.iter() {
            if !family.contains(&u.id) {
                continue;
            }
            if let Some(off) = table.offset(ci, stat, u.id) {
                targets.push((ci, off));
            }
        }
    }'''

SCOPED = '''    let mut targets = Vec::new();
    let mut seen_civ = false;
    for (ci, c) in s810.civs.iter().enumerate() {
        if !civ_in_scope(&c.name, wanted) {
            continue;
        }
        seen_civ = true;
        for u in c.units.iter() {
            if !family.contains(&u.id) {
                continue;
            }
            if let Some(off) = table.offset(ci, stat, u.id) {
                targets.push((ci, off));
            }
        }
    }
    // "matched no civilization" and "the civilization has no such unit" are
    // different failures. Reporting the second for the first sends the player to
    // look for the wrong problem, so the name is checked before the unit is.
    if !seen_civ {
        let names = wanted.cloned().unwrap_or_default();
        return Err(format!("认不出「{}」是哪个文明", names.join("、")));
    }'''

assert s.count(LOOP) == 2, 'found %d copies' % s.count(LOOP)
s = s.replace(LOOP, SCOPED)

# `apply` signature gains the scope.
old_sig = '''pub fn apply(server: &Server, stat: &str, unit: i16, value: f64) -> Result<String, String> {'''
new_sig = '''pub fn apply(
    server: &Server,
    stat: &str,
    unit: i16,
    value: f64,
    wanted: &Option<Vec<String>>,
) -> Result<String, String> {'''
assert s.count(old_sig) == 1
s = s.replace(old_sig, new_sig, 1)

# `build_one` computes its scope right before the loop it now uses.
old_fam = '''    let family = family_ids(unit);
    let mut targets = Vec::new();'''
new_fam = '''    let family = family_ids(unit);
    let wanted = civ_filter(req);
    let mut targets = Vec::new();'''
count = s.count(old_fam)
assert count == 2, 'family expansion appears %d times' % count
# The first occurrence is inside `apply`, which has no `req`.
i = s.index(old_fam)
s = s[:i] + '    let family = family_ids(unit);\n    let mut targets = Vec::new();' + s[i + len(old_fam):]
j = s.index(old_fam, i + 10)
s = s[:j] + new_fam + s[j + len(old_fam):]

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched both loops')
