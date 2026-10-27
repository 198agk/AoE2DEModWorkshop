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
pub fn profile_root() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_PROFILE") {
        let p = PathBuf::from(v);
        if p.join("mods/mod-status.json").is_file() {
            return Some(p);
        }
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
