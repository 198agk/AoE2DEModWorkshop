//! The player's installed mods: read `mod-status.json`, say which one wins.
//!
//! The one fact a player cannot learn anywhere else is WHICH data mod the next
//! match will actually load.  The game hides that in a dropdown on the
//! create-game screen; the mods screen has no such dropdown.  So this reports,
//! for every enabled mod that ships a `.dat`, its rank among the competitors --
//! naming the winner, not just counting the field.
//!
//! Read-only: nothing here writes the player's profile.  Enabling, reordering
//! and uninstalling are separate routes precisely because they change a file the
//! game also writes when it exits.

use std::fs;
use std::io;
use std::path::{Path, PathBuf};

/// One row as the screen shows it.
#[derive(Debug, Clone, Default)]
pub struct ModRow {
    pub name: String,
    pub title: String,
    pub enabled: bool,
    pub kind: String,
    pub priority: i64,
    pub ships_dat: bool,
    pub dat_rank: Option<usize>,
    pub dat_competing: usize,
    /// The `（界面）` half of a split build, tied to `pair_base`.
    pub pair_base: Option<String>,
}

/// The player's profile directory, which holds `mods/mod-status.json`.
///
/// Located by scanning `Documents/Games/Age of Empires 2 DE/<steam id>/`, since
/// the id differs per account and hardcoding one would work on exactly this
/// machine.
///
/// `AOE2MOD_PROFILE` points at ONE account directory (the one holding `mods/`).
/// When it is set, it is the ONLY answer: a set-but-unusable override returns
/// `None` instead of falling through to the real profile.  Falling through is
/// how a test that meant to use a sandbox wrote an entry into the player's own
/// mod list -- the caller had declared where it wanted to write, the layout was
/// one level off, and nothing said so.
pub fn profile_root() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_PROFILE") {
        if v.is_empty() {
            return None;
        }
        let p = PathBuf::from(&v);
        if p.join("mods/mod-status.json").is_file() {
            return Some(p);
        }
        // Say which level is expected: the account folder itself, not the
        // `Age of Empires 2 DE` folder above it.
        eprintln!(
            "AOE2MOD_PROFILE={v} 里面没有 mods\\mod-status.json。\
             它要指到存账号文件夹那一层（本该有 mods\\ 的那一级），不是它的上一层。\
             因为已经指定了档案目录，就不再退回真实档案。"
        );
        return None;
    }
    let base = PathBuf::from(std::env::var("USERPROFILE").ok()?)
        .join("Games/Age of Empires 2 DE");
    let entries = fs::read_dir(&base).ok()?;
    for e in entries.flatten() {
        let p = e.path();
        if p.join("mods/mod-status.json").is_file() {
            return Some(p);
        }
    }
    None
}

/// Parse `mod-status.json` into rows, then decide ranks.
///
/// Hand-rolled scanning rather than serde: the file's shape is fixed, it is
/// written by the game, and pulling a derive dependency in to read three fields
/// would be more machinery than the format deserves.  A malformed file yields
/// whatever rows could be read rather than an error, because a mod list that
/// refuses to load is worse than one that is missing a row.
pub fn read_mods(profile: &Path) -> io::Result<Vec<ModRow>> {
    let path = profile.join("mods/mod-status.json");
    let text = fs::read_to_string(&path)?;
    let mut rows = Vec::new();

    let mods_at = match text.find("\"Mods\"") {
        Some(i) => i,
        None => return Ok(rows),
    };
    let arr_start = match text[mods_at..].find('[') {
        Some(i) => mods_at + i,
        None => return Ok(rows),
    };
    let arr_end = match matching_bracket(&text, arr_start) {
        Some(i) => i,
        None => return Ok(rows),
    };
    let body = &text[arr_start + 1..arr_end];

    let mut i = 0usize;
    while let Some(open) = body[i..].find('{') {
        let start = i + open;
        let end = match matching_brace(body, start) {
            Some(e) => e,
            None => break,
        };
        let obj = &body[start + 1..end];
        let mut row = ModRow {
            name: field_str(obj, "Path").unwrap_or_default(),
            title: field_str(obj, "Title").unwrap_or_default(),
            enabled: field_bool(obj, "Enabled").unwrap_or(false),
            priority: field_int(obj, "Priority").unwrap_or(0),
            ..Default::default()
        };
        // `Path` is `local//<name>` or `subscribed//<name>`; the kind is the
        // prefix and the name is what follows, which is what every other route
        // uses as the key.
        if let Some((kind, rest)) = row.name.split_once("//") {
            row.kind = kind.to_string();
            row.name = rest.to_string();
        }
        if row.title.is_empty() {
            row.title = row.name.clone();
        }
        rows.push(row);
        i = end + 1;
    }

    // Which mods ship a .dat, i.e. compete for the single data-mod slot.
    for row in rows.iter_mut() {
        let dir = profile.join("mods").join(if row.kind.is_empty() {
            "local"
        } else {
            &row.kind
        }).join(&row.name);
        row.ships_dat = dir
            .join("resources/_common/dat/empires2_x2_p1.dat")
            .is_file();
    }

    // Rank the ENABLED data mods by priority: highest wins a shared path, and
    // that is decided by the game, not by this tool.
    let mut live: Vec<usize> = rows
        .iter()
        .enumerate()
        .filter(|(_, r)| r.ships_dat && r.enabled)
        .map(|(i, _)| i)
        .collect();
    live.sort_by_key(|&i| -rows[i].priority);
    let competing = live.len();
    for (rank, &i) in live.iter().enumerate() {
        rows[i].dat_rank = Some(rank + 1);
    }
    for row in rows.iter_mut() {
        row.dat_competing = competing;
    }

    // A split build is two folders; the interface half is titled `<base>（界面）`
    // and that suffix is the only thing on disk tying them together.
    let bases: Vec<String> = rows
        .iter()
        .filter(|r| !r.title.ends_with("（界面）"))
        .map(|r| r.title.clone())
        .collect();
    for row in rows.iter_mut() {
        if let Some(base) = row.title.strip_suffix("（界面）") {
            if bases.iter().any(|b| b == base) {
                row.pair_base = Some(base.to_string());
            }
        }
    }

    Ok(rows)
}

pub fn to_json(rows: &[ModRow]) -> String {
    let items: Vec<String> = rows
        .iter()
        .map(|r| {
            let rank = match r.dat_rank {
                Some(v) => v.to_string(),
                None => "null".into(),
            };
            let pair = match &r.pair_base {
                Some(v) => format!("\"{}\"", crate::server::json_escape(v)),
                None => "null".into(),
            };
            format!(
                "{{\"name\":\"{}\",\"title\":\"{}\",\"enabled\":{},\"kind\":\"{}\",\"priority\":{},\"ships_dat\":{},\"dat_rank\":{},\"dat_competing\":{},\"pair_base\":{}}}",
                crate::server::json_escape(&r.name),
                crate::server::json_escape(&r.title),
                r.enabled,
                crate::server::json_escape(&r.kind),
                r.priority,
                r.ships_dat,
                rank,
                r.dat_competing,
                pair
            )
        })
        .collect();
    format!("[{}]", items.join(","))
}

fn matching_bracket(s: &str, open: usize) -> Option<usize> {
    let b = s.as_bytes();
    let mut depth = 0i32;
    let mut in_str = false;
    for i in open..b.len() {
        match b[i] {
            b'"' if i == 0 || b[i - 1] != b'\\' => in_str = !in_str,
            b'[' if !in_str => depth += 1,
            b']' if !in_str => {
                depth -= 1;
                if depth == 0 {
                    return Some(i);
                }
            }
            _ => {}
        }
    }
    None
}

fn matching_brace(s: &str, open: usize) -> Option<usize> {
    let b = s.as_bytes();
    let mut depth = 0i32;
    let mut in_str = false;
    for i in open..b.len() {
        match b[i] {
            b'"' if i == 0 || b[i - 1] != b'\\' => in_str = !in_str,
            b'{' if !in_str => depth += 1,
            b'}' if !in_str => {
                depth -= 1;
                if depth == 0 {
                    return Some(i);
                }
            }
            _ => {}
        }
    }
    None
}

fn field_str(obj: &str, name: &str) -> Option<String> {
    let pat = format!("\"{name}\"");
    let a = obj.find(&pat)? + pat.len();
    let rest = &obj[a..];
    let colon = rest.find(':')?;
    let tail = rest[colon + 1..].trim_start();
    let tail = tail.strip_prefix('"')?;
    let end = tail.find('"')?;
    Some(tail[..end].to_string())
}

fn field_int(obj: &str, name: &str) -> Option<i64> {
    let pat = format!("\"{name}\"");
    let a = obj.find(&pat)? + pat.len();
    let rest = &obj[a..];
    let colon = rest.find(':')?;
    let tail = rest[colon + 1..].trim_start();
    let tail = tail.strip_prefix('"').unwrap_or(tail);
    let end = tail
        .find(|c: char| !c.is_ascii_digit() && c != '-')
        .unwrap_or(tail.len());
    tail[..end].parse().ok()
}

fn field_bool(obj: &str, name: &str) -> Option<bool> {
    let pat = format!("\"{name}\"");
    let a = obj.find(&pat)? + pat.len();
    let rest = &obj[a..];
    let colon = rest.find(':')?;
    let tail = rest[colon + 1..].trim_start();
    if tail.starts_with("true") {
        Some(true)
    } else if tail.starts_with("false") {
        Some(false)
    } else {
        None
    }
}


// ---------------------------------------------------------------------------
// Writing: enable / disable, move in load order, uninstall
// ---------------------------------------------------------------------------

/// Turn an installed mod on or off without moving it in the list.
///
/// Disabling is not deleting: the entry stays (the engine keeps a disabled mod in
/// the list, greyed out) and its position is preserved, so re-enabling restores
/// exactly the conflict order the player had.
///
/// A name that matches NOTHING is REFUSED instead of created. `upsert` creates an
/// entry when it finds none, which is what installing wants and the opposite of
/// what toggling means: measured 2026-10-20, toggling a name that did not exist
/// inserted a phantom entry at Priority 1 of the player's real list, pointing at
/// a folder that is not there, reported to the caller as ok. A folder the player
/// dropped into `mods/local` by hand still works, because the game registers
/// those itself -- so the folder on disk is the second half of "does this exist".
pub fn set_enabled(profile: &Path, name: &str, enabled: bool) -> Result<ModRow, String> {
    let rows = read_mods(profile).map_err(|e| e.to_string())?;
    let (fname, fkind, ftitle) = match rows.iter().find(|r| r.name == name || r.title == name) {
        Some(r) => (r.name.clone(), r.kind.clone(), r.title.clone()),
        None => {
            let dir = profile.join("mods/local").join(name);
            if !dir.is_dir() {
                return Err(format!(
                    "没找到叫「{name}」的模组：模组列表里没有它，模组文件夹里也没有这个文件夹。它可能已经被删掉或者改名了，刷新一下列表再试。"
                ));
            }
            (name.to_string(), "local".to_string(), name.to_string())
        }
    };
    let path = profile.join("mods/mod-status.json");
    let text = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let rel = format!("{}//{}", if fkind.is_empty() { "local" } else { &fkind }, fname);
    let doc = if text.contains(&format!("\"{rel}\"")) {
        set_bool_in_entry(&text, &rel, enabled)
    } else {
        insert_status_entry(&text, &rel, &ftitle, enabled)?
    };
    write_status(&path, &text, &doc)?;
    Ok(ModRow {
        name: fname,
        title: ftitle,
        kind: fkind,
        enabled,
        ..Default::default()
    })
}

/// Move a mod one step in load order. `delta = -1` is up (higher priority, wins
/// a shared path), `+1` is down.
pub fn move_mod(profile: &Path, name: &str, delta: i64) -> Result<(), String> {
    let path = profile.join("mods/mod-status.json");
    let text = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut entries = parse_entries(&text);
    let pos = entries
        .iter()
        .position(|e| e.name == name || e.title == name)
        .ok_or_else(|| format!("模组列表里没有「{name}」。"))?;
    let target = pos as i64 + delta;
    if target < 0 || target as usize >= entries.len() {
        // Already at an end: nothing to do, and not an error.
        return Ok(());
    }
    let e = entries.remove(pos);
    entries.insert(target as usize, e);
    let doc = rebuild_status(&text, &entries);
    write_status(&path, &text, &doc)
}

/// Remove a mod folder and its entry.
///
/// A split build is TWO folders (`<base>` and `<base>（界面）`), and that suffix is
/// the only thing on disk tying them together. Deleting one half of an installed
/// pair leaves a folder that renders an empty command card, so both go.
pub fn uninstall(profile: &Path, name: &str) -> Result<Vec<String>, String> {
    let rows = read_mods(profile).map_err(|e| e.to_string())?;
    let mut targets: Vec<String> = vec![name.to_string()];
    if let Some(base) = name.strip_suffix("（界面）") {
        targets.push(base.to_string());
    } else {
        let ui = format!("{name}（界面）");
        if rows.iter().any(|r| r.name == ui || r.title == ui) {
            targets.push(ui);
        }
    }
    let mut removed = Vec::new();
    let path = profile.join("mods/mod-status.json");
    let mut text = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let before = text.clone();
    for t in &targets {
        let row = rows.iter().find(|r| &r.name == t || &r.title == t);
        let kind = row.map(|r| r.kind.clone()).unwrap_or_else(|| "local".into());
        let dir = profile
            .join("mods")
            .join(if kind.is_empty() { "local".to_string() } else { kind.clone() })
            .join(t);
        if dir.is_dir() {
            fs::remove_dir_all(&dir).map_err(|e| format!("删不掉 {}：{e}", dir.display()))?;
            removed.push(t.clone());
        }
        let mut entries = parse_entries(&text);
        entries.retain(|e| &e.name != t && &e.title != t);
        text = rebuild_status(&text, &entries);
    }
    write_status(&path, &before, &text)?;
    Ok(removed)
}

/// One entry, as the status file spells it.
#[derive(Debug, Clone)]
pub struct Entry {
    pub name: String,
    pub title: String,
    pub kind: String,
    pub enabled: bool,
    pub priority: i64,
}

fn parse_entries(text: &str) -> Vec<Entry> {
    let mut out = Vec::new();
    let at = match text.find("\"Mods\"") {
        Some(a) => a,
        None => return out,
    };
    let lb = match text[at..].find('[') {
        Some(v) => v + at,
        None => return out,
    };
    let rb = match matching_brace_or_bracket(text, lb) {
        Some(v) => v,
        None => return out,
    };
    let body = &text[lb + 1..rb];
    let mut i = 0usize;
    while let Some(open) = body[i..].find('{') {
        let s = i + open;
        let e = match matching_brace_or_bracket(body, s) {
            Some(v) => v,
            None => break,
        };
        let obj = &body[s + 1..e];
        let raw_path = field_str(obj, "Path").unwrap_or_default();
        let (kind, name) = match raw_path.split_once("//") {
            Some((k, n)) => (k.to_string(), n.to_string()),
            None => (String::new(), raw_path.clone()),
        };
        out.push(Entry {
            name: name.clone(),
            title: field_str(obj, "Title").unwrap_or(name),
            kind,
            enabled: field_bool(obj, "Enabled").unwrap_or(false),
            priority: field_int(obj, "Priority").unwrap_or(0),
        });
        i = e + 1;
    }
    out
}

fn rebuild_status(template: &str, entries: &[Entry]) -> String {
    let at = match template.find("\"Mods\"") {
        Some(a) => a,
        None => return template.to_string(),
    };
    let lb = match template[at..].find('[') {
        Some(v) => v + at,
        None => return template.to_string(),
    };
    let rb = match matching_brace_or_bracket(template, lb) {
        Some(v) => v,
        None => return template.to_string(),
    };
    let items: Vec<String> = entries
        .iter()
        .enumerate()
        .map(|(i, e)| {
            format!(
                "{{\"CheckSum\":\"0\",\"Enabled\":{},\"LastUpdate\":\"{}\",\"Path\":\"{}//{}\",\"Priority\":{},\"PublishID\":0,\"Title\":\"{}\",\"WorkshopID\":0}}",
                e.enabled,
                now_ms(),
                if e.kind.is_empty() { "local" } else { &e.kind },
                crate::server::json_escape(&e.name),
                i + 1,
                crate::server::json_escape(&e.title)
            )
        })
        .collect();
    format!("{}{}{}", &template[..lb + 1], items.join(","), &template[rb..])
}

fn insert_status_entry(
    text: &str,
    rel: &str,
    title: &str,
    enabled: bool,
) -> Result<String, String> {
    let at = text.find("\"Mods\"").ok_or("mod-status.json 里没有 Mods")?;
    let lb = text[at..].find('[').ok_or("Mods 不是数组")? + at;
    let entry = format!(
        "{{\"CheckSum\":\"0\",\"Enabled\":{},\"LastUpdate\":\"{}\",\"Path\":\"{}\",\"Priority\":1,\"PublishID\":0,\"Title\":\"{}\",\"WorkshopID\":0}}",
        enabled,
        now_ms(),
        rel,
        crate::server::json_escape(title)
    );
    let mut out = String::new();
    out.push_str(&text[..lb + 1]);
    out.push_str(&entry);
    let rest = &text[lb + 1..];
    if rest.trim_start().starts_with(']') {
        out.push_str(rest);
    } else {
        out.push(',');
        out.push_str(rest);
    }
    let entries = parse_entries(&out);
    Ok(rebuild_status(&out, &entries))
}

fn set_bool_in_entry(text: &str, rel: &str, value: bool) -> String {
    let rel_q = format!("\"{rel}\"");
    let p = match text.find(&rel_q) {
        Some(v) => v,
        None => return text.to_string(),
    };
    let obj_start = match text[..p].rfind('{') {
        Some(v) => v,
        None => return text.to_string(),
    };
    let obj_end = match matching_brace_or_bracket(text, obj_start) {
        Some(v) => v,
        None => return text.to_string(),
    };
    let obj = &text[obj_start..obj_end];
    let pat = "\"Enabled\":";
    let q = match obj.find(pat) {
        Some(v) => v,
        None => return text.to_string(),
    };
    let after = q + pat.len();
    let tail = &obj[after..];
    let trimmed = tail.trim_start();
    let lead = tail.len() - trimmed.len();
    let rest = if trimmed.starts_with("true") {
        &trimmed[4..]
    } else if trimmed.starts_with("false") {
        &trimmed[5..]
    } else {
        return text.to_string();
    };
    let mut fixed = String::new();
    fixed.push_str(&obj[..after]);
    fixed.push_str(&obj[after..after + lead]);
    fixed.push_str(if value { "true" } else { "false" });
    fixed.push_str(rest);
    format!("{}{}{}", &text[..obj_start], fixed, &text[obj_end..])
}

fn write_status(path: &Path, before: &str, doc: &str) -> Result<(), String> {
    // One guard, one writer: `build.rs` installs mods into the same file, and a
    // second copy of the parse check is a second place for it to drift.
    crate::build::checked_status_write(path, before, doc)
}

fn now_ms() -> String {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis().to_string())
        .unwrap_or_else(|_| "0".into())
}

fn matching_brace_or_bracket(s: &str, open: usize) -> Option<usize> {
    let b = s.as_bytes();
    if open >= b.len() {
        return None;
    }
    let (o, c) = match b[open] {
        b'{' => (b'{', b'}'),
        b'[' => (b'[', b']'),
        _ => return None,
    };
    let mut depth = 0i32;
    let mut in_str = false;
    for i in open..b.len() {
        match b[i] {
            b'"' if i == 0 || b[i - 1] != b'\\' => in_str = !in_str,
            x if x == o && !in_str => depth += 1,
            x if x == c && !in_str => {
                depth -= 1;
                if depth == 0 {
                    return Some(i);
                }
            }
            _ => {}
        }
    }
    None
}
