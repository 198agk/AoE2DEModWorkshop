//! A native HTTP server for the workshop, replacing the Python one route by route.
//!
//! Why a second server instead of "compile the Python"
//! ------------------------------------------------
//! The target is a folder a player double-clicks: no `python.exe`, no `.py`
//! files, nothing to install.  Nuitka does get there, but it leaves a 7 MB
//! `python312.dll` and a runtime image, and the owner of this project said, in
//! as many words, that a pile of Python glued together is not what was asked
//! for.  So the server is rewritten and the engine underneath it already is
//! (see `aoe2mod-dat`: full parse and byte-identical round trip).
//!
//! What this file is NOT yet
//! -------------------------
//! It serves four routes.  The page calls nineteen.  That is deliberate: a
//! server that answers `/api/meta` with the real civ list, `/api/progress` with
//! the real stage machine, and `/api/stat-edit` with a real edit proves the
//! whole path (WebView2 -> HTTP -> Rust -> 93 MB parse -> bytes back) before
//! nine hundred lines of route-by-route porting are written on top of it.
//!
//! Threading: one accept loop, one thread per connection.  The expensive work
//! (a 93 MB parse) is done once, lazily, behind a lock, and cached -- the
//! page's first paint must not wait on it.

use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

/// What the server is doing right now, for the loading page to poll.
#[derive(Default)]
pub struct Progress {
    pub stage: String,
    pub label: String,
    pub percent: u32,
    pub elapsed: f64,
    pub ready: bool,
    pub error: Option<String>,
}

impl Progress {
    pub fn to_json(&self) -> String {
        let err = match &self.error {
            Some(e) => format!("\"{}\"", json_escape(e)),
            None => "null".to_string(),
        };
        format!(
            "{{\"stage\":\"{}\",\"label\":\"{}\",\"percent\":{},\"elapsed\":{:.2},\"ready\":{},\"error\":{}}}",
            json_escape(&self.stage),
            json_escape(&self.label),
            self.percent,
            self.elapsed,
            self.ready,
            err
        )
    }
}

pub struct Server {
    pub root: PathBuf,
    pub progress: Mutex<Progress>,
    pub parsed: Mutex<Option<Arc<ParseResult>>>,
    pub port: u16,
}

/// The facts the page asks for once the game data is read.
pub struct ParseResult {
    pub civs: Vec<String>,
    pub unit_count: usize,
    pub tech_count: usize,
    pub graph_count: usize,
    pub raw_len: usize,
    pub millis: u128,
}

pub fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

const LOADING_PAGE: &str = r#"<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>模组工坊</title>
<style>
 html,body{height:100%;margin:0;background:#14161a;color:#e6e6e6;
   font:14px/1.7 "Microsoft YaHei",system-ui,sans-serif}
 .w{max-width:420px;margin:18vh auto;text-align:center}
 h1{font-size:16px;font-weight:500;margin:0 0 6px}
 .s{color:#8a949f;min-height:22px;margin:0 0 14px}
 .t{height:4px;background:#232a33;border-radius:999px;overflow:hidden}
 .b{height:100%;width:0;background:#c9a227;transition:width .25s}
 .f{color:#cf222e;margin-top:14px;text-align:left;white-space:pre-wrap;display:none}
 .f.on{display:block}
</style></head><body><div class="w">
<h1>帝国时代 2 决定版 · 模组工坊</h1>
<p class="s" id="s">正在启动</p>
<div class="t"><div class="b" id="b"></div></div>
<p class="f" id="f"></p>
</div><script>
function tick(){
 fetch("/api/progress",{cache:"no-store"}).then(r=>r.json()).then(j=>{
  var p=(j&&j.progress)||{};
  if(p.label) document.getElementById("s").textContent=p.label;
  if(typeof p.percent==="number") document.getElementById("b").style.width=p.percent+"%";
  if(p.error){var f=document.getElementById("f");f.className="f on";f.textContent=p.error;return}
  if(p.ready){location.replace("/");return}
  setTimeout(tick,250);
 }).catch(()=>{document.getElementById("s").textContent="正在重试连接";setTimeout(tick,700)});
}
tick();
</script></body></html>"#;

pub fn serve(server: Arc<Server>) -> std::io::Result<()> {
    let listener = TcpListener::bind(("127.0.0.1", server.port))?;
    // Announce the bound port, which is how the shell learns it when the caller
    // asked for port 0.
    println!("listening 127.0.0.1:{}", server.port);
    for conn in listener.incoming() {
        match conn {
            Ok(stream) => {
                let s = Arc::clone(&server);
                std::thread::spawn(move || {
                    let _ = handle(s, stream);
                });
            }
            Err(e) => eprintln!("accept: {e}"),
        }
    }
    Ok(())
}

fn handle(server: Arc<Server>, mut stream: TcpStream) -> std::io::Result<()> {
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut request_line = String::new();
    if reader.read_line(&mut request_line)? == 0 {
        return Ok(());
    }
    let mut len = 0usize;
    loop {
        let mut line = String::new();
        if reader.read_line(&mut line)? == 0 {
            break;
        }
        if line == "\r\n" || line == "\n" {
            break;
        }
        let lower = line.to_ascii_lowercase();
        if let Some(v) = lower.strip_prefix("content-length:") {
            len = v.trim().parse().unwrap_or(0);
        }
    }
    let mut body = vec![0u8; len];
    if len > 0 {
        reader.read_exact(&mut body)?;
    }

    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("GET").to_string();
    let target = parts.next().unwrap_or("/").to_string();
    let (path, query) = match target.split_once('?') {
        Some((p, q)) => (p.to_string(), q.to_string()),
        None => (target.clone(), String::new()),
    };
    let _ = method;

    let (status, ctype, payload) = route(&server, &path, &query, &body);
    let mut head = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n",
        status,
        reason(status),
        ctype,
        payload.len()
    )
    .into_bytes();
    head.extend_from_slice(&payload);
    stream.write_all(&head)?;
    stream.flush()
}


/// The folder that holds `aoe2mod/schema`, derived from the static dir.
///
/// `root` is `<app>/aoe2mod/ui/static`, so the app dir is THREE levels up.
/// Two levels gives `<app>/aoe2mod`, where `aoe2mod/schema` does not exist and
/// every table comes back EMPTY -- which reads on screen as "no forms, no
/// wording" rather than as an error.
fn app_dir_of(static_root: &std::path::Path) -> std::path::PathBuf {
    let mut p = static_root.to_path_buf();
    for _ in 0..3 {
        if let Some(parent) = p.parent() {
            p = parent.to_path_buf();
        }
    }
    p
}

fn reason(code: u16) -> &'static str {
    match code {
        200 => "OK",
        400 => "Bad Request",
        404 => "Not Found",
        500 => "Internal Server Error",
        _ => "OK",
    }
}

fn route(
    server: &Arc<Server>,
    path: &str,
    _query: &str,
    body: &[u8],
) -> (u16, &'static str, Vec<u8>) {
    match path {
        "/" => match std::fs::read(server.root.join("index.html")) {
            Ok(b) => (200, "text/html; charset=utf-8", b),
            Err(_) => (404, "text/plain; charset=utf-8", b"no index.html".to_vec()),
        },
        "/loading" => (200, "text/html; charset=utf-8", LOADING_PAGE.as_bytes().to_vec()),
        "/api/progress" => {
            let p = server.progress.lock().unwrap();
            let json = format!("{{\"ok\":true,\"progress\":{}}}", p.to_json());
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/meta" => match server.parsed.lock().unwrap().clone() {
            Some(r) => {
                let civs: Vec<String> = r
                    .civs
                    .iter()
                    .map(|c| format!("\"{}\"", json_escape(c)))
                    .collect();
                let json = format!(
                    "{{\"ok\":true,\"version\":\"native\",\"civs\":[{}],\"unit_count\":{},\"tech_count\":{},\"graphic_count\":{},\"raw_bytes\":{},\"parse_ms\":{}}}",
                    civs.join(","),
                    r.unit_count,
                    r.tech_count,
                    r.graph_count,
                    r.raw_len,
                    r.millis
                );
                (200, "application/json; charset=utf-8", json.into_bytes())
            }
            None => (
                200,
                "application/json; charset=utf-8",
                b"{\"ok\":false,\"error\":\"\xe8\xbf\x98\xe5\x9c\xa8\xe8\xaf\xbb\xe5\x8f\x96\xe6\xb8\xb8\xe6\x88\x8f\xe6\x95\xb0\xe6\x8d\xae\"}".to_vec(),
            ),
        },
        "/api/mods" => match crate::mods::profile_root() {
            Some(root) => match crate::mods::read_mods(&root) {
                Ok(rows) => {
                    let json = format!("{{\"ok\":true,\"mods\":{}}}", crate::mods::to_json(&rows));
                    (200, "application/json; charset=utf-8", json.into_bytes())
                }
                Err(e) => (
                    200,
                    "application/json; charset=utf-8",
                    format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e.to_string())).into_bytes(),
                ),
            },
            None => (
                200,
                "application/json; charset=utf-8",
                format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape("找不到玩家档案目录")).into_bytes(),
            ),
        },
        "/api/forms" => {
            // `?intent=` narrows to one intent.  Read fresh per request: a
            // plugin can change the table while the tool runs.
            let want = _query
                .split('&')
                .find_map(|kv| kv.strip_prefix("intent="))
                .filter(|s| !s.is_empty());
            let app_dir = app_dir_of(&server.root);
            let v = crate::tables::forms(&app_dir, want);
            (200, "application/json; charset=utf-8", v.to_string().into_bytes())
        }
        "/api/locale" => {
            let name = _query
                .split('&')
                .find_map(|kv| kv.strip_prefix("locale="))
                .filter(|s| !s.is_empty())
                .unwrap_or("zh");
            let app_dir = app_dir_of(&server.root);
            let v = crate::tables::locale(&app_dir, name);
            (200, "application/json; charset=utf-8", v.to_string().into_bytes())
        }
        "/api/parse" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let text = req.get("text").and_then(|v| v.as_str()).unwrap_or("");
            let clauses = crate::sentences::read(text);
            let mut intents: Vec<String> = Vec::new();
            let mut refusals: Vec<String> = Vec::new();
            let mut rows: Vec<String> = Vec::new();
            for cl in &clauses {
                match &cl.intent {
                    Some(it) => intents.push(it.to_json()),
                    None => refusals.push(format!(
                        "{{\"text\":\"{}\",\"why\":\"{}\"}}",
                        json_escape(&cl.text),
                        json_escape(cl.why.as_deref().unwrap_or(""))
                    )),
                }
                rows.push(format!(
                    "{{\"text\":\"{}\",\"entity\":{},\"entity_id\":{},\"why\":{}}}",
                    json_escape(&cl.text),
                    match &cl.entity_name {
                        Some(n) => format!("\"{}\"", json_escape(n)),
                        None => "null".into(),
                    },
                    match cl.entity_id {
                        Some(v) => v.to_string(),
                        None => "null".into(),
                    },
                    match &cl.why {
                        Some(w) => format!("\"{}\"", json_escape(w)),
                        None => "null".into(),
                    }
                ));
            }
            let json = format!(
                "{{\"ok\":true,\"intents\":[{}],\"refusals\":[{}],\"clauses\":[{}]}}",
                intents.join(","), refusals.join(","), rows.join(",")
            );
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/recipes" => {
            let json = match crate::recipes::rows() {
                Ok(rows) => {
                    let items: Vec<String> = rows.iter().map(|r| {
                        let sents: Vec<String> = r.sentences.iter()
                            .map(|x| format!("\"{}\"", json_escape(x))).collect();
                        format!("{{\"name\":\"{}\",\"sentences\":[{}],\"count\":{},\"saved_at\":\"{}\",\"note\":\"{}\"}}",
                            json_escape(&r.name), sents.join(","), r.sentences.len(),
                            json_escape(&r.saved_at), json_escape(&r.note))
                    }).collect();
                    format!("{{\"ok\":true,\"recipes\":[{}]}}", items.join(","))
                }
                Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e.to_string())),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/recipe" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(e) => {
                    let m = format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e.to_string()));
                    return (400, "application/json; charset=utf-8", m.into_bytes());
                }
            };
            let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let sents: Vec<String> = req.get("sentences")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().filter_map(|x| x.as_str().map(|s| s.to_string())).collect())
                .unwrap_or_default();
            let note = req.get("note").and_then(|v| v.as_str()).unwrap_or("");
            let json = match crate::recipes::remember(name, sents, note) {
                Ok(_) => "{\"ok\":true}".to_string(),
                Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/recipe-forget" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let json = match crate::recipes::forget(name) {
                Ok(_) => "{\"ok\":true}".to_string(),
                Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        // The one write path, so the whole chain can be exercised end to end.
        "/api/icon" => {
            // `?kind=unit&id=83&section=Units&max=64`
            let q: std::collections::HashMap<String, String> = _query
                .split('&')
                .filter_map(|kv| kv.split_once('='))
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect();
            let section = q.get("section").cloned().unwrap_or_else(|| "Units".into());
            let id: u32 = q.get("id").and_then(|v| v.parse().ok()).unwrap_or(0);
            let max_side: u32 = q.get("max").and_then(|v| v.parse().ok()).unwrap_or(64);
            match crate::game_root() {
                None => (
                    200,
                    "application/json; charset=utf-8",
                    b"{\"ok\":false,\"error\":\"no game root\"}".to_vec(),
                ),
                Some(root) => match crate::icons::Icons::load(&root) {
                    None => (
                        200,
                        "application/json; charset=utf-8",
                        b"{\"ok\":false,\"error\":\"icons.json unreadable\"}".to_vec(),
                    ),
                    Some(ic) => match ic.file_for(&section, id) {
                        Err(why) => {
                            let m = format!(
                                "{{\"ok\":false,\"error\":\"{}\"}}",
                                json_escape(&why)
                            );
                            (200, "application/json; charset=utf-8", m.into_bytes())
                        }
                        Ok((rel, material)) => {
                            let path = ic.path_of(&rel);
                            match crate::ddstex::to_png(&path, max_side) {
                                Ok(png) => (200, "image/png", png),
                                Err(e) => {
                                    let m = format!(
                                        "{{\"ok\":false,\"error\":\"{}\",\"file\":\"{}\",\"material\":\"{}\"}}",
                                        json_escape(&e.to_string()),
                                        json_escape(&rel),
                                        json_escape(&material)
                                    );
                                    (200, "application/json; charset=utf-8", m.into_bytes())
                                }
                            }
                        }
                    },
                },
            }
        }
        "/api/update-check" => {
            let json = match (crate::mods::profile_root(), crate::game_root()) {
                (Some(prof), Some(root)) => {
                    let dat = root.join("resources/_common/dat/empires2_x2_p1.dat");
                    match crate::updates::check(&prof, &dat, true) {
                        Ok((rows, attention)) => {
                            let state = crate::updates::state_file()
                                .map(|p| {
                                    p.parent()
                                        .map(|d| d.display().to_string())
                                        .unwrap_or_default()
                                })
                                .unwrap_or_default();
                            crate::updates::to_json(&rows, attention, &state)
                        }
                        Err(e) => format!(
                            "{{\"ok\":false,\"error\":\"{}\"}}",
                            json_escape(&e)
                        ),
                    }
                }
                _ => format!(
                    "{{\"ok\":false,\"error\":\"{}\"}}",
                    json_escape("找不到游戏目录或玩家档案目录")
                ),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/mod" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let enabled = req.get("enabled").and_then(|v| v.as_bool()).unwrap_or(false);
            let json = match crate::mods::profile_root() {
                None => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape("找不到玩家档案目录")),
                Some(prof) => match crate::mods::set_enabled(&prof, name, enabled) {
                    Ok(row) => {
                        let rows = crate::mods::read_mods(&prof).unwrap_or_default();
                        format!("{{\"ok\":true,\"mod\":{{\"name\":\"{}\",\"enabled\":{}}},\"mods\":{}}}",
                            json_escape(&row.name), row.enabled, crate::mods::to_json(&rows))
                    }
                    Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
                },
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/mod-move" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let delta = req.get("delta").and_then(|v| v.as_i64()).unwrap_or(0);
            let json = match crate::mods::profile_root() {
                None => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape("找不到玩家档案目录")),
                Some(prof) => match crate::mods::move_mod(&prof, name, delta) {
                    Ok(()) => {
                        let rows = crate::mods::read_mods(&prof).unwrap_or_default();
                        format!("{{\"ok\":true,\"mods\":{}}}", crate::mods::to_json(&rows))
                    }
                    Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
                },
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/uninstall" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let json = match crate::mods::profile_root() {
                None => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape("找不到玩家档案目录")),
                Some(prof) => match crate::mods::uninstall(&prof, name) {
                    Ok(removed) => {
                        let rows = crate::mods::read_mods(&prof).unwrap_or_default();
                        let names: Vec<String> = removed
                            .iter()
                            .map(|r| format!("\"{}\"", json_escape(r)))
                            .collect();
                        format!("{{\"ok\":true,\"removed\":[{}],\"mods\":{}}}",
                            names.join(","), crate::mods::to_json(&rows))
                    }
                    Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
                },
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/build" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let json = match crate::stat_edit::build_and_install(server, &req) {
                Ok(j) => j,
                Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/stat" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(e) => {
                    let msg = format!("{{\"ok\":false,\"error\":\"bad json: {}\"}}", json_escape(&e.to_string()));
                    return (400, "application/json; charset=utf-8", msg.into_bytes());
                }
            };
            let stat = req.get("stat").and_then(|v| v.as_str()).unwrap_or("");
            let unit = req.get("unit").and_then(|v| v.as_i64()).unwrap_or(-1) as i16;
            let value = req.get("value").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let json = match crate::stat_edit::apply(server, stat, unit, value) {
                Ok(report) => report,
                Err(e) => format!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e)),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        _ => (404, "text/plain; charset=utf-8", b"not found".to_vec()),
    }
}
