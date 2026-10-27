//! Named recipes: the sentences a player saves, in the same file the Python
//! engine uses.
//!
//! Why sentences and not intents
//! -----------------------------
//! The reader is the only thing that decides what a sentence means, and a recipe
//! that stored resolved intents would be a second interpretation kept in sync by
//! hand. Saving the sentences means a recipe is exactly as correct as the reader
//! on the day it runs -- and if the reader gets stricter, the recipe fails loudly
//! at parse time instead of quietly building something else.
//!
//! Why the same file
//! -----------------
//! `recipes.json` already exists beside `builds.json`, written by the Python
//! engine. A native server that invented its own store would split a player's
//! saved names between two implementations, and whichever one they opened next
//! would look like it had lost them. So this reads and writes that exact file,
//! and a document it cannot parse reads as empty rather than erroring -- the
//! worst case is that names disappear, which is recoverable and visible, whereas
//! refusing to start is neither.

use std::fs;
use std::io;
use std::path::PathBuf;

const FILE_NAME: &str = "recipes.json";
const MAX_NAME: usize = 24;

#[derive(Debug, Clone, Default)]
pub struct Recipe {
    pub name: String,
    pub sentences: Vec<String>,
    pub saved_at: String,
    pub note: String,
}

/// The state directory the Python engine already uses, so both implementations
/// agree on where a player's names live.
pub fn state_dir() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_STATE") {
        return Some(PathBuf::from(v));
    }
    let base = std::env::var("LOCALAPPDATA").ok()?;
    Some(PathBuf::from(base).join("aoe2de-mod-workshop"))
}

pub fn path() -> Option<PathBuf> {
    Some(state_dir()?.join(FILE_NAME))
}

/// Every recipe, oldest name first.
pub fn rows() -> io::Result<Vec<Recipe>> {
    let p = match path() {
        Some(p) => p,
        None => return Ok(Vec::new()),
    };
    let text = match fs::read_to_string(&p) {
        Ok(t) => t,
        // A missing file is not an error: a player who has never saved a
        // recipe has an empty list, which is exactly what this returns.
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(e),
    };
    let mut out = read_doc(&text);
    out.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(out)
}

/// Save or replace one recipe.
pub fn remember(name: &str, sentences: Vec<String>, note: &str) -> Result<Recipe, String> {
    let clean = name.trim();
    if clean.is_empty() {
        return Err("配方要有个名字，不然下次没法叫它出来。".into());
    }
    if clean.chars().count() > MAX_NAME {
        return Err(format!(
            "配方名最多 {MAX_NAME} 个字，现在有 {} 个。",
            clean.chars().count()
        ));
    }
    let mut seen = Vec::new();
    for s in sentences {
        let t = s.trim();
        if !t.is_empty() && !seen.iter().any(|x: &String| x == t) {
            seen.push(t.to_string());
        }
    }
    if seen.is_empty() {
        return Err("这个配方一句都没有，存下来也没有东西可以重建。".into());
    }

    let p = path().ok_or("找不到状态目录")?;
    if let Some(dir) = p.parent() {
        fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    let mut all = if p.is_file() {
        read_doc(&fs::read_to_string(&p).map_err(|e| e.to_string())?)
    } else {
        Vec::new()
    };
    let stamped = now_stamp();
    let row = Recipe {
        name: clean.to_string(),
        sentences: seen,
        saved_at: stamped,
        note: note.trim().to_string(),
    };
    all.retain(|r| r.name != clean);
    all.push(row.clone());
    write_doc(&p, &all).map_err(|e| e.to_string())?;
    Ok(row)
}

pub fn forget(name: &str) -> Result<bool, String> {
    let p = match path() {
        Some(p) => p,
        None => return Ok(false),
    };
    if !p.is_file() {
        return Ok(false);
    }
    let mut all = read_doc(&fs::read_to_string(&p).map_err(|e| e.to_string())?);
    let before = all.len();
    all.retain(|r| r.name != name.trim());
    let removed = all.len() != before;
    if removed {
        write_doc(&p, &all).map_err(|e| e.to_string())?;
    }
    Ok(removed)
}

fn now_stamp() -> String {
    // `%Y-%m-%d %H:%M`, the same shape the Python engine writes, so a file
    // touched by either implementation reads the same in the other.
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = now / 86400;
    let secs = now % 86400;
    let (y, m, d) = civil_from_days(days as i64);
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02}",
        y,
        m,
        d,
        secs / 3600,
        (secs % 3600) / 60
    )
}

/// Howard Hinnant's days-from-civil, inverted.  Avoids a chrono dependency for
/// one timestamp.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

fn read_doc(text: &str) -> Vec<Recipe> {
    // `{"recipes": {"<name>": {"sentences": [...], "saved_at": ..., "note": ...}}}`
    let mut out = Vec::new();
    let at = match text.find("\"recipes\"") {
        Some(i) => i,
        None => return out,
    };
    let obj_start = match text[at..].find('{') {
        Some(i) => at + i,
        None => return out,
    };
    let obj_end = match matching(text, obj_start, b'{', b'}') {
        Some(i) => i,
        None => return out,
    };
    let body = &text[obj_start + 1..obj_end];

    let mut i = 0usize;
    while let Some(q) = body[i..].find('"') {
        let name_start = i + q + 1;
        let name_end = match body[name_start..].find('"') {
            Some(e) => name_start + e,
            None => break,
        };
        let name = body[name_start..name_end].to_string();
        let after = name_end + 1;
        let inner = match body[after..].find('{') {
            Some(o) => after + o,
            None => break,
        };
        let inner_end = match matching(body, inner, b'{', b'}') {
            Some(e) => e,
            None => break,
        };
        let obj = &body[inner + 1..inner_end];
        out.push(Recipe {
            name,
            sentences: str_array(obj, "sentences"),
            saved_at: str_field(obj, "saved_at").unwrap_or_default(),
            note: str_field(obj, "note").unwrap_or_default(),
        });
        i = inner_end + 1;
    }
    out
}

fn write_doc(p: &std::path::Path, rows: &[Recipe]) -> io::Result<()> {
    let mut items: Vec<String> = Vec::new();
    for r in rows {
        let sents: Vec<String> = r
            .sentences
            .iter()
            .map(|s| format!("\"{}\"", crate::server::json_escape(s)))
            .collect();
        items.push(format!(
            "\"{}\":{{\"sentences\":[{}],\"saved_at\":\"{}\",\"note\":\"{}\"}}",
            crate::server::json_escape(&r.name),
            sents.join(","),
            crate::server::json_escape(&r.saved_at),
            crate::server::json_escape(&r.note)
        ));
    }
    let text = format!("{{\"recipes\":{{{}}}}}\n", items.join(","));
    // Write beside, then rename: a half-written recipe file would lose every
    // name the player ever saved, and that is not recoverable from anywhere.
    let tmp = p.with_extension("json.tmp");
    fs::write(&tmp, text)?;
    fs::rename(&tmp, p)
}

fn matching(s: &str, open: usize, o: u8, c: u8) -> Option<usize> {
    let b = s.as_bytes();
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

fn str_field(obj: &str, name: &str) -> Option<String> {
    let pat = format!("\"{name}\"");
    let a = obj.find(&pat)? + pat.len();
    let rest = &obj[a..];
    let colon = rest.find(':')?;
    let tail = rest[colon + 1..].trim_start().strip_prefix('"')?;
    let end = tail.find('"')?;
    Some(tail[..end].to_string())
}

fn str_array(obj: &str, name: &str) -> Vec<String> {
    let mut out = Vec::new();
    let pat = format!("\"{name}\"");
    let a = match obj.find(&pat) {
        Some(i) => i + pat.len(),
        None => return out,
    };
    let rest = &obj[a..];
    let lb = match rest.find('[') {
        Some(i) => i,
        None => return out,
    };
    let rb = match matching(rest, lb, b'[', b']') {
        Some(i) => i,
        None => return out,
    };
    let body = &rest[lb + 1..rb];
    let mut i = 0usize;
    while let Some(q) = body[i..].find('"') {
        let start = i + q + 1;
        let end = match body[start..].find('"') {
            Some(e) => start + e,
            None => break,
        };
        out.push(body[start..end].to_string());
        i = end + 1;
    }
    out
}
