//! Apply a stat edit through the offset table, and report exactly what moved.

use crate::server::{json_escape, Server};
use aoe2mod_dat::stats::{StatKind, StatTable};
use aoe2mod_dat::writer::Writer;
use aoe2mod_dat::write23::{write_stage1, write_stages23};
use aoe2mod_dat::write47::write_stages47;
use aoe2mod_dat::write810::write_stages810;
use aoe2mod_dat::{
    load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
};

/// "Tell me what you would do; change nothing."
///
/// The preview calls the builders with this set so it reports the build's own
/// numbers instead of a second calculation.  Every builder honours it at exactly
/// one place: the line before it creates the mod folder.
/// The mod's `Description`, taken from the request.
///
/// The reference engine does not invent one: `aoe2mod/ui/server.py:898` reads
/// `payload.get("description") or ""` and writes whatever it got, empty
/// included.  This side used to synthesise a line per builder
/// (`"hp 74 -> 100"`), which meant the same intent produced a different
/// `info.json` depending on WHO built it -- the byte-comparison gate caught it
/// as ten of eleven cases differing in exactly this file.  A description is the
/// player's text; deriving it from the numbers that already appear in the
/// manifest's own intents adds a second, weaker copy of the same facts.
///
/// It is also used for `remember_build`, so the build record and the shipped
/// `info.json` cannot disagree about what was asked for.
fn description_of(req: &serde_json::Value) -> String {
    req.get("description")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string()
}

pub fn is_dry(req: &serde_json::Value) -> bool {
    req.get("dry").and_then(|v| v.as_bool()).unwrap_or(false)
}

/// Every record id that an edit named after `unit` has to touch.
///
/// Reads the exported family table, so the preview and the build answer this
/// question from one source.  A missing table is not fatal: the fallback is the
/// one-member family, which is correct for every lone unit and is what this
/// server did before the table existed.
fn family_ids(unit: i16) -> Vec<i16> {
    let path = crate::families::table_path();
    match crate::families::Families::load(&path) {
        Ok(f) => f.of(unit),
        Err(_) => vec![unit],
    }
}

/// Which civilizations a request scopes the edit to.
///
/// `None` means every civilization, which is the default and the only reading
/// available when the sentence names none.  A named civilization narrows the
/// write list, and the two must never be conflated: 「不列颠村民血量改成100」
/// that writes all 63 records reports `civ_count: 63` and looks like a success
/// while it edits sixty-two civilizations nobody asked about.
///
/// The spellings are the .dat's own (`British`), which is what the sentence
/// layer stores; matching is case-insensitive because a sentence may write
/// `BRITONS` and the file writes `Britons`.
fn civ_filter(req: &serde_json::Value) -> Option<Vec<String>> {
    let arr = req.get("civs").and_then(|v| v.as_array())?;
    let words: Vec<String> = arr
        .iter()
        .filter_map(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();
    if words.is_empty() {
        None
    } else {
        Some(words)
    }
}

/// The intent a build record keeps, so that a later rebuild reproduces THIS
/// edit and not a wider one.
///
/// `civs` was left out of the record the first time round.  Rebuilding
/// 「不列颠村民血量改成100」 then replayed an intent with no scope and silently
/// widened the mod to all 63 civilizations -- the file existed, the count was
/// plausible, and the edit that came back was not the edit that was asked for.
fn recorded_intent(fields: serde_json::Value, req: &serde_json::Value) -> serde_json::Value {
    let mut obj = match fields {
        serde_json::Value::Object(m) => m,
        _ => serde_json::Map::new(),
    };
    if let Some(c) = req.get("civs") {
        if !c.is_null() {
            obj.insert("civs".to_string(), c.clone());
        }
    }
    serde_json::json!([serde_json::Value::Object(obj)])
}

/// Whether a civilisation record is in scope.
///
/// A name that matches nothing is a REFUSAL at the call site, not a silent empty
/// list: an edit that writes zero bytes and reports success is worse than one
/// that says the name was not recognised.
pub(crate) fn civ_in_scope(name: &str, want: &Option<Vec<String>>) -> bool {
    match want {
        None => true,
        Some(list) => list.iter().any(|w| w.eq_ignore_ascii_case(name)),
    }
}

/// Edit `stat` on `unit` in every civilization, and describe what changed.
///
/// Editing every civ is not a convenience: a villager exists in all 63, and
/// touching one of them is the "it worked in the game I tested" failure this
/// project has already paid for.
pub fn apply(
    server: &Server,
    stat: &str,
    unit: i16,
    value: f64,
    wanted: &Option<Vec<String>>,
) -> Result<String, String> {
    let parsed = server
        .parsed
        .lock()
        .unwrap()
        .clone()
        .ok_or("游戏数据还没读完")?;
    let _ = parsed;

    let root = std::env::var("AOE2MOD_GAME_ROOT")
        .map(std::path::PathBuf::from)
        .ok()
        .or_else(|| {
            [
                r"d:\games\steam\steamapps\common\AoE2DE",
                r"c:\games\steam\steamapps\common\AoE2DE",
            ]
            .iter()
            .map(std::path::PathBuf::from)
            .find(|p: &std::path::PathBuf| {
                p.join("resources/_common/dat/empires2_x2_p1.dat").is_file()
            })
        })
        .ok_or("找不到游戏目录")?;

    //  is the one place that knows how to find this table.
    // Building the path here by hand worked only when the cwd was the repo, and
    // in a shipped folder it answered os error 3 for a file that was right
    // there in app/_golden/ -- the same defect already fixed for the other
    // three call sites.
    let offsets_path = crate::stats_path();
    let table = StatTable::load(&offsets_path)
        .map_err(|e| format!("读不到 {}：{e}", offsets_path.display()))?;
    let kind = *table
        .kinds
        .get(stat)
        .ok_or_else(|| format!("不认识的属性 {stat}"))?;

    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Same family expansion as `build_one`, from the same table: `/api/stat` and
    // `/api/build` must never write different scopes for the same sentence.
    let family = family_ids(unit);
    let mut targets = Vec::new();
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
        let names = wanted.clone().unwrap_or_default();
        return Err(format!("认不出「{}」是哪个文明", names.join("、")));
    }
    if targets.is_empty() {
        return Err(format!("没有任何文明的单位 {unit} 带 {stat}"));
    }

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;

    // An absolute offset only means the same thing in the output because the
    // unmodified round trip is byte-identical. That is asserted, not assumed.
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    let before = read_at(&raw, targets[0].1, kind);
    for (_, off) in &targets {
        write_at(&mut out, *off, kind, value);
    }
    // Same mirror rule as `build_one`: `/api/stat` and `/api/build` must never
    // write different bytes for the same sentence, and a stat that is stored
    // twice (panel number + the raw row the engine reads) has to move both.
    let mirrors = crate::unitfield::stat_mirrors(&s810, &family, stat, wanted);
    let mirrors_len = mirrors.len();
    for m in &mirrors {
        let m_before = read_at(&raw, m.offset, m.kind);
        write_at(&mut out, m.offset, m.kind, m_before + (value - before));
    }

    let diffs = raw
        .iter()
        .zip(out.iter())
        .filter(|(a, b)| a != b)
        .count();

    // The mod ships raw-deflated, which is the container the game reads.
    let out_dir = std::env::temp_dir().join("aoe2mod-native");
    std::fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;
    let out_path = out_dir.join("empires2_x2_p1.dat");
    {
        use flate2::write::DeflateEncoder;
        use flate2::Compression;
        use std::io::Write;
        let f = std::fs::File::create(&out_path).map_err(|e| e.to_string())?;
        let mut e = DeflateEncoder::new(f, Compression::default());
        e.write_all(&out).map_err(|e| e.to_string())?;
        e.finish().map_err(|e| e.to_string())?;
    }

    Ok(format!(
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"variants\":{},\"edit_count\":{},\"mirror_count\":{},\"before\":{},\"value\":{},\"bytes_changed\":{},\"out\":\"{}\"}}",
        json_escape(stat),
        unit,
        civ_count(&targets),
        family.len(),
        targets.len() + mirrors_len,
        mirrors_len,
        before,
        value,
        diffs,
        json_escape(&out_path.display().to_string())
    ))
}

fn read_at(buf: &[u8], off: usize, kind: StatKind) -> f64 {
    match kind {
        StatKind::I16 if off + 2 <= buf.len() => {
            i16::from_le_bytes([buf[off], buf[off + 1]]) as f64
        }
        StatKind::U8 if off < buf.len() => buf[off] as f64,
        StatKind::F32 if off + 4 <= buf.len() => f32::from_le_bytes([
            buf[off],
            buf[off + 1],
            buf[off + 2],
            buf[off + 3],
        ]) as f64,
        _ => f64::NAN,
    }
}

fn write_at(buf: &mut [u8], off: usize, kind: StatKind, value: f64) {
    match kind {
        StatKind::I16 => {
            let v = value as i16;
            buf[off..off + 2].copy_from_slice(&v.to_le_bytes());
        }
        StatKind::U8 => buf[off] = value as u8,
        StatKind::F32 => {
            let v = value as f32;
            buf[off..off + 4].copy_from_slice(&v.to_le_bytes());
        }
    }
}

/// Compile one intent from the sentence layer, write the mod, install it.
///
/// The whole chain in one call, because each step alone is provable and the
/// interesting failures live in the joins: an intent that resolves but cannot be
/// compiled, a build that succeeds but installs nowhere, a title the engine will
/// truncate.
/// `/api/build` takes an intent LIST (`{"intents":[{...},{...}]}`) because one mod
/// carries every sentence the player typed: splitting them turns "tougher
/// villagers AND faster loom" into two mods of which the engine loads only the
/// higher-priority one.
///
/// Measured 2026-10-27: reading the field as `intent` (singular) meant the
/// Build button never worked for ANY intent -- every call fell through to the
/// stat branch and refused with "这句话没有说要改哪个单位", including the ones this
/// server implemented. The end-to-end probes missed it because they posted a flat
/// `{stat,unit,value}` body that the page never sends.
///
/// A bundle is still all-or-nothing: the first intent that fails to compile stops
/// the build, because a mod that applied two of the player's three sentences does
/// less than it says. Several intents that each want their own files are refused
/// by name rather than silently keeping the last one.
pub fn build_one(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    // Tech edits take a different path: a technology is ONE record (not 63), its
    // research time is a list of locations, and its cost is a slot index.
    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    if intent == "tech.research_time" || intent == "tech.cost" {
        return build_tech(server, req);
    }
    if intent == "tech.effect" {
        return build_effect(server, req);
    }
    if intent == "tech.toggle_group" {
        return build_toggle_group(server, req);
    }
    if intent == "unit.sprite" {
        return build_sprite(server, req);
    }
    if intent == "unit.card_move" || intent == "card_move" {
        return build_card_move(server, req);
    }
    if intent == "unit.cost" {
        return build_unit_cost(server, req);
    }
    if intent == "unit.attack_class" {
        return build_unit_attack_class(server, req);
    }
    let stat = req.get("stat").and_then(|v| v.as_str()).unwrap_or("");
    let unit = req.get("unit").and_then(|v| v.as_i64()).map(|v| v as i16);
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("{stat} {unit:?}"));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);

    let unit = unit.ok_or("这句话没有说要改哪个单位")?;
    if !server.parsed.lock().unwrap().is_some() {
        return Err("游戏数据还没读完".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let offsets_path = crate::stats_path();
    let table = StatTable::load(&offsets_path)
        .map_err(|e| format!("读不到 {}：{e}", offsets_path.display()))?;
    let kind = *table
        .kinds
        .get(stat)
        .ok_or_else(|| format!("不认识的属性 {stat}"))?;

    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Resolve the target value: SET means the number, DELTA means old + delta.
    //
    // `family_of` is not a nicety.  `村民血量改成100` names ONE id (83) but the
    // game ships 27 villager records per civilization -- age variants for the
    // trained unit and separate male/female baskets joined through
    // `objreplacement.json`.  Writing only the named id changes the male villager
    // and leaves the female one alone, while the screen reports "63 处改动": a
    // number that is really the extent of the loop, not of the edit.
    let family = family_ids(unit);
    let wanted = civ_filter(req);
    let mut targets = Vec::new();
    let mut seen_civ = false;
    for (ci, c) in s810.civs.iter().enumerate() {
        if !civ_in_scope(&c.name, &wanted) {
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
        let names = wanted.clone().unwrap_or_default();
        return Err(format!("认不出「{}」是哪个文明", names.join("、")));
    }
    if targets.is_empty() {
        return Err(format!("没有任何文明的单位 {unit} 带 {stat}"));
    }
    let old = read_at(&raw, targets[0].1, kind);
    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => old + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };

    // The second number, wherever AoE2 stores this property twice.
    //
    // `城堡攻击加5` used to write 126 bytes where the reference writes 252: the
    // panel's `displayed_attack` moved and the raw class-3 attack row that the
    // damage maths actually reads did not, so the panel would show 10 while the
    // arrow still hit for 5.  The mirror carries the DELTA, never the value,
    // because 20 shipped records keep the two numbers apart on purpose.
    let mirrors = crate::unitfield::stat_mirrors(&s810, &family, stat, &wanted);
    let mirror_delta = match (value, delta) {
        (Some(v), _) => v - old,
        (None, Some(d)) => d,
        (None, None) => 0.0,
    };

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }
    for (_, off) in &targets {
        write_at(&mut out, *off, kind, new_value);
    }
    for m in &mirrors {
        let before = read_at(&raw, m.offset, m.kind);
        write_at(&mut out, m.offset, m.kind, before + mirror_delta);
    }

    let head = format!(
        "{{\"ok\":true,\"stat\":\"{}\",\"unit\":{},\"civs\":{},\"variants\":{},\"edit_count\":{},\"mirror_count\":{},\"before\":{},\"value\":{}",
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
        return Ok(format!("{head},\"dry\":true,\"dat_bytes\":0,\"compressed\":0,\"built\":\"\",\"installed\":\"\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &description_of(req),
        true,
    )?;

    // Remember the origin BEFORE installing: the record is what makes the mod
    // visible to /api/update-check and replayable by /api/rebuild, and a mod
    // that exists while both guards have never heard of it is the failure this
    // project's provenance layer exists to prevent.
    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, r, _v)) => (f, r),
        None => (String::new(), None),
    };
    // Hash the bytes that LAND ON DISK, which are raw-deflated -- the same file
    // `update-check` will hash later. Hashing the uncompressed stream here made
    // every freshly built mod report `edited`, i.e. "something else overwrote
    // this", about the file this tool had just written itself.
    let dat_out_sha = sha256_bytes(&built.compressed);

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    // The record. `changes_dat: true` because this build genuinely rewrites the
    // .dat, which is what lets the update guard call it `stale` later instead of
    // `no_dat`.
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description_of(req),
        recorded_intent(
            serde_json::json!({
                "intent": "unit.stat",
                "unit": unit,
                "stat": stat,
                "value": new_value
            }),
            req,
        ),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    // Distinct civilizations, not writes: `targets.len()` under the name `civs`
    // says 1701 civilizations exist after family expansion.  The two numbers
    // answer different questions and the reference calls them `civ_count` and
    // `edit_count`.
    Ok(format!(
        "{head},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

/// How many distinct civilizations the write list touches.
fn civ_count(targets: &[(usize, usize)]) -> usize {
    let mut seen: Vec<usize> = targets.iter().map(|(ci, _)| *ci).collect();
    seen.sort_unstable();
    seen.dedup();
    seen.len()
}

/// The shared body of `unit.cost` and `unit.attack_class`.
///
/// Both write `i16`s into a unit record at offsets the parser measured, both
/// have to expand to the variant family, and both produce the same report.  The
/// only difference is how a sentence becomes offsets, so that is the closure --
/// one copy of the write/install/remember chain, which is where a divergence
/// would be invisible: a cost edit that installed and a damage edit that only
/// reported would each look correct from its own JSON.
fn build_unit_field(
    server: &Server,
    req: &serde_json::Value,
    resolve: impl FnOnce(
        &aoe2mod_dat::stage810::Stages810,
        &[i16],
        i16,
        &Option<Vec<String>>,
    ) -> Result<crate::unitfield::Resolved, String>,
) -> Result<String, String> {
    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    let unit = req
        .get("unit")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("这句话没有说要改哪个单位")?;
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Family, not the named id: `村民` is 27 records per civilisation, and
    // writing only the one the sentence named leaves the female villager alone
    // while the screen reports the loop's extent as if it were the edit's.
    let family = family_ids(unit);
    // Same scope as the two byte-patch paths: `/api/build`, `/api/stat` and the
    // preview all have to touch the same civilizations for the same sentence.
    let wanted = civ_filter(req);
    let resolved = resolve(&s810, &family, unit, &wanted)?;

    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => resolved.before + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }
    let kind = resolved.kind();
    for hit in &resolved.hits {
        write_at(&mut out, hit.offset, kind, new_value);
    }

    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("{intent} {unit}"));

    let head = format!(
        "{{\"ok\":true,\"intent\":\"{}\",\"unit\":{},\"field\":\"{}\",\"civs\":{},\"variants\":{},\"edit_count\":{},\"before\":{},\"value\":{}",
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
        return Ok(format!("{head},\"dry\":true,\"dat_bytes\":0,\"compressed\":0,\"built\":\"\",\"installed\":\"\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &description_of(req),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description_of(req),
        recorded_intent(
            serde_json::json!({
                "intent": intent,
                "unit": unit,
                "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
                "attack_kind": req.get("attack_kind").cloned().unwrap_or(serde_json::Value::Null),
                "value": new_value
            }),
            req,
        ),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{head},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

/// `unit.cost`: the amount in one of the unit's three cost slots.
fn build_unit_cost(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    let resource = req
        .get("resource")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    build_unit_field(server, req, |s810, family, unit, wanted| {
        crate::unitfield::cost_targets(s810, family, wanted, &resource, unit)
    })
}

/// `unit.attack_class`: one row of Type50's attack or armour list, plus the
/// panel number that tracks it.
fn build_unit_attack_class(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    let kind = req
        .get("attack_kind")
        .and_then(|v| v.as_str())
        .or_else(|| req.get("kind").and_then(|v| v.as_str()))
        .unwrap_or("attack")
        .to_string();
    // The candidate list comes from the sentence layer when it has one, so a
    // sentence that names a class can narrow it.  The default is the schema's
    // `attack_classes.attack|armour.class_candidates`, tried in order.
    // A class the sentence named is the ONLY candidate, exactly as the
    // reference's `_class_selectors` does it (`compiler.py:2100`: `if "class_id"
    // in b: return [b["class_id"]]`).  Keeping the schema's list as a fallback
    // would make a sentence that asked for a class the unit does not carry
    // silently edit a different class instead of refusing -- measured on
    // 「民兵对建筑攻击加2」, which asked for 3 and used to write 4.
    let classes: Vec<i16> = match req.get("class_id").and_then(|v| v.as_i64()) {
        Some(c) => vec![c as i16],
        None => req
            .get("class_candidates")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|x| x.as_i64().map(|v| v as i16)).collect())
            .filter(|v: &Vec<i16>| !v.is_empty())
            .unwrap_or_else(|| {
                if kind == "armour" {
                    vec![4, 3]
                } else {
                    vec![3, 4]
                }
            }),
    };
    build_unit_field(server, req, |s810, family, unit, wanted| {
        crate::unitfield::damage_targets(s810, family, wanted, &kind, &classes, unit)
    })
}


/// `tech.research_time` / `tech.cost`: one global record, one or more offsets.

/// The `/api/build` entry point: an intent ARRAY, or a single flat intent.
///
/// One intent is the whole story for every current strategy -- each writes its
/// own files under its own `<build>/<title>/`, so two of them in one folder would
/// each recreate the folder and drop the other's file. That is a real limitation
/// and it is said out loud instead of returning the last build as if it were the
/// bundle the player asked for.
pub fn build_and_install(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    let list = match req.get("intents").and_then(|v| v.as_array()) {
        Some(a) if !a.is_empty() => a.clone(),
        _ => return build_one(server, req),
    };
    if list.len() > 1 {
        let names: Vec<String> = list
            .iter()
            .map(|it| {
                it.get("intent")
                    .and_then(|v| v.as_str())
                    .unwrap_or("?")
                    .to_string()
            })
            .collect();
        return Err(format!(
            "这一步一个 mod 只能装一件事：现在收到 {} 句（{}）。每句话各写自己的文件、各自建目录，装进同一个 mod 会互相覆盖。先做一句，或把它们分成几步。",
            list.len(),
            names.join("、")
        ));
    }
    let mut one = list[0].clone();
    // Carry the bundle-level fields onto the single intent: the title says what
    // the mod is CALLED, and every builder reads it from the intent it is given.
    if let Some(obj) = one.as_object_mut() {
        for key in ["title", "author", "description", "install", "title_auto"] {
            if !obj.contains_key(key) {
                if let Some(v) = req.get(key) {
                    obj.insert(key.to_string(), v.clone());
                }
            }
        }
    }
    build_one(server, &one)
}

fn build_tech(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::writer::Writer;
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    let intent = req.get("intent").and_then(|v| v.as_str()).unwrap_or("");
    let tech = req
        .get("tech")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("这句话没有说要改哪个科技")?;
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("tech {tech}"));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let table = crate::techedit::TechTable::load(&crate::techedit::table_path())
        .map_err(|e| format!("读不到科技偏移表：{e}"))?;

    // Which absolute offsets this edit writes.
    let offsets: Vec<usize> = if intent == "tech.research_time" {
        let v = table.research_time_offsets(tech);
        if v.is_empty() {
            return Err(format!("科技 {tech} 没有研究时间可改"));
        }
        v
    } else {
        // The cost slot is chosen by the resource word, mapped through the order
        // the record stores them in. Naming the slot rather than inferring it is
        // the point: an empty slot is a real thing and (-1,0,0) is the sentinel.
        let res = req.get("resource").and_then(|v| v.as_str()).unwrap_or("");
        let rtype = crate::techedit::TechTable::resource_type_id(res)
            .ok_or_else(|| format!("不认识的资源 {res}"))?;
        match table.cost_offset(tech, rtype) {
            Some(o) => vec![o],
            // Refused rather than added: "give this tech a new cost" is a
            // different operation from "change the price", and guessing a slot
            // is how the price moves on one field and the artefact shows a cost
            // the game does not charge.
            None => {
                return Err(format!(
                    "科技 {tech} 本来就不花{res}，所以没有可以改的那一格；                     加一条新成本是另一件事，这个版本还不做"
                ))
            }
        }
    };

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    let kind = aoe2mod_dat::stats::StatKind::I16;
    let old = read_at(&raw, offsets[0], kind);
    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => old + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };
    // EVERY location, not the first: a tech can carry several and the untouched
    // copies keep the old time, which in game reads as "nothing changed".
    for off in &offsets {
        write_at(&mut out, *off, kind, new_value);
    }
    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();

    let head = format!(
        "{{\"ok\":true,\"intent\":\"{}\",\"tech\":{},\"locations\":{},\"edit_count\":{},\"before\":{},\"value\":{},\"bytes_changed\":{}",
        crate::server::json_escape(intent),
        tech,
        offsets.len(),
        // Every copy is written, so the reach IS the location count.  A tech
        // with one location says "1 处", which is what the reference says.
        offsets.len(),
        old,
        new_value,
        diffs
    );
    if is_dry(req) {
        return Ok(format!("{head},\"dry\":true,\"dat_bytes\":0,\"compressed\":0,\"built\":\"\",\"installed\":\"\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &description_of(req),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    // Hash the bytes that LAND ON DISK, which are raw-deflated -- the same file
    // `update-check` will hash later. Hashing the uncompressed stream here made
    // every freshly built mod report `edited`, i.e. "something else overwrote
    // this", about the file this tool had just written itself.
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description_of(req),
        recorded_intent(
            serde_json::json!({
                "intent": intent,
                "tech": tech,
                "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
                "value": new_value
            }),
            req,
        ),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{head},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


fn sha256_bytes(b: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(b);
    format!("{:x}", h.finalize())
}


/// `tech.effect`: write ONE field of ONE command inside a technology's effect.
///
/// What it refuses, and why refusing is the right answer:
///
///   * a command index that does not exist -- adding a command changes the
///     record's LENGTH, which shifts every following effect and invalidates
///     `effect_id` everywhere;
///   * a field name that is not `t`/`a`/`b`/`c`/`d` -- those are the five the
///     format has, and inventing one would write at an offset that means
///     something else.
fn build_effect(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::writer::Writer;
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    // A tech's effect_id names the effect record. The sentence layer returns the
    // TECH id, so it has to be resolved through the tech record -- editing the
    // effect whose index happens to equal the tech id would be right for Loom
    // (tech 22, effect 22) and wrong for most others, which is the worst kind of
    // coincidence to rely on.
    let tech = req
        .get("tech")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("这句话没有说要改哪个科技")?;
    let command = req
        .get("command")
        .and_then(|v| v.as_u64())
        .map(|v| v as usize)
        .ok_or("这句话没有说是第几条效果")?;
    let field = req
        .get("field")
        .and_then(|v| v.as_str())
        .unwrap_or("d")
        .to_string();
    let value = req.get("value").and_then(|v| v.as_f64());
    let delta = req.get("delta").and_then(|v| v.as_f64());
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("tech {tech} effect"));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }
    let (kind_name, width) = crate::effectedit::field_kind(&field)
        .ok_or_else(|| format!("没有 {field} 这个字段（只有 t/a/b/c/d）"))?;

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let effect_id = s810
        .techs
        .get(tech as usize)
        .map(|t| t.effect_id)
        .ok_or_else(|| format!("没有编号 {tech} 的科技"))?;
    if effect_id < 0 {
        return Err(format!("科技 {tech} 没有效果记录"));
    }

    let table = crate::effectedit::EffectTable::load(&crate::effectedit::table_path())
        .map_err(|e| format!("读不到效果偏移表：{e}"))?;
    // `command` is 0-BASED, which is what the reference's intent carries
    // (`nl.py:1769`: `"command": idx`, and `idx` already had one subtracted).
    // The sentence layer therefore must not subtract, and this side must not
    // either.  Measured both ways: with `- 1` here and `idx = ordv` there the
    // two cancelled out, so 「第2条」 wrote the THIRD command and looked fine;
    // removing only the sentence side made 「第1条」 ask for command 0 minus one,
    // which `as u64` had already wrapped past the end and reported as "没有第 0
    // 条命令".  Both numbers are positions, so exactly one of them converts.
    let cmd = table
        .command(effect_id as i32, command)
        .ok_or_else(|| {
            format!(
                "效果 {effect_id} 没有第 {} 条命令（加一条是另一件事，会让后面所有效果错位）",
                command + 1
            )
        })?;
    let off = *cmd
        .get(&field)
        .ok_or_else(|| format!("效果 {effect_id} 第 {} 条没有 {field} 字段", command + 1))?;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    let old = match width {
        1 => raw.get(off).map(|b| *b as f64).unwrap_or(f64::NAN),
        2 => read_at(&raw, off, aoe2mod_dat::stats::StatKind::I16),
        _ => read_at(&raw, off, aoe2mod_dat::stats::StatKind::F32),
    };
    let new_value = match (value, delta) {
        (Some(v), _) => v,
        (None, Some(d)) => old + d,
        (None, None) => return Err("这句话没有说要改成多少".into()),
    };
    match width {
        1 => {
            if off < out.len() {
                out[off] = new_value as u8;
            }
        }
        2 => write_at(&mut out, off, aoe2mod_dat::stats::StatKind::I16, new_value),
        _ => write_at(&mut out, off, aoe2mod_dat::stats::StatKind::F32, new_value),
    }
    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();

    let head = format!(
        "{{\"ok\":true,\"tech\":{},\"effect\":{},\"command\":{},\"edit_count\":1,\"field\":\"{}\",\"field_kind\":\"{}\",\"before\":{},\"value\":{},\"bytes_changed\":{}",
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
        return Ok(format!("{head},\"dry\":true,\"dat_bytes\":0,\"compressed\":0,\"built\":\"\",\"installed\":\"\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &description_of(req),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description_of(req),
        serde_json::json!([{
            "intent": "tech.effect",
            "tech": tech,
            "command": command,
            "field": field,
            "value": new_value
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{head},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


/// `unit.card_move`: exchange two units' boxes on one building's card.
///
/// Dragging a box in the engine is ONE BYTE: the `button_id` in that unit's
/// `train_locations` entry. The byte sits `TRAIN_BUTTON_OFF` after the entry's
/// absolute `_off_train_time`, which `command_cards.json` carries.
///
/// A move SWAPS. Two units on one box is a state the shipped data never
/// contains, and the engine resolves it by drawing one of them -- so an editor
/// that lets a drop overwrite deletes a unit and reports success.
fn build_card_move(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::writer::Writer;
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    let unit = req
        .get("unit")
        .and_then(|v| v.as_i64())
        .map(|v| v as i16)
        .ok_or("没说要把哪个单位挪走")?;
    // The sentence may omit the building ("把民兵放在第5格"), and the server
    // reads it from the TABLE: the card the unit is already on. That is what the
    // sentence means -- "move it within its own card" -- and inventing a
    // different building would either fail or move it somewhere the player did
    // not ask for.
    let mut building = req
        .get("building")
        .or_else(|| req.get("builder"))
        .and_then(|v| v.as_i64())
        .map(|v| v as i16);
    // TWO spellings, deliberately.  The page's own drag handler posts `box`, and
    // the sentence reader emits `button` (`sentences.rs:230`) because that is
    // what the schema calls the slot.  Reading only `box` meant every sentence
    // this program said it understood came back "没说要挪到第几格" -- the
    // reader and the builder disagreed about a field name, and only the
    // parse→build path crossed the join.
    let target = req
        .get("box")
        .or_else(|| req.get("button"))
        .and_then(|v| v.as_u64())
        .map(|v| v as u8)
        .ok_or("没说要挪到第几格")?;
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("card {}", building.map(|b| b.to_string()).unwrap_or_else(|| "auto".into())));
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let cards_json: serde_json::Value = {
        let t = std::fs::read_to_string(crate::cards::table_path())
            .map_err(|e| format!("读不到命令面板表：{e}"))?;
        serde_json::from_str(t.trim_start_matches('\u{feff}'))
            .map_err(|e| format!("命令面板表不是合法 JSON：{e}"))?
    };
    if building.is_none() {
        // First card in id order that lists this unit. Deterministic, and the
        // common case for a villager is the town centre / barracks it starts on.
        if let Some(cards) = cards_json.get("cards").and_then(|c| c.as_object()) {
            let mut ids: Vec<i16> = cards.keys().filter_map(|k| k.parse().ok()).collect();
            ids.sort();
            for id in ids {
                if let Some(list) = cards.get(&id.to_string()).and_then(|v| v.as_array()) {
                    if list.iter().any(|e| {
                        e.get("unit").and_then(|v| v.as_i64()) == Some(unit as i64)
                    }) {
                        building = Some(id);
                        break;
                    }
                }
            }
        }
    }
    let building = building.ok_or_else(|| {
        format!("第 {unit} 号单位不在任何建筑的训练表里，所以它没有格子可挪")
    })?;
    let lookup = crate::cardmove::entry_lookup(&cards_json, building, |_| None);
    if !lookup.contains_key(&unit) {
        return Err(format!(
            "第 {unit} 号单位不在这座建筑（{building}）的训练表里，所以它没有格子可挪"
        ));
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let mut out = w.out;
    if out != raw {
        return Err("未修改的往返不是逐字节相同，拒绝按绝对偏移写入".into());
    }

    // Offsets are ABSOLUTE in the table (locate stores cursor positions); the box
    // byte is a fixed distance after the train-time field.
    let table = lookup.clone();
    let slots = crate::slots::card_slots(&root).0;
    let report = crate::cardmove::move_unit(&mut out, unit, building, target, slots, |u| {
        table.get(&u).copied()
    })?;

    let diffs = raw.iter().zip(out.iter()).filter(|(a, b)| a != b).count();
    let moved: Vec<String> = report
        .moved
        .iter()
        .map(|(u, from, to)| format!("{{\"unit\":{u},\"from\":{from},\"to\":{to}}}"))
        .collect();
    let head = format!(
        "{{\"ok\":true,\"building\":{},\"offset\":{},\"before\":{},\"after\":{},\"moved\":[{}],\"edit_count\":{},\"bytes_changed\":{}",
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
    );
    if is_dry(req) {
        return Ok(format!("{head},\"dry\":true,\"dat_bytes\":0,\"compressed\":0,\"built\":\"\",\"installed\":\"\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &description_of(req),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description_of(req),
        serde_json::json!([{
            "intent": "unit.card_move",
            "unit": unit,
            "building": building,
            "button": target
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{head},\"built\":\"{}\",\"installed\":\"{}\"}}",
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}


/// Public wrapper: the server module calls this, and `build_card_move` stays
/// private so its signature can change without touching the routing layer.
pub fn build_card_move_pub(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    build_card_move(server, req)
}


/// `unit.sprite` in RENAME mode: re-point graphics records, ship no pictures.
///
/// Copy mode would ship 466 `.sld` files (438 MB). Rename mode ships none: the
/// `.dat` already says which file to load per graphics record, so re-pointing
/// them is the whole edit -- ~12 MB.
///
/// The hazard is the one this project paid for: a graphics record's `file` string
/// has a STORED WIDTH, and re-emitting it at a different length must advance the
/// input cursor by the OLD width or every later verbatim read shifts. That is
/// what `Graphic::file_len` is for, and it is passed through here.
fn build_sprite(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use crate::write23::{write_stage1, write_stages23};
    use crate::write47::write_stages47;
    use crate::write810::write_stages810;
    use crate::writer::Writer;
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };

    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "sprite".to_string());
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    // Which unit and which donor the sentence named.  Absent means the request
    // came from a path that had no sentence (the page's own sprite form), and in
    // that case there is nothing to decide: refuse rather than pick a pair, which
    // is exactly how this function used to edit the villager for an archer
    // sentence.
    let target = req.get("unit").and_then(|v| v.as_i64());
    let donor = req.get("donor").and_then(|v| v.as_i64());
    let (Some(target), Some(donor)) = (target, donor) else {
        return Err("没说要换成哪个单位的图".into());
    };
    let target = target as i16;
    let donor = donor as i16;
    if target == donor {
        return Err("目标单位和捐赠方是同一个，改了等于没改".into());
    }

    let art = crate::spriteart::SpriteArt::load(&crate::spriteart::table_path())
        .map_err(|e| format!("读不到贴图艺术表：{e}"))?;
    if art.arts.is_empty() || art.units.is_empty() {
        return Err("贴图艺术表是空的".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let gdir = root.join("resources/_common/drs/graphics");
    let wanted = civ_filter(req);
    let plan = art.plan(target, donor, &wanted, Some(&gdir))?;
    if wanted.is_some() && plan.civs == 0 {
        return Err("这些文明里没有这个单位的散图".into());
    }

    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;
    let mut r = Reader::new(&raw);
    let s1 = read_stage1(&mut r).map_err(|e| e.to_string())?;
    let gv = s1.game_version;
    let mut s23 = read_stages23(&mut r).map_err(|e| e.to_string())?;
    let s47 = read_stages47(&mut r, gv).map_err(|e| e.to_string())?;
    let s810 = read_stages810(&mut r, gv).map_err(|e| e.to_string())?;

    // Re-point the graphics records whose file the decision named. `file_len` is
    // left ALONE on purpose: it is the width the INPUT used, and the writer needs
    // it to advance the cursor.
    let mut touched = 0usize;
    let mut moved_by_name: std::collections::BTreeMap<String, usize> =
        std::collections::BTreeMap::new();
    for g in s23.graphics.iter_mut() {
        if let Some(donor_file) = plan.want.get(&g.file) {
            if &g.file != donor_file {
                *moved_by_name.entry(g.file.clone()).or_insert(0) += 1;
                g.file = donor_file.clone();
                touched += 1;
            }
        }
    }
    if touched == 0 {
        // The decision named files no record uses.  That is not a success with a
        // small number: it is a rename of nothing, and the reference refuses it in
        // the same words.
        return Err(format!(
            "没有任何图像记录用这 {} 个目标文件名，改名等于什么也没做",
            plan.want.len()
        ));
    }

    let mut w = Writer::new(&raw);
    write_stage1(&mut w, &s1).map_err(|e| e.to_string())?;
    write_stages23(&mut w, &s23, &raw).map_err(|e| e.to_string())?;
    write_stages47(&mut w, &s47, gv).map_err(|e| e.to_string())?;
    write_stages810(&mut w, &s810).map_err(|e| e.to_string())?;
    let out = w.out;
    // NOT `mismatches != 0`: this edit changes the LENGTH of a string, so every
    // byte after it legitimately differs from the input. The round-trip check
    // applies to unmodified builds, where the whole stream must be identical.
    // Here the gate is the RE-PARSE below: if the cursor bookkeeping is right the
    // output parses to its own EOF, and if it is wrong it will not.
    let _ = w.mismatches;

    // Re-parse the OUTPUT: the whole point of rename mode is that the records say
    // what we asked and nothing else moved.
    let mut r2 = Reader::new(&out);
    let o1 = read_stage1(&mut r2).map_err(|e| e.to_string())?;
    let _ = read_stages23(&mut r2).map_err(|e| e.to_string())?;
    let _ = read_stages47(&mut r2, o1.game_version).map_err(|e| e.to_string())?;
    let _ = read_stages810(&mut r2, o1.game_version).map_err(|e| e.to_string())?;
    if r2.pos != out.len() {
        return Err(format!(
            "改完之后重新解析停在 {}，文件长 {}",
            r2.pos,
            out.len()
        ));
    }

    // What the decision came to, so the preview can describe THIS edit rather
    // than a generic one.  `file_count` is the number of distinct filenames the
    // decision covers (both resolutions), which is what a person means by "how
    // many pictures"; `edit_count` is how many records actually moved.
    let stems_json = |v: &[String]| {
        v.iter()
            .map(|s| format!("\"{}\"", json_escape(s)))
            .collect::<Vec<String>>()
            .join(",")
    };
    let unmapped_json = plan
        .unmapped
        .iter()
        .map(|(t, f)| format!("{{\"token\":\"{}\",\"file\":\"{}\"}}", json_escape(t), json_escape(f)))
        .collect::<Vec<String>>()
        .join(",");
    let mut warnings: Vec<String> = Vec::new();
    for (anim, tg, dg) in plan.grid_mismatches.iter() {
        let grid = |g: &Vec<Vec<i64>>| {
            g.first()
                .map(|r| format!("{}x{}", r[0], r[1]))
                .unwrap_or_else(|| "?".into())
        };
        warnings.push(format!(
            "换来的「{}」动画帧格子和原来的不一样（{} 对 {}），游戏可能照着错的行列去播，而不是报错",
            anim,
            grid(dg),
            grid(tg)
        ));
    }
    if !plan.unmapped.is_empty() {
        let mut words: Vec<String> = plan.unmapped.iter().map(|(t, _f)| t.clone()).collect();
        words.sort();
        words.dedup();
        warnings.push(format!(
            "捐赠方没有这些动画，{}张原图会留着：{}",
            words.len(),
            words.join("、")
        ));
    }
    let warnings_json = warnings
        .iter()
        .map(|w| format!("\"{}\"", json_escape(w)))
        .collect::<Vec<String>>()
        .join(",");
    // The whole-map report, for a caller that wants to know which names moved.
    let moved_json = moved_by_name
        .iter()
        .map(|(k, n)| format!("{{\"was\":\"{}\",\"count\":{}}}", json_escape(k), n))
        .collect::<Vec<String>>()
        .join(",");

    // Which civilizations the decision actually reached, by their `.dat` name, so
    // a scoped rename can say so instead of claiming all 63.
    let scope_names: Vec<String> = match &wanted {
        Some(list) => list.clone(),
        None => art.civ_names.clone(),
    };
    let scope_json = scope_names
        .iter()
        .filter(|n| !n.is_empty())
        .map(|n| format!("\"{}\"", json_escape(n)))
        .collect::<Vec<String>>()
        .join(",");

    let head = format!(
        "{{\"ok\":true,\"intent\":\"unit.sprite\",\"mode\":\"rename\",\"records\":{touched},\"edit_count\":{touched},\
\"target\":{target},\"donor\":{donor},\
\"target_stems\":[{}],\"donor_stems\":[{}],\
\"file_count\":{},\"civ_count\":{},\
\"target_names\":{},\"donor_names\":{},\
\"civ_names\":[{}],\
\"writes\":\"resources/_common/dat/empires2_x2_p1.dat\",\"changes_dat\":true,\
\"unmapped\":[{}],\"warnings\":[{}],\"moved\":[{}]",
        stems_json(&plan.target_stems),
        stems_json(&plan.donor_stems),
        plan.want.len(),
        plan.civs,
        plan.want.len(),
        plan
            .want
            .values()
            .collect::<std::collections::BTreeSet<&String>>()
            .len(),
        scope_json,
        unmapped_json,
        warnings_json,
        moved_json
    );
    if is_dry(req) {
        return Ok(format!("{head},\"dry\":true,\"dat_bytes\":0,\"compressed\":0,\"built\":\"\",\"installed\":\"\"}}"));
    }

    let build_root = std::env::temp_dir().join("aoe2mod-native-build").join(&title);
    let built = crate::build::build_data_mod(
        &build_root,
        &out,
        &title,
        "aoe2mod",
        &description_of(req),
        true,
    )?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    let dat_out_sha = sha256_bytes(&built.compressed);
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description_of(req),
        serde_json::json!([{
            "intent": "unit.sprite",
            "unit": target,
            "donor": donor,
            "mode": "rename"
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        "{head},\"dat_bytes\":{},\"compressed\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        built.dat_bytes,
        built.compressed.len(),
        crate::server::json_escape(&built.dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

/// Public wrapper for the routing layer.
pub fn build_sprite_pub(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    build_sprite(server, req)
}


/// `tech.toggle_group`: append one `MutuallyExclusive` entry to linkedTechs.json.
///
/// The mod ships an UNMODIFIED `.dat` beside the JSON: measured in this project,
/// a mod writing under `resources/_common/dat/` without one makes the game fail to
/// start, because that storage point is resolved as a unit rather than per file.
/// `changes_dat` is therefore true even though no `.dat` byte moved -- the record
/// says "this mod carries a .dat", which is what the update guard needs to know.
fn build_toggle_group(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    use aoe2mod_dat::load_dat;

    let techs: Vec<i16> = req
        .get("techs")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|x| x.as_i64().map(|n| n as i16)).collect())
        .unwrap_or_default();
    let title = req
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.trim().is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "tech group".to_string());
    let install = req.get("install").and_then(|v| v.as_bool()).unwrap_or(false);
    if server.parsed.lock().unwrap().is_none() {
        return Err("游戏数据还没读完".into());
    }

    let root = crate::game_root().ok_or("找不到游戏目录")?;
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
    let (raw, _how) = load_dat(&dat).map_err(|e| e.to_string())?;

    let out_dir = std::env::temp_dir()
        .join("aoe2mod-native-build")
        .join(&title);
    let kind = req
        .get("type")
        .and_then(|v| v.as_str())
        .unwrap_or("MutuallyExclusive")
        .to_string();
    if is_dry(req) {
        // The JSON layer is the whole edit, and it is refused or accepted by
        // `add_group` -- so the preview has to run it, not guess.  Run it against
        // a COPY of the document and throw the copy away.
        let src = root.join("resources/_common/dat/linkedTechs.json");
        let text = std::fs::read_to_string(&src)
            .map_err(|e| format!("读不到 {}：{e}", src.display()))?;
        let mut doc: serde_json::Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .map_err(|e| format!("{} 不是合法 JSON：{e}", src.display()))?;
        let entry = crate::togglegroup::add_group(&mut doc, &techs)?;
        let total = doc
            .get("LinkedTechs")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0);
        // The `.dat` half is counted, not guessed: an `edit_count` that says
        // "1 entry" while the mechanism is 4 commands (or, for a Cycle, none at
        // all) understates what pressing 生成 does to the player's game folder.
        let (cmds, cloned, changed) = crate::groupdat::rewrite(&raw, &techs, &kind)
            .map(|r| match r {
                Some(r) => (
                    r.added.commands_added,
                    r.added.cloned.len(),
                    r.bytes != raw,
                ),
                None => (0, 0, false),
            })
            .unwrap_or((0, 0, false));
        return Ok(format!(
            // `edit_count` must be here too: the preview reads the builder's own
            // report, and a dry run that omits the field previews "0 edits" for
            // an edit that writes one entry.  A zero meaning "not reported" is
            // indistinguishable from a zero meaning "nothing will happen".
            "{{\"ok\":true,\"intent\":\"tech.toggle_group\",\"entry\":{},\"entries\":{},\"edit_count\":1,\"files\":2,\"changes_dat\":{},\"commands_added\":{},\"shared_effects_cloned\":{},\"dry\":true,\"built\":\"\",\"installed\":\"\"}}",
            entry,
            total,
            changed,
            cmds,
            cloned
        ));
    }
    if out_dir.exists() {
        std::fs::remove_dir_all(&out_dir).map_err(|e| e.to_string())?;
    }
    std::fs::create_dir_all(&out_dir).map_err(|e| e.to_string())?;

    // 1. the JSON layer
    let (entry, total) = crate::togglegroup::build(
        &root.join("resources/_common/dat"),
        &out_dir,
        &techs,
    )?;

    // 2. the .dat half.
    //
    // The label alone is not the mechanism: `linkedTechs.json` draws the red
    // cross and the second technology stays researchable.  The `type 102`
    // commands in each member's own effect are what actually hide it, so this
    // half is written whenever `kind` is one of the two that use it -- and
    // VERIFIED by re-parsing the bytes, because a wrong writer cursor still
    // produces a well-formed 93 MB file.
    let (dat_bytes, compressed, commands_added, cloned) = match crate::groupdat::rewrite(
        &raw, &techs, &kind,
    )? {
        Some(rw) => {
            let first = techs[0];
            let expect = rw
                .added
                .cloned
                .iter()
                .find(|c| c.tech == first)
                .map(|c| (c.from, c.to));
            let v = crate::groupdat::verify(&rw.bytes, first, &kind, expect)?;
            if v.reparsed_commands == 0 {
                return Err("写出的 .dat 里没有 102 命令".into());
            }
            use flate2::write::DeflateEncoder;
            use flate2::Compression;
            use std::io::Write;
            let mut enc = DeflateEncoder::new(Vec::new(), Compression::default());
            enc.write_all(&rw.bytes).map_err(|e| e.to_string())?;
            let packed = enc.finish().map_err(|e| e.to_string())?;
            (
                rw.bytes.len(),
                packed,
                rw.added.commands_added,
                rw.added.cloned.len(),
            )
        }
        None => {
            // Nothing to add: every member already bans the others, so the only
            // change is the JSON entry.  A `.dat` is still shipped because a mod
            // that writes under `resources/_common/dat/` without one makes the
            // game fail to start -- the DAT storage point is resolved as a unit,
            // not per file.
            use flate2::write::DeflateEncoder;
            use flate2::Compression;
            use std::io::Write;
            let mut enc = DeflateEncoder::new(Vec::new(), Compression::default());
            enc.write_all(&raw).map_err(|e| e.to_string())?;
            (raw.len(), enc.finish().map_err(|e| e.to_string())?, 0usize, 0usize)
        }
    };
    let dat_out = out_dir.join("resources/_common/dat/empires2_x2_p1.dat");
    if let Some(parent) = dat_out.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&dat_out, &compressed).map_err(|e| e.to_string())?;

    // 3. info.json, compact, four keys
    let description = description_of(req);
    let info = format!(
        "{{\"Author\":\"aoe2mod\",\"CacheStatus\":0,\"Description\":\"{}\",\"Title\":\"{}\"}}",
        crate::server::json_escape(&description),
        crate::server::json_escape(&title)
    );
    std::fs::write(out_dir.join("info.json"), info).map_err(|e| e.to_string())?;

    let mut installed_to = String::new();
    if install {
        let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
        let built = crate::build::Built {
            dir: out_dir.clone(),
            title: title.clone(),
            dat_bytes,
            compressed: compressed.clone(),
        };
        let dest = crate::build::install_local(&prof, &built, &title)?;
        installed_to = dest.display().to_string();
    }

    let (base_file_sha, base_raw_sha) = match crate::updates::fingerprint(&dat, true) {
        Some((f, rr, _v)) => (f, rr),
        None => (String::new(), None),
    };
    // The hash of what LANDED ON DISK.  Empty only when the `.dat` is a byte
    // copy of the factory one: `update-check` reads an empty hash as "carrier",
    // and reading a real hash as carrier would hide a mod that went stale.
    let dat_out_sha = if commands_added > 0 {
        sha256_bytes(&compressed)
    } else {
        String::new()
    };
    crate::updates::remember_build(
        &title,
        "aoe2mod",
        &description,
        serde_json::json!([{
            "intent": "tech.toggle_group",
            "techs": techs
        }]),
        &base_file_sha,
        base_raw_sha.as_deref(),
        &dat_out_sha,
        true,
    )
    .map_err(|e| format!("建好了但没能写构建记录：{e}"))?;

    Ok(format!(
        // One entry, not one per member: the array it lands in is keyed by
        // group, and 「2 项做成一组」 changes that array once.  The reference
        // reports edit_count 1 for the same sentence.  `commands_added` is the
        // separate, honest count of what the `.dat` half did -- the two numbers
        // answer different questions and a single one would hide the case where
        // the JSON changed and the mechanism did not.
        "{{\"ok\":true,\"intent\":\"tech.toggle_group\",\"entry\":{},\"entries\":{},\"edit_count\":1,\"files\":2,\"changes_dat\":{},\"commands_added\":{},\"shared_effects_cloned\":{},\"dat_bytes\":{},\"built\":\"{}\",\"installed\":\"{}\"}}",
        entry,
        total,
        commands_added > 0,
        commands_added,
        cloned,
        dat_bytes,
        crate::server::json_escape(&out_dir.display().to_string()),
        crate::server::json_escape(&installed_to)
    ))
}

pub fn build_toggle_group_pub(server: &Server, req: &serde_json::Value) -> Result<String, String> {
    build_toggle_group(server, req)
}
