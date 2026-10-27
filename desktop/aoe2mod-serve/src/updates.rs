//! `/api/update-check`: has the game's data moved since a mod was built?
//!
//! Why this exists
//! ---------------
//! A data mod ships a whole copy of `empires2_x2_p1.dat`. When the game updates,
//! that copy is stale and it OVERRIDES the update -- the player sees the new
//! version number and none of the new content, or the game cannot start. Nothing
//! in the game tells them which mod did it.
//!
//! The five states, and why "unknown" is not "needs attention"
//! ----------------------------------------------------------
//! `current` / `stale` / `edited` / `unknown` / `no_dat`. An unknown row is
//! honestly unknowable (a mod this tool did not build, or the record was
//! deleted), and shouting about it would train the player to ignore the banner.
//! `needs_attention` therefore counts only `stale` and `edited`.
//!
//! Two rules that are easy to get backwards
//! ---------------------------------------
//!   * A mod that ships NO `.dat` cannot go stale: an official update cannot
//!     invalidate loose sprites or tree JSON.
//!   * A `.dat` whose FILE hash changed but whose CONTENT hash did not is
//!     `current`, not stale. The game re-packs the file on some updates (same
//!     bytes, different deflate), and reporting that as "rebuild it" trains the
//!     player to ignore the banner too. That is why the deep check exists.

use sha2::{Digest, Sha256};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    Current,
    Stale,
    Edited,
    Unknown,
    NoDat,
}

impl Status {
    pub fn as_str(self) -> &'static str {
        match self {
            Status::Current => "current",
            Status::Stale => "stale",
            Status::Edited => "edited",
            Status::Unknown => "unknown",
            Status::NoDat => "no_dat",
        }
    }
}

pub struct Row {
    pub name: String,
    pub title: String,
    pub kind: String,
    pub enabled: bool,
    pub status: Status,
    pub detail: String,
    pub fixable: bool,
    pub built_at: Option<String>,
    pub built_version: Option<String>,
    pub installed_dat: Option<String>,
}

fn sha256_file(p: &Path) -> Option<String> {
    let mut f = fs::File::open(p).ok()?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut buf).ok()?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Some(format!("{:x}", h.finalize()))
}

/// `(file_sha256, raw_sha256)` of a `.dat`, and its version string.
///
/// The file hash is of the bytes on disk (raw-deflated); the raw hash is of the
/// DECOMPRESSED stream. Both are needed: the first detects "someone replaced the
/// file", the second detects "the game re-packed it with identical content".
pub fn fingerprint(dat: &Path, deep: bool) -> Option<(String, Option<String>, Option<String>)> {
    let file = sha256_file(dat)?;
    if !deep {
        return Some((file, None, version_of(dat)));
    }
    let blob = fs::read(dat).ok()?;
    let raw = inflate(&blob).or_else(|| if blob.starts_with(b"VER ") { Some(blob) } else { None })?;
    let mut h = Sha256::new();
    h.update(&raw);
    let raw_hex = format!("{:x}", h.finalize());
    let ver = if raw.len() >= 8 {
        let s = String::from_utf8_lossy(&raw[..8]);
        Some(s.trim_end_matches('\u{0}').trim().to_string())
    } else {
        None
    };
    Some((file, Some(raw_hex), ver))
}

fn version_of(dat: &Path) -> Option<String> {
    // The version string is in the first 8 bytes of the DECOMPRESSED stream, so
    // reading it means inflating at least the head. Cheap: 145 KB is the whole
    // first stage.
    let blob = fs::read(dat).ok()?;
    if blob.starts_with(b"VER ") {
        return Some(String::from_utf8_lossy(&blob[..8]).trim_end_matches('\u{0}').trim().to_string());
    }
    let mut d = flate2::read::DeflateDecoder::new(&blob[..]);
    let mut head = [0u8; 8];
    d.read_exact(&mut head).ok()?;
    Some(String::from_utf8_lossy(&head).trim_end_matches('\u{0}').trim().to_string())
}

fn inflate(blob: &[u8]) -> Option<Vec<u8>> {
    let mut d = flate2::read::DeflateDecoder::new(blob);
    let mut out = Vec::new();
    d.read_to_end(&mut out).ok()?;
    Some(out)
}

/// The builds record: `name -> {changes_dat, dat_is_carrier, ...}`.
///
/// Read with serde_json because a hand scanner that gets this wrong returns no
/// entries, and "no entries" means every mod reports `unknown` -- which is the
/// one status that deliberately does NOT raise attention, so the failure would
/// be invisible.
fn load_builds(path: &Path) -> serde_json::Map<String, serde_json::Value> {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => return serde_json::Map::new(),
    };
    let v: serde_json::Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => return serde_json::Map::new(),
    };
    v.get("builds")
        .and_then(|b| b.as_object())
        .cloned()
        .unwrap_or_default()
}

pub fn state_file() -> Option<PathBuf> {
    let base = std::env::var("LOCALAPPDATA").ok()?;
    Some(PathBuf::from(base).join("aoe2de-mod-workshop/builds.json"))
}

/// Compare every installed mod against the game's data right now.
pub fn check(profile: &Path, game_dat: &Path, deep: bool) -> Result<(Vec<Row>, usize), String> {
    let (cur_file, cur_raw, cur_ver) =
        fingerprint(game_dat, deep).ok_or("读不到游戏的 .dat")?;
    let builds = load_builds(&state_file().ok_or("找不到状态目录")?);
    let mods = crate::mods::read_mods(profile).map_err(|e| e.to_string())?;

    let mut rows = Vec::new();
    let mut attention = 0usize;
    for m in mods {
        let entry = builds
            .get(&m.name)
            .or_else(|| builds.get(&m.title))
            .and_then(|v| v.as_object());
        let mut row = Row {
            name: m.name.clone(),
            title: m.title.clone(),
            kind: m.kind.clone(),
            enabled: m.enabled,
            status: Status::Unknown,
            detail: String::new(),
            fixable: false,
            built_at: None,
            built_version: None,
            installed_dat: None,
        };
        let kind_dir = if m.kind.is_empty() { "local" } else { &m.kind };
        let installed = profile
            .join("mods")
            .join(kind_dir)
            .join(&m.name)
            .join("resources/_common/dat/empires2_x2_p1.dat");
        if installed.is_file() {
            row.installed_dat = Some(installed.display().to_string());
        }

        let entry = match entry {
            Some(e) => e,
            None => {
                row.detail =
                    "没有任何构建记录：这份模组不是本工具建的，或者记录文件被删了".into();
                rows.push(row);
                continue;
            }
        };
        row.built_at = entry.get("built_at").and_then(|v| v.as_str()).map(|s| s.to_string());
        row.built_version = entry
            .get("base_version")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());
        row.fixable = true;

        let ships_dat = entry.get("changes_dat").and_then(|v| v.as_bool()).unwrap_or(false)
            || entry.get("dat_is_carrier").and_then(|v| v.as_bool()).unwrap_or(false);
        if !ships_dat || row.installed_dat.is_none() {
            row.status = Status::NoDat;
            row.detail =
                "这份模组不带 .dat（只发松散文件），官方更新不会让它失效".into();
            row.fixable = false;
            rows.push(row);
            continue;
        }

        // Did the mod's own copy change since it was emitted?
        let installed_path = PathBuf::from(row.installed_dat.as_ref().unwrap());
        let have = sha256_file(&installed_path);
        let want = entry.get("dat_file_sha256").and_then(|v| v.as_str());
        if let (Some(w), Some(h)) = (want, have.as_ref()) {
            if w != h {
                row.status = Status::Edited;
                row.detail =
                    "装着的这份 .dat 和本工具发出去的不是同一个文件（可能被别的模组或手工覆盖过）；重建会覆盖它"
                        .into();
                attention += 1;
                rows.push(row);
                continue;
            }
        }

        let base_file = entry.get("base_file_sha256").and_then(|v| v.as_str());
        if base_file == Some(cur_file.as_str()) {
            row.status = Status::Current;
            row.detail = "按游戏现在这份数据建的".into();
            rows.push(row);
            continue;
        }

        // The file changed. Same content re-compressed, or new data?
        let same_content = match (cur_raw.as_ref(), entry.get("base_raw_sha256").and_then(|v| v.as_str())) {
            (Some(now), Some(then)) => now == then,
            _ => false,
        };
        if same_content {
            row.status = Status::Current;
            row.detail = "游戏重新打包过 .dat，内容没变，不用重建".into();
            rows.push(row);
            continue;
        }

        row.status = Status::Stale;
        let now_s = cur_ver.clone().unwrap_or_else(|| "?".into());
        let then_s = row.built_version.clone().unwrap_or_else(|| "?".into());
        row.detail = if now_s != then_s {
            format!(
                "游戏数据从 {then_s} 更新到了 {now_s}；这份模组带着旧的一整份 .dat，会把更新盖掉"
            )
        } else {
            format!(
                "游戏数据更新过（版本号还是 {now_s}，但内容变了）；这份模组带着旧的一整份 .dat，会把更新盖掉"
            )
        };
        attention += 1;
        rows.push(row);
    }
    Ok((rows, attention))
}

pub fn to_json(rows: &[Row], attention: usize, state_dir: &str) -> String {
    let items: Vec<String> = rows
        .iter()
        .map(|r| {
            let opt = |v: &Option<String>| match v {
                Some(s) => format!("\"{}\"", crate::server::json_escape(s)),
                None => "null".into(),
            };
            format!(
                "{{\"name\":\"{}\",\"title\":\"{}\",\"kind\":\"{}\",\"enabled\":{},\"status\":\"{}\",\"detail\":\"{}\",\"fixable\":{},\"built_at\":{},\"built_version\":{},\"installed_dat\":{}}}",
                crate::server::json_escape(&r.name),
                crate::server::json_escape(&r.title),
                crate::server::json_escape(&r.kind),
                r.enabled,
                r.status.as_str(),
                crate::server::json_escape(&r.detail),
                r.fixable,
                opt(&r.built_at),
                opt(&r.built_version),
                opt(&r.installed_dat)
            )
        })
        .collect();
    format!(
        "{{\"ok\":true,\"state_dir\":\"{}\",\"rows\":[{}],\"needs_attention\":{}}}",
        crate::server::json_escape(state_dir),
        items.join(","),
        attention
    )
}


/// Record one build: what was asked for, and which bytes it was built from.
///
/// `intents` is stored so a rebuild is the same REQUEST rather than a copy of the
/// bytes it produced -- a saved `.dat` is a snapshot of data the game can update
/// underneath it, while a saved intent is rebuilt against today's file.
///
/// Failures here are returned, not swallowed: a build that succeeded while its
/// record did not is a mod both guard routes cannot see.
#[allow(clippy::too_many_arguments)]
pub fn remember_build(
    title: &str,
    author: &str,
    description: &str,
    intents: serde_json::Value,
    base_file_sha: &str,
    base_raw_sha: Option<&str>,
    dat_out_sha: &str,
    changes_dat: bool,
) -> Result<(), String> {
    let path = state_file().ok_or("找不到状态目录")?;
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    let mut doc: serde_json::Value = if path.is_file() {
        let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
        serde_json::from_str(text.trim_start_matches('\u{feff}'))
            .unwrap_or_else(|_| serde_json::json!({"builds": {}}))
    } else {
        serde_json::json!({"builds": {}})
    };
    if !doc.get("builds").map(|b| b.is_object()).unwrap_or(false) {
        doc["builds"] = serde_json::json!({});
    }
    let entry = serde_json::json!({
        "title": title,
        "author": author,
        "description": description,
        "built_at": now_stamp(),
        "base_version": version_of(&std::path::PathBuf::from("")),
        "base_file_sha256": base_file_sha,
        "base_raw_sha256": base_raw_sha,
        "dat_file_sha256": dat_out_sha,
        "changes_dat": changes_dat,
        "dat_is_carrier": false,
        "intents": intents,
    });
    doc["builds"][title] = entry;
    let text = serde_json::to_string_pretty(&doc).map_err(|e| e.to_string())?;
    // Write beside, then rename: a half-written record file loses every mod the
    // guard knows about.
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, text).map_err(|e| e.to_string())?;
    std::fs::rename(&tmp, &path).map_err(|e| e.to_string())?;
    Ok(())
}

fn now_stamp() -> String {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}
