"""Give every builder a `dry` mode, so the preview runs the BUILD, not a copy.

The preview has to say how many places an edit would touch.  If it recomputed
that number its own way, the two would drift and the page would promise work the
build does not do -- the shape this project has paid for repeatedly (`edit_count`
was 1701 in the build and 1 in the preview attempt).

So: one code path.  A request with `"dry": true` runs the same resolution, the
same family expansion, the same mirror lookup, and stops right before the first
write to disk, returning the same report minus the artefact.

Each builder already assembles its report in one `format!` at the end.  This
splits that into a `head` (everything computed) and a tail (the artefact), so
there is still only ONE copy of the numbers.
"""
import io
import re
import sys

P = 'desktop/aoe2mod-serve/src/stat_edit.rs'
s = io.open(P, encoding='utf-8').read()
before = s

# ---- the predicate, next to the other request helpers -----------------------
anchor = '/// Every record id that an edit named after `unit` has to touch.'
assert s.count(anchor) == 1
s = s.replace(anchor, '''/// "Tell me what you would do; change nothing."
///
/// The preview calls the builders with this set so it reports the build's own
/// numbers instead of a second calculation.  Every builder honours it at exactly
/// one place: the line before it creates the mod folder.
pub fn is_dry(req: &serde_json::Value) -> bool {
    req.get("dry").and_then(|v| v.as_bool()).unwrap_or(false)
}

''' + anchor, 1)

# ---- build_one --------------------------------------------------------------
old = '''    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{stat} {unit} -> {new_value}"),
        true,
    )?;'''
new = '''    let head = format!(
        "{{\\"ok\\":true,\\"stat\\":\\"{}\\",\\"unit\\":{},\\"civs\\":{},\\"variants\\":{},\\"edit_count\\":{},\\"mirror_count\\":{},\\"before\\":{},\\"value\\":{}",
        crate::server::json_escape(stat),
        unit,
        civ_count(&targets),
        family.len(),
        targets.len() + mirrors.len(),
        mirrors.len(),
        old,
        new_value
    );
    if is_dry(req) {
        return Ok(format!("{head},\\"dry\\":true,\\"dat_bytes\\":0,\\"compressed\\":0,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{stat} {unit} -> {new_value}"),
        true,
    )?;'''
assert s.count(old) == 1, 'build_one head'
s = s.replace(old, new, 1)

# build_one's tail: reuse `head`.
old = '''    Ok(format!(
        "{{\\"ok\\":true,\\"stat\\":\\"{}\\",\\"unit\\":{},\\"civs\\":{},\\"variants\\":{},\\"edit_count\\":{},\\"mirror_count\\":{},\\"before\\":{},\\"value\\":{},\\"dat_bytes\\":{},\\"compressed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        crate::server::json_escape(stat),
        unit,
        // Distinct civilizations, not writes.  `targets.len()` used to be
        // reported here under the name `civs`, which after family expansion says
        // 1701 civilizations exist.  The two numbers answer different questions
        // and the reference calls them `civ_count` and `edit_count`.
        civ_count(&targets),
        family.len(),
        targets.len() + mirrors.len(),
        mirrors.len(),
        old,
        new_value,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
new = '''    // Distinct civilizations, not writes: `targets.len()` under the name `civs`
    // says 1701 civilizations exist after family expansion.  The two numbers
    // answer different questions and the reference calls them `civ_count` and
    // `edit_count`.
    Ok(format!(
        "{head},\\"dat_bytes\\":{},\\"compressed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
assert s.count(old) == 1, 'build_one tail'
s = s.replace(old, new, 1)

# ---- build_unit_field ------------------------------------------------------
old = '''    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{} {unit} -> {new_value}", resolved.label),
        true,
    )?;'''
new = '''    let head = format!(
        "{{\\"ok\\":true,\\"intent\\":\\"{}\\",\\"unit\\":{},\\"field\\":\\"{}\\",\\"civs\\":{},\\"variants\\":{},\\"edit_count\\":{},\\"before\\":{},\\"value\\":{}",
        crate::server::json_escape(intent),
        unit,
        crate::server::json_escape(&resolved.label),
        resolved.civ_count(),
        family.len(),
        resolved.hits.len(),
        resolved.before,
        new_value
    );
    if is_dry(req) {
        return Ok(format!("{head},\\"dry\\":true,\\"dat_bytes\\":0,\\"compressed\\":0,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{} {unit} -> {new_value}", resolved.label),
        true,
    )?;'''
assert s.count(old) == 1, 'unit_field head'
s = s.replace(old, new, 1)

old = '''    Ok(format!(
        "{{\\"ok\\":true,\\"intent\\":\\"{}\\",\\"unit\\":{},\\"field\\":\\"{}\\",\\"civs\\":{},\\"variants\\":{},\\"edit_count\\":{},\\"before\\":{},\\"value\\":{},\\"dat_bytes\\":{},\\"compressed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        crate::server::json_escape(intent),
        unit,
        crate::server::json_escape(&resolved.label),
        resolved.civ_count(),
        family.len(),
        resolved.hits.len(),
        resolved.before,
        new_value,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
new = '''    Ok(format!(
        "{head},\\"dat_bytes\\":{},\\"compressed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
assert s.count(old) == 1, 'unit_field tail'
s = s.replace(old, new, 1)

# ---- build_tech -----------------------------------------------------------
old = '''    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{intent} {tech} -> {new_value}"),
        true,
    )?;'''
new = '''    let head = format!(
        "{{\\"ok\\":true,\\"intent\\":\\"{}\\",\\"tech\\":{},\\"locations\\":{},\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{}",
        crate::server::json_escape(intent),
        tech,
        offsets.len(),
        old,
        new_value,
        diffs
    );
    if is_dry(req) {
        return Ok(format!("{head},\\"dry\\":true,\\"dat_bytes\\":0,\\"compressed\\":0,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("{intent} {tech} -> {new_value}"),
        true,
    )?;'''
assert s.count(old) == 1, 'tech head'
s = s.replace(old, new, 1)

old = '''    Ok(format!(
        "{{\\"ok\\":true,\\"intent\\":\\"{}\\",\\"tech\\":{},\\"locations\\":{},\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        crate::server::json_escape(intent),
        tech,
        offsets.len(),
        old,
        new_value,
        diffs,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
new = '''    Ok(format!(
        "{head},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
assert s.count(old) == 1, 'tech tail'
s = s.replace(old, new, 1)

# ---- build_effect --------------------------------------------------------
old = '''    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("effect {effect_id} cmd {command} {field} -> {new_value}"),
        true,
    )?;'''
new = '''    let head = format!(
        "{{\\"ok\\":true,\\"tech\\":{},\\"effect\\":{},\\"command\\":{},\\"field\\":\\"{}\\",\\"field_kind\\":\\"{}\\",\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{}",
        tech,
        effect_id,
        command,
        crate::server::json_escape(&field),
        kind_name,
        old,
        new_value,
        diffs
    );
    if is_dry(req) {
        return Ok(format!("{head},\\"dry\\":true,\\"dat_bytes\\":0,\\"compressed\\":0,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("effect {effect_id} cmd {command} {field} -> {new_value}"),
        true,
    )?;'''
assert s.count(old) == 1, 'effect head'
s = s.replace(old, new, 1)

old = '''    Ok(format!(
        "{{\\"ok\\":true,\\"tech\\":{},\\"effect\\":{},\\"command\\":{},\\"field\\":\\"{}\\",\\"field_kind\\":\\"{}\\",\\"before\\":{},\\"value\\":{},\\"bytes_changed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        tech,
        effect_id,
        command,
        crate::server::json_escape(&field),
        kind_name,
        old,
        new_value,
        diffs,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
new = '''    Ok(format!(
        "{head},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
assert s.count(old) == 1, 'effect tail'
s = s.replace(old, new, 1)

# ---- build_card_move -----------------------------------------------------
old = '''    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();
    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("card {building}: unit {unit} -> box {target}"),
        true,
    )?;'''
new = '''    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();
    let moved: Vec<String> = report
        .moved
        .iter()
        .map(|(u, from, to)| format!("{{\\"unit\\":{u},\\"from\\":{from},\\"to\\":{to}}}"))
        .collect();
    let head = format!(
        "{{\\"ok\\":true,\\"building\\":{},\\"offset\\":{},\\"before\\":{},\\"after\\":{},\\"moved\\":[{}],\\"bytes_changed\\":{}",
        building,
        report.offset,
        report.before,
        report.after,
        moved.join(","),
        diffs
    );
    if is_dry(req) {
        return Ok(format!("{head},\\"dry\\":true,\\"dat_bytes\\":0,\\"compressed\\":0,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("card {building}: unit {unit} -> box {target}"),
        true,
    )?;'''
assert s.count(old) == 1, 'card_move head'
s = s.replace(old, new, 1)

old = '''    let moved: Vec<String> = report
        .moved
        .iter()
        .map(|(u, from, to)| format!("{{\\"unit\\":{u},\\"from\\":{from},\\"to\\":{to}}}"))
        .collect();
    Ok(format!(
        "{{\\"ok\\":true,\\"building\\":{},\\"offset\\":{},\\"before\\":{},\\"after\\":{},\\"moved\\":[{}],\\"bytes_changed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        building,
        report.offset,
        report.before,
        report.after,
        moved.join(","),
        diffs,
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
new = '''    Ok(format!(
        "{head},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
assert s.count(old) == 1, 'card_move tail'
s = s.replace(old, new, 1)

# ---- build_sprite --------------------------------------------------------
old = '''    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("sprite rename: {touched} records"),
        true,
    )?;'''
new = '''    let head = format!(
        "{{\\"ok\\":true,\\"intent\\":\\"unit.sprite\\",\\"mode\\":\\"rename\\",\\"records\\":{touched}"
    );
    if is_dry(req) {
        return Ok(format!("{head},\\"dry\\":true,\\"dat_bytes\\":0,\\"compressed\\":0,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &format!("sprite rename: {touched} records"),
        true,
    )?;'''
assert s.count(old) == 1, 'sprite head'
s = s.replace(old, new, 1)

old = '''    Ok(format!(
        "{{\\"ok\\":true,\\"intent\\":\\"unit.sprite\\",\\"mode\\":\\"rename\\",\\"records\\":{},\\"dat_bytes\\":{},\\"compressed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        touched,
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
new = '''    Ok(format!(
        "{head},\\"dat_bytes\\":{},\\"compressed\\":{},\\"built\\":\\"{}\\",\\"installed\\":\\"{}\\"}}",
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))'''
assert s.count(old) == 1, 'sprite tail'
s = s.replace(old, new, 1)

# ---- build_toggle_group --------------------------------------------------
old = '''    let out_dir = std::env::temp_dir()
        .join("aoe2mod-native-build")
        .join(&title);
    if out_dir.exists() {'''
new = '''    let out_dir = std::env::temp_dir()
        .join("aoe2mod-native-build")
        .join(&title);
    if is_dry(req) {
        // The JSON layer is the whole edit, and it is refused or accepted by
        // `add_group` -- so the preview has to run it, not guess.  Run it against
        // a COPY of the document and throw the copy away.
        let src = root.join("resources/_common/dat/linkedTechs.json");
        let text = std::fs::read_to_string(&src)
            .map_err(|e| format!("读不到 {}：{e}", src.display()))?;
        let mut doc: serde_json::Value = serde_json::from_str(text.trim_start_matches('\\u{feff}'))
            .map_err(|e| format!("{} 不是合法 JSON：{e}", src.display()))?;
        let entry = crate::togglegroup::add_group(&mut doc, &techs)?;
        let total = doc
            .get("LinkedTechs")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0);
        return Ok(format!(
            "{{\\"ok\\":true,\\"intent\\":\\"tech.toggle_group\\",\\"entry\\":{},\\"entries\\":{},\\"files\\":2,\\"dry\\":true,\\"built\\":\\"\\",\\"installed\\":\\"\\"}}",
            entry, total
        ));
    }
    if out_dir.exists() {'''
assert s.count(old) == 1, 'toggle head'
s = s.replace(old, new, 1)

assert s != before
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('stat_edit.rs: dry mode in all seven builders')
