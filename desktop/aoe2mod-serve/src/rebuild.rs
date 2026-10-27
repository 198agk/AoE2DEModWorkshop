//! `/api/rebuild`: replay the intents a build record kept, then reinstall.
//!
//! A data mod ships a whole copy of the `.dat`, so after a game update it
//! overrides the new data. The fix is to rebuild it against today's file -- and
//! to do that the record has to remember what the user asked for, not the bytes
//! that were produced.
//!
//! The refusal matters as much as the rebuild: if the record's intent is
//! something this compiler cannot replay, say WHICH one. Approximating would ship
//! a different mod under a name the player already trusts.

use serde_json::Value;
use std::path::Path;

pub struct BuildRecord {
    pub title: String,
    pub author: String,
    pub description: String,
    pub intents: Vec<Value>,
}

/// The record for `title`, from `builds.json`.
pub fn record(title: &str) -> Result<BuildRecord, String> {
    let path = crate::updates::state_file().ok_or("找不到状态目录")?;
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("读不到 {}：{e}", path.display()))?;
    let doc: Value = serde_json::from_str(text.trim_start_matches('\u{feff}'))
        .map_err(|e| format!("{} 不是合法 JSON：{e}", path.display()))?;
    let builds = doc
        .get("builds")
        .and_then(|v| v.as_object())
        .ok_or("记录文件里没有 builds")?;
    let entry = builds
        .get(title)
        .or_else(|| {
            // The record may be keyed by the folder name rather than the title.
            builds
                .iter()
                .find(|(_, v)| v.get("title").and_then(|t| t.as_str()) == Some(title))
                .map(|(_, v)| v)
        })
        .ok_or_else(|| format!("没有「{title}」的构建记录，没法按原样重建"))?;
    let intents = entry
        .get("intents")
        .and_then(|v| v.as_array())
        .cloned()
        .filter(|a| !a.is_empty())
        .ok_or_else(|| {
            format!("「{title}」的记录里没有留下当初的改动，需要重新说一遍")
        })?;
    Ok(BuildRecord {
        title: title.to_string(),
        author: entry
            .get("author")
            .and_then(|v| v.as_str())
            .unwrap_or("dsh")
            .to_string(),
        description: entry
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        intents,
    })
}

/// Replay one intent through the native compiler.
///
/// Returns the JSON body the stat editor produced, or a refusal naming the
/// intent. Only stat edits are replayable today; everything else says so.
///
/// A replayed intent must be the SAME edit, scope included: `civs` is copied
/// through, because dropping it turns 「只改不列颠」 into all 63 civilizations
/// and reports success.
pub fn replay(
    server: &crate::server::Server,
    intent: &Value,
    title: &str,
    install: bool,
) -> Result<Value, String> {
    let kind = intent
        .get("intent")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let unit = intent.get("unit").and_then(|v| v.as_i64());
    let stat = intent.get("stat").and_then(|v| v.as_str());
    let value = intent.get("value").and_then(|v| v.as_f64());
    let delta = intent.get("delta").and_then(|v| v.as_f64());

    match (kind.as_str(), unit, stat) {
        ("unit.stat", Some(u), Some(st)) => {
            let mut req = serde_json::json!({
                "stat": st,
                "unit": u,
            });
            if let Some(v) = value {
                req["value"] = serde_json::json!(v);
            }
            if let Some(d) = delta {
                req["delta"] = serde_json::json!(d);
            }
            // Replay the scope too.  Without it the rebuild reproduces a WIDER
            // edit than the one that was recorded, which is the quietest way to
            // undo the player's "只改不列颠" without ever contradicting them.
            if let Some(c) = intent.get("civs") {
                if !c.is_null() {
                    req["civs"] = c.clone();
                }
            }
            // The rebuild has to land under the SAME title and go through
            // install, or it produces a second folder and leaves the stale one
            // in place while reporting a fresh build.
            req["title"] = serde_json::json!(title);
            if install {
                req["install"] = serde_json::json!(true);
            }
            let body = crate::stat_edit::build_and_install(server, &req)?;
            let v: Value = serde_json::from_str(&body)
                .map_err(|e| format!("重建结果不是 JSON：{e}"))?;
            Ok(v)
        }
        (other, _, _) => Err(format!(
            "「{other}」这个改动还只能用原来的引擎重建；这条记录先留着，不会拿别的结果顶替它"
        )),
    }
}

/// Rebuild a stale mod and put it back where it was.
pub fn rebuild(server: &crate::server::Server, title: &str) -> Result<Value, String> {
    let rec = record(title)?;
    if rec.intents.len() != 1 {
        return Err(format!(
            "「{title}」当初是 {} 条改动一起建的，一次重放多条还没有接进来；\
             现在只能按一条重建，请先单独建一次",
            rec.intents.len()
        ));
    }
    // `install: true` because the whole point is replacing the stale folder; the
    // title so the replacement goes to the same place instead of beside it.
    let built = replay(server, &rec.intents[0], &rec.title, true)?;
    let prof = crate::mods::profile_root().ok_or("找不到玩家档案目录")?;
    let _ = crate::mods::set_enabled(&prof, title, true);
    Ok(serde_json::json!({
        "ok": true,
        "title": rec.title,
        "author": rec.author,
        "rebuilt": built,
    }))
}

/// Kept so the module compiles standalone during bring-up.
pub fn _path() -> Option<std::path::PathBuf> {
    crate::updates::state_file().and_then(|p| p.parent().map(Path::to_path_buf))
}
