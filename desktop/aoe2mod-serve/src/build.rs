//! Build a mod folder and install it: the other half of the write path.
//!
//! Why the folder shape matters
//! ---------------------------
//! A data mod is `resources/_common/dat/empires2_x2_p1.dat`, raw-deflated, plus
//! an `info.json` with exactly four keys. Measured facts this repeats:
//!
//!   * `info.json` must be COMPACT (`{"Author":"x","CacheStatus":0,...}`). The
//!     indented shape is the one the game's own publisher cannot parse, and it
//!     then shows "Unpublished" / "No Description".
//!   * `CacheStatus` is 0 on all 21 mods installed on this machine, no
//!     exceptions. Writing 1 makes this tool the odd one out.
//!   * `Title` is truncated at 100 UTF-8 bytes and the game then looks for the
//!     truncated name, so an over-long title yields a mod that logs as enabled
//!     and changes nothing. Three bytes per Chinese character, so 33 characters
//!     is the budget.
//!   * Installing writes into the PLAYER's profile, so it is a separate decision
//!     from building, exactly as `api.build` and `api.install` are separate.
//!
//! What this deliberately does NOT do yet
//! -------------------------------------
//! Copy a thumbnail. The publish pipeline requires one at 1280x720, but a
//! locally installed mod does not, and generating a lie (a flat colour) would be
//! worse than not shipping one. The publish path is where that belongs.

use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

pub const DAT_REL: &str = "resources/_common/dat/empires2_x2_p1.dat";
const TITLE_MAX_BYTES: usize = 100;

/// One built mod, described by what actually landed on disk.
pub struct Built {
    pub dir: PathBuf,
    pub title: String,
    pub dat_bytes: usize,
    /// The raw-deflated bytes actually written to disk. Kept on the struct
    /// because the provenance record must hash THESE, not the uncompressed
    /// stream:  compares against the file, and hashing the wrong
    /// one made every fresh build look overwritten.
    pub compressed: Vec<u8>,
}

/// Write a data mod folder.
///
/// `dat_out` is the raw (uncompressed) `.dat` stream; it is deflated on the way
/// out because that is how the game stores and expects it.
pub fn build_data_mod(
    out_dir: &Path,
    dat_out: &[u8],
    title: &str,
    author: &str,
    description: &str,
    overwrite: bool,
) -> Result<Built, String> {
    if title.trim().is_empty() {
        return Err("模组要有个名字，不然装上去在列表里找不到。".into());
    }
    let n = title.as_bytes().len();
    if n > TITLE_MAX_BYTES {
        return Err(format!(
            "标题有 {n} 个字节，引擎在 {TITLE_MAX_BYTES} 字节处截断，\
             然后拿截断后的名字去找文件夹——那样做出来的模组日志里说已启用、\
             游戏里什么都不改。一个汉字 3 个字节，请缩短到 33 个字以内。",
        ));
    }
    for bad in ['<', '>', ':', '"', '/', '\\', '|', '?', '*'] {
        if title.contains(bad) {
            return Err(format!(
                "标题里有「{bad}」，它会变成文件夹名，这个字符在 Windows 文件名里不能用。"
            ));
        }
    }

    if out_dir.exists() {
        if !overwrite {
            let non_empty = fs::read_dir(out_dir)
                .map(|mut d| d.next().is_some())
                .unwrap_or(false);
            if non_empty {
                return Err(format!(
                    "这个模组文件夹已经存在，里面还有别的东西：{}。要整个换掉的话，\
                     调用时带上 overwrite。",
                    out_dir.display()
                ));
            }
        } else {
            // A rebuild must be a REPLACEMENT, not a merge: a stale file at an
            // old path is a mod that ships two copies of one picture and
            // nothing in the manifest says which is live.
            fs::remove_dir_all(out_dir).map_err(|e| e.to_string())?;
        }
    }

    let dat_path = out_dir.join(DAT_REL);
    if let Some(parent) = dat_path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let mut compressed = Vec::new();
    {
        use flate2::write::DeflateEncoder;
        use flate2::Compression;
        let mut e = DeflateEncoder::new(&mut compressed, Compression::default());
        e.write_all(dat_out).map_err(|e| e.to_string())?;
        e.finish().map_err(|e| e.to_string())?;
    }
    fs::write(&dat_path, &compressed).map_err(|e| e.to_string())?;

    // COMPACT, exactly like every mod the game ships and accepts.
    let info = format!(
        "{{\"Author\":\"{}\",\"CacheStatus\":0,\"Description\":\"{}\",\"Title\":\"{}\"}}",
        crate::server::json_escape(author),
        crate::server::json_escape(description),
        crate::server::json_escape(title)
    );
    fs::write(out_dir.join("info.json"), info).map_err(|e| e.to_string())?;

    Ok(Built {
        dir: out_dir.to_path_buf(),
        title: title.to_string(),
        dat_bytes: dat_out.len(),
        compressed,
    })
}

/// Copy a built mod into the player's profile and register it.
///
/// `position = 0` puts it at the TOP of the list, which is the highest priority:
/// the engine checks mods from the top and the first one holding a given file
/// wins. That is what "install this and play" means for a data mod.
pub fn install_local(profile: &Path, built: &Built, title: &str) -> Result<PathBuf, String> {
    if !profile.join("mods").is_dir() {
        return Err(format!(
            "这个目录不像是游戏档案：{}（里面没有 mods\\）。",
            profile.display()
        ));
    }
    let dest = profile.join("mods/local").join(title);
    if dest.exists() {
        fs::remove_dir_all(&dest).map_err(|e| e.to_string())?;
    }
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    copy_dir(&built.dir, &dest).map_err(|e| e.to_string())?;
    register(&profile.join("mods/mod-status.json"), title)?;
    Ok(dest)
}

/// Put an entry at the top of `Mods[]` and renumber, or update the one already
/// there.
///
/// The game registers a local mod folder it finds on disk, so a mod being
/// installed for the first time can ALREADY be in the list at the bottom and
/// disabled. Treating that as "an entry the user positioned by hand" leaves a
/// fresh install last, which is a real defect this project measured once.
fn register(status_path: &Path, title: &str) -> Result<(), String> {
    let text = if status_path.is_file() {
        fs::read_to_string(status_path).map_err(|e| e.to_string())?
    } else {
        "{\"Mods\":[],\"Unsub\":[]}".to_string()
    };

    // Rewrite by regex-free surgery: keep every OTHER entry's text verbatim and
    // only move ours. Rebuilding the whole document from a hand parser would
    // normalise the game's own formatting on every install.
    let rel = format!("\"Path\": \"local//{title}\"");
    let rel_compact = format!("\"Path\":\"local//{title}\"");
    let has = text.contains(&rel) || text.contains(&rel_compact);

    let mut doc = text.clone();
    if has {
        // Already present: force Enabled true, then move to front.
        doc = enable_entry(&doc, title);
        doc = move_to_front(&doc, title);
    } else {
        let entry = format!(
            "{{\"CheckSum\":\"0\",\"Enabled\":true,\"LastUpdate\":\"{}\",\
             \"Path\":\"local//{}\",\"Priority\":1,\"PublishID\":0,\
             \"Title\":\"{}\",\"WorkshopID\":0}}",
            now_ms(),
            crate::server::json_escape(title),
            crate::server::json_escape(title)
        );
        doc = insert_entry(&doc, &entry)?;
        doc = renumber(&doc);
    }
    checked_status_write(status_path, &text, &doc)
}

fn now_ms() -> String {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis().to_string())
        .unwrap_or_else(|_| "0".into())
}

fn insert_entry(doc: &str, entry: &str) -> Result<String, String> {
    let at = doc.find("\"Mods\"").ok_or("mod-status.json 里没有 Mods")?;
    let lb = doc[at..].find('[').ok_or("Mods 不是数组")? + at;
    let mut out = String::with_capacity(doc.len() + entry.len() + 2);
    out.push_str(&doc[..lb + 1]);
    out.push_str(entry);
    let rest = &doc[lb + 1..];
    if rest.trim_start().starts_with(']') {
        out.push_str(rest);
    } else {
        out.push(',');
        out.push_str(rest);
    }
    Ok(out)
}

fn enable_entry(doc: &str, title: &str) -> String {
    // Find the entry object containing our Path, then set Enabled to true
    // inside it.
    let rels = [
        format!("\"Path\":\"local//{title}\""),
        format!("\"Path\": \"local//{title}\""),
    ];
    for rel in rels.iter() {
        if let Some(p) = doc.find(rel) {
            // Walk back to the '{' that opens this object and forward to its
            // matching '}'.
            if let Some(obj_start) = doc[..p].rfind('{') {
                if let Some(obj_end) = matching(doc, obj_start) {
                    let obj = &doc[obj_start..obj_end];
                    let fixed = set_bool(obj, "Enabled", true);
                    if fixed != obj {
                        let mut out = String::new();
                        out.push_str(&doc[..obj_start]);
                        out.push_str(&fixed);
                        out.push_str(&doc[obj_end..]);
                        return out;
                    }
                    return doc.to_string();
                }
            }
        }
    }
    doc.to_string()
}

/// Cut `doc[start..=end]` out, dropping exactly the one comma that separated it
/// from its neighbours.
///
/// Written as a splice rather than a `,,` substitution because entries carry
/// free text: a mod titled `a,, b` would have been silently rewritten by the
/// substitution, and `{,` never actually occurred here.
fn splice_out(doc: &str, start: usize, end: usize) -> String {
    let head = &doc[..start];
    let tail = &doc[end + 1..];
    let head_kept = head.trim_end_matches(char::is_whitespace);
    let tail_off = tail.len() - tail.trim_start_matches(char::is_whitespace).len();
    if head_kept.ends_with(',') {
        // `[{prev},{this},{next}]` -> the comma BEFORE this entry goes away.
        format!("{}{}", &head[..head_kept.len() - 1], tail)
    } else if tail[tail_off..].starts_with(',') {
        // Only entry before this position -> the comma AFTER it goes away.
        format!("{}{}", head, &tail[tail_off + 1..])
    } else {
        // Sole entry in the array.
        format!("{head}{tail}")
    }
}

/// Move an existing entry to the front of `Mods[]` and renumber by position.
///
/// `matching` returns the index OF the closing brace, so the entry is
/// `doc[obj_start..=obj_end]`.  Slicing `..obj_end` dropped the brace and left
/// it behind at the removal point -- that is how this used to write
/// `..."WorkshopID":0,}` into the player's real mod list on every reinstall of
/// an already-present mod, which then made `json.loads` fail for the whole
/// product and for the game.
pub fn move_to_front(doc: &str, title: &str) -> String {
    let rels = [
        format!("\"Path\":\"local//{title}\""),
        format!("\"Path\": \"local//{title}\""),
    ];
    for rel in rels.iter() {
        if let Some(p) = doc.find(rel) {
            if let Some(obj_start) = doc[..p].rfind('{') {
                if let Some(obj_end) = matching(doc, obj_start) {
                    let entry = doc[obj_start..=obj_end].to_string();
                    let rest = splice_out(doc, obj_start, obj_end);
                    if let Some(at) = rest.find("\"Mods\"") {
                        if let Some(lb) = rest[at..].find('[') {
                            let lb = lb + at;
                            let mut out = String::new();
                            out.push_str(&rest[..lb + 1]);
                            out.push_str(&entry);
                            let tail = &rest[lb + 1..];
                            if !tail.trim_start().starts_with(']') {
                                out.push(',');
                            }
                            out.push_str(tail);
                            return renumber(&out);
                        }
                    }
                }
            }
        }
    }
    doc.to_string()
}

/// Parse-check a `mod-status.json` rewrite before it reaches the disk.
///
/// The player's whole mod configuration lives in this one file and the game
/// refuses to start when it does not parse, so a string-surgery bug here costs
/// the user their setup -- which is exactly what happened once.  `before` is
/// the text we read: if that parsed and our rewrite does not, the rewrite is
/// what is wrong and it must not land.  A file that was ALREADY broken
/// (`before` fails to parse) is not ours to reject -- repairing it is the job.
pub fn checked_status_write(path: &Path, before: &str, doc: &str) -> Result<(), String> {
    let was_ok = serde_json::from_str::<serde_json::Value>(before).is_ok();
    if was_ok {
        if let Err(e) = serde_json::from_str::<serde_json::Value>(doc) {
            return Err(format!(
                "这次改写会把 mod-status.json 写成不合法的 JSON（{e}），已放弃写入。\
                 文件里是 {} 个模组的顺序，宁可不装也不能写坏它。",
                before.matches("\"Path\"").count()
            ));
        }
    }
    // Write beside, then rename: a half-written status file loses the player's
    // whole mod list, and that is not recoverable from anywhere.
    let tmp = path.with_extension("json.tmp");
    fs::write(&tmp, doc).map_err(|e| e.to_string())?;
    fs::rename(&tmp, path).map_err(|e| e.to_string())
}

fn set_bool(obj: &str, key: &str, value: bool) -> String {
    let pat = format!("\"{key}\":");
    if let Some(p) = obj.find(&pat) {
        let after = p + pat.len();
        let tail = &obj[after..];
        let trimmed = tail.trim_start();
        let lead = tail.len() - trimmed.len();
        let (had, rest) = if trimmed.starts_with("true") {
            (4, &trimmed[4..])
        } else if trimmed.starts_with("false") {
            (5, &trimmed[5..])
        } else {
            return obj.to_string();
        };
        let mut out = String::new();
        out.push_str(&obj[..after]);
        out.push_str(&obj[after..after + lead]);
        out.push_str(if value { "true" } else { "false" });
        out.push_str(rest);
        let _ = had;
        return out;
    }
    obj.to_string()
}

/// Renumber `Priority` 1..n in array order, which is what the engine reads.
fn renumber(doc: &str) -> String {
    let at = match doc.find("\"Mods\"") {
        Some(a) => a,
        None => return doc.to_string(),
    };
    let lb = match doc[at..].find('[') {
        Some(v) => v + at,
        None => return doc.to_string(),
    };
    let rb = match matching(doc, lb) {
        Some(v) => v,
        None => return doc.to_string(),
    };
    let body = &doc[lb + 1..rb];

    let mut out = String::new();
    let mut i = 0usize;
    let mut idx = 0usize;
    while let Some(open) = body[i..].find('{') {
        let s = i + open;
        let e = match matching(body, s) {
            Some(v) => v,
            None => break,
        };
        idx += 1;
        out.push_str(&body[i..s]);
        let obj = &body[s..e];
        out.push_str(&set_int(obj, "Priority", idx as i64));
        i = e;
    }
    out.push_str(&body[i..]);
    format!("{}{}{}", &doc[..lb + 1], out, &doc[rb..])
}

fn set_int(obj: &str, key: &str, value: i64) -> String {
    let pat = format!("\"{key}\":");
    if let Some(p) = obj.find(&pat) {
        let after = p + pat.len();
        let tail = &obj[after..];
        let trimmed = tail.trim_start();
        let lead = tail.len() - trimmed.len();
        let end = trimmed
            .find(|c: char| !c.is_ascii_digit() && c != '-')
            .unwrap_or(trimmed.len());
        let mut out = String::new();
        out.push_str(&obj[..after]);
        out.push_str(&obj[after..after + lead]);
        out.push_str(&value.to_string());
        out.push_str(&trimmed[end..]);
        return out;
    }
    obj.to_string()
}

fn matching(s: &str, open: usize) -> Option<usize> {
    let b = s.as_bytes();
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

fn copy_dir(from: &Path, to: &Path) -> io::Result<()> {
    fs::create_dir_all(to)?;
    for entry in fs::read_dir(from)? {
        let entry = entry?;
        let src = entry.path();
        let dst = to.join(entry.file_name());
        if src.is_dir() {
            copy_dir(&src, &dst)?;
        } else {
            fs::copy(&src, &dst)?;
        }
    }
    Ok(())
}
