//! The native engine as a library, so the shell can host it in-process.
//!
//! Two ways to run this exist on purpose:
//!   * `aoe2mod-serve.exe` (the binary) -- a standalone process, used while
//!     developing and by anything that wants a port without a window.
//!   * this library, embedded by `desktop/src-tauri` -- no child process, no
//!     `python.exe`, no port handoff: the window and the engine are one image.
//!
//! The second is what "a folder you double-click" needs. A shell that spawns a
//! server must decide what to do when the spawn fails, and every answer to that
//! ("wait 150 s", "show an error page") has already cost this project a round.
pub mod groupdat;
pub mod togglegroup;
pub mod spriteart;
pub mod spritemap;
pub mod attack_class;
pub mod cardmove;
pub mod cards;
pub mod civtree;
pub mod browse;
pub mod effectedit;
pub use aoe2mod_dat::{write23, write47, write810, writer};
pub mod techedit;
pub use aoe2mod_dat::stats;
pub mod describe;
pub mod families;
pub mod rebuild;
pub mod ai;

pub mod build;
pub mod ddstex;
pub mod icons;
pub mod mods;
pub mod preview;
pub mod recipes;
pub mod sentences;
pub mod slots;
pub mod server;
pub mod stat_edit;
pub mod tables;
pub mod updates;
pub mod unitfield;

use server::{ParseResult, Progress, Server};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

/// Build a server bound to `port` with its own progress state.
pub fn build(root: PathBuf, port: u16) -> Arc<Server> {
    Arc::new(Server {
        root,
        progress: Mutex::new(Progress {
            stage: "boot".into(),
            label: "正在启动".into(),
            ..Default::default()
        }),
        parsed: Mutex::new(None),
        port,
    })
}

/// Read the game data and fill in `server.parsed`, reporting progress as it goes.
///
/// Called from a background thread by both hosts: the loading page polls
/// `/api/progress` and must answer in milliseconds, so nothing here may run on
/// the accept thread.
pub fn load_game(server: &Arc<Server>) {
    use aoe2mod_dat::{
        load_dat, read_stage1, read_stages23, read_stages47, read_stages810, Reader,
    };
    use std::time::Instant;

    let t0 = Instant::now();
    let set = |stage: &str, label: &str, pct: u32, ready: bool, err: Option<String>| {
        let mut p = server.progress.lock().unwrap();
        p.stage = stage.into();
        p.label = label.into();
        p.percent = pct;
        p.elapsed = t0.elapsed().as_secs_f64();
        p.ready = ready;
        p.error = err;
    };

    set("find", "正在寻找游戏目录", 5, false, None);
    let root = match game_root() {
        Some(r) => r,
        None => {
            set(
                "find",
                "找不到游戏目录",
                0,
                false,
                Some(
                    "找不到《帝国时代 2 决定版》。请确认游戏已安装，\
                     或用环境变量 AOE2MOD_GAME_ROOT 指定游戏目录。"
                        .into(),
                ),
            );
            return;
        }
    };
    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");

    set("read", "正在读取游戏数据", 25, false, None);
    let (raw, _how) = match load_dat(&dat) {
        Ok(v) => v,
        Err(e) => {
            set("read", "读取游戏数据失败", 25, false,
                Some(format!("{}：{e}", dat.display())));
            return;
        }
    };

    // The offset tables were measured from one specific `.dat`.  On 2026-10-28
    // Steam replaced it (`sounds` 769 -> 930, +4135 bytes) and every table went
    // stale while the tool happily kept writing at the old offsets -- `/api/stat`
    // answered `ok:true` for edits landing 4397 bytes off.  Refuse before parse:
    // a wrong write that reports success is worse than a refusal that explains.
    if let Some(err) = stamp_mismatch(&dat, &raw) {
        set("stale", "游戏数据更新了，偏移表对不上", 30, false, Some(err));
        return;
    }

    set("parse", "正在解析游戏数据", 60, false, None);
    let mut r = Reader::new(&raw);
    let s1 = match read_stage1(&mut r) {
        Ok(v) => v,
        Err(e) => return set("parse", "解析失败", 60, false, Some(format!("版本头：{e}"))),
    };
    let gv = s1.game_version;
    let s23 = match read_stages23(&mut r) {
        Ok(v) => v,
        Err(e) => {
            return set("parse", "解析失败", 60, false, Some(format!("图形与音效：{e}")))
        }
    };
    if let Err(e) = read_stages47(&mut r, gv) {
        return set("parse", "解析失败", 70, false, Some(format!("地形与效果：{e}")));
    }
    let s810 = match read_stages810(&mut r, gv) {
        Ok(v) => v,
        Err(e) => {
            return set("parse", "解析失败", 85, false, Some(format!("文明与科技：{e}")))
        }
    };

    let civs: Vec<String> = s810.civs.iter().map(|c| c.name.clone()).collect();
    let unit_count: usize = s810.civs.iter().map(|c| c.units.len()).sum();
    *server.parsed.lock().unwrap() = Some(Arc::new(ParseResult {
        civs,
        unit_count,
        tech_count: s810.techs.len(),
        graph_count: s23.graphics.len(),
        raw_len: raw.len(),
        millis: t0.elapsed().as_millis(),
    }));
    set("ready", "可以开始了", 100, true, None);
}

/// Where the game lives: environment override, then the paths that exist on a
/// normal Steam install.
///
/// A set-but-unusable `AOE2MOD_GAME_ROOT` returns `None` rather than falling
/// through: the caller declared which installation to read, and silently
/// answering from a different one is how a test measures the wrong `.dat`.
pub fn game_root() -> Option<PathBuf> {
    if let Ok(v) = std::env::var("AOE2MOD_GAME_ROOT") {
        if v.is_empty() {
            return None;
        }
        let p = PathBuf::from(&v);
        if p.is_dir() {
            return Some(p);
        }
        eprintln!("AOE2MOD_GAME_ROOT={v} 不是一个存在的目录，就不再退回别的游戏装了。");
        return None;
    }
    [
        r"d:\games\steam\steamapps\common\AoE2DE",
        r"c:\games\steam\steamapps\common\AoE2DE",
        r"c:\program files (x86)\steam\steamapps\common\AoE2DE",
    ]
    .iter()
    .map(PathBuf::from)
    .find(|p| p.join("resources/_common/dat/empires2_x2_p1.dat").is_file())
}


/// Where `stat_offsets.json` lives: the first candidate that exists.
///
/// Three call sites used to build this path by hand with an `unwrap_or` onto a
/// repo-relative default, which works only when the cwd happens to be the repo.
/// In a shipped folder it produced `os error 3` for a path nobody had, and the
/// route reported "读不到属性偏移表" -- correct, useless, and invisible until the
/// bundle was tested rather than the development binary.
pub fn stats_path() -> std::path::PathBuf {
    for p in sentences::table_paths("AOE2MOD_STAT_OFFSETS", "stat_offsets.json") {
        if p.is_file() {
            return p;
        }
    }
    std::path::PathBuf::from("_golden/stat_offsets.json")
}

/// Where `dat_stamp.json` lives: the manifest naming the `.dat` every
/// offset-bearing table under `_golden/` was measured from.
pub fn stamp_path() -> Option<std::path::PathBuf> {
    sentences::table_paths("AOE2MOD_DAT_STAMP", "dat_stamp.json")
        .into_iter()
        .find(|p| p.is_file())
}

/// `Some(reason)` when the tables do not belong to this `.dat`.
///
/// Three outcomes, and the middle one is the point of the whole function:
///
/// * no stamp at all -> refuse.  A missing manifest is not "assume it is fine":
///   that is exactly the state the 2026-10-28 update produced on every machine
///   that had already generated tables, and it looks identical to a fresh,
///   correct install.
/// * stamp names a different `.dat` -> refuse, and quote both byte counts so the
///   message says what happened instead of "something is wrong".
/// * stamp matches -> `None`.
///
/// The comparison is on the DECOMPRESSED stream because the game re-packs the
/// container between builds without changing its content; a file-level hash
/// would cry wolf on every re-install with identical data.
pub fn stamp_mismatch(dat: &std::path::Path, raw: &[u8]) -> Option<String> {
    use sha2::{Digest, Sha256};
    let path = match stamp_path() {
        Some(p) => p,
        None => {
            return Some(
                "找不到 dat_stamp.json（记录偏移表来自哪一份 .dat 的清单）。\
                 没有它就无法确定 _golden/ 里的偏移表还属不属于这份游戏数据，\
                 而按过期表写字节会改到别的位置——还会返回 ok:true。\
                 修复：py _probe/make_dat_stamp.py"
                    .into(),
            )
        }
    };
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) => return Some(format!("读不到 {}：{e}", path.display())),
    };
    let doc: serde_json::Value = match serde_json::from_str(text.trim_start_matches('\u{feff}')) {
        Ok(v) => v,
        Err(e) => return Some(format!("{} 不是合法 JSON：{e}", path.display())),
    };
    let want = doc
        .get("dat")
        .and_then(|d| d.get("raw_sha256"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    if want.is_empty() {
        return Some(format!("{} 里没有 dat.raw_sha256", path.display()));
    }
    let mut h = Sha256::new();
    h.update(raw);
    let got = format!("{:x}", h.finalize());
    if got == want {
        return None;
    }
    let was = doc
        .get("dat")
        .and_then(|d| d.get("raw_bytes"))
        .and_then(|v| v.as_i64())
        .unwrap_or(-1);
    Some(format!(
        "游戏数据更新了：偏移表是按另一份 .dat 量的（{} 字节，sha {}…），\
         现在这份 {} 是 {} 字节（sha {}…）。按旧表写字节会改到别的位置，\
         而且会返回 ok:true——所以这里先停下。\
         修复：重新生成偏移表（py _probe/make_stat_offsets.py 等），\
         再跑 py _probe/make_dat_stamp.py。",
        was,
        &want[..want.len().min(12)],
        dat.display(),
        raw.len(),
        &got[..got.len().min(12)]
    ))
}

