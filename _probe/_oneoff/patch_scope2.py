"""One-off: thread the civilization scope through the unit-field resolvers.

Every function that walks `s810.civs` has to take the same scope, or the pieces
of one edit disagree about which civilizations they touch: the primary write list
would be scoped while the mirror pass still moved all 63, and the screen would
report one number while the file held another.
"""
import io

# --- unitfield.rs -------------------------------------------------------------
p = 'desktop/aoe2mod-serve/src/unitfield.rs'
s = io.open(p, encoding='utf-8').read()

# cost_targets
old = '''pub fn cost_targets(
    s810: &Stages810,
    family: &[i16],'''
new = '''pub fn cost_targets(
    s810: &Stages810,
    family: &[i16],
    wanted: &Option<Vec<String>>,'''
assert s.count(old) == 1, 'cost_targets signature'
s = s.replace(old, new, 1)

# damage_targets
old = '''pub fn damage_targets(
    s810: &Stages810,
    family: &[i16],'''
new = '''pub fn damage_targets(
    s810: &Stages810,
    family: &[i16],
    wanted: &Option<Vec<String>>,'''
assert s.count(old) == 1, 'damage_targets signature'
s = s.replace(old, new, 1)

# stat_mirrors
old = '''pub fn stat_mirrors(s810: &Stages810, family: &[i16], stat: &str) -> Vec<MirrorHit> {'''
new = '''pub fn stat_mirrors(
    s810: &Stages810,
    family: &[i16],
    stat: &str,
    wanted: &Option<Vec<String>>,
) -> Vec<MirrorHit> {'''
assert s.count(old) == 1, 'stat_mirrors signature'
s = s.replace(old, new, 1)

# All three loop bodies open the same way; scope each of them.
LOOP = '''    for (ci, c) in s810.civs.iter().enumerate() {
        for u in c.units.iter() {
            if !family.contains(&u.id) {'''
SCOPED = '''    for (ci, c) in s810.civs.iter().enumerate() {
        if !civ_in_scope(&c.name, wanted) {
            continue;
        }
        for u in c.units.iter() {
            if !family.contains(&u.id) {'''
n = s.count(LOOP)
assert n == 3, 'expected 3 civilisational loops in unitfield.rs, found %d' % n
s = s.replace(LOOP, SCOPED)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('unitfield.rs: signatures + %d loops scoped' % n)

# --- stat_edit.rs ------------------------------------------------------------
p = 'desktop/aoe2mod-serve/src/stat_edit.rs'
s = io.open(p, encoding='utf-8').read()

# apply(): the mirror pass
old = '''    let mirrors = crate::unitfield::stat_mirrors(&s810, &family, stat);'''
n = s.count(old)
assert n == 2, 'stat_mirrors calls: %d' % n
s = s.replace(old, '''    let mirrors = crate::unitfield::stat_mirrors(&s810, &family, stat, wanted);''')
# build_one computes `wanted` a few lines above its own call, `apply` gets it as a
# parameter.  The substitution above is correct for both because both name it
# `wanted`.

# build_unit_field: resolve() needs the scope, so the closure grows a parameter.
old = '''    resolve: impl FnOnce(
        &aoe2mod_dat::stage810::Stages810,
        &[i16],
        i16,
    ) -> Result<crate::unitfield::Resolved, String>,'''
new = '''    resolve: impl FnOnce(
        &aoe2mod_dat::stage810::Stages810,
        &[i16],
        i16,
        &Option<Vec<String>>,
    ) -> Result<crate::unitfield::Resolved, String>,'''
assert s.count(old) == 1, 'build_unit_field signature'
s = s.replace(old, new, 1)

old = '''    let family = family_ids(unit);
    let resolved = resolve(&s810, &family, unit)?;'''
new = '''    let family = family_ids(unit);
    // Same scope as the two byte-patch paths: `/api/build`, `/api/stat` and the
    // preview all have to touch the same civilizations for the same sentence.
    let wanted = civ_filter(req);
    let resolved = resolve(&s810, &family, unit, &wanted)?;'''
assert s.count(old) == 1, 'resolve call'
s = s.replace(old, new, 1)

# The two closures passed to build_unit_field.
old = '''    build_unit_field(server, req, |s810, family, unit| {
        crate::unitfield::cost_targets(s810, family, &resource, unit)
    })'''
new = '''    build_unit_field(server, req, |s810, family, unit, wanted| {
        crate::unitfield::cost_targets(s810, family, wanted, &resource, unit)
    })'''
assert s.count(old) == 1, 'cost closure'
s = s.replace(old, new, 1)

old = '''    build_unit_field(server, req, |s810, family, unit| {
        crate::unitfield::damage_targets(s810, family, &kind, &classes, unit)
    })'''
new = '''    build_unit_field(server, req, |s810, family, unit, wanted| {
        crate::unitfield::damage_targets(s810, family, wanted, &kind, &classes, unit)
    })'''
assert s.count(old) == 1, 'damage closure'
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('stat_edit.rs: closures + mirror calls scoped')
