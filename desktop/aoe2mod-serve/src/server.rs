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


/// Percent-decode a query value, which is how a Chinese filter arrives.
fn percent_decode(s: &str) -> String {
    let b = s.as_bytes();
    let mut out = Vec::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'%' && i + 2 < b.len() {
            if let Ok(v) = u8::from_str_radix(&s[i + 1..i + 3], 16) {
                out.push(v);
                i += 3;
                continue;
            }
        }
        if b[i] == b'+' {
            out.push(b' ');
        } else {
            out.push(b[i]);
        }
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn empty_stat_table() -> crate::stats::StatTable {
    crate::stats::StatTable {
        kinds: std::collections::HashMap::new(),
        civs: Vec::new(),
    }
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
                // The page reads six fields off META: version, mods, civs,
                // available, model, intents. Supplying two of them made `boot()`
                // throw at `renderIntentList` and the editor never initialised
                // -- while every per-endpoint probe was green. The screen is the
                // user, so the screen is the test.
                let app_dir = app_dir_of(&server.root);
                let table = crate::tables::load_sentences(&app_dir);
                let empty = serde_json::Map::new();
                let intents_src = table
                    .get("intents")
                    .and_then(|v| v.as_object())
                    .unwrap_or(&empty);
                let mut intents: Vec<String> = Vec::new();
                for (id, spec) in intents_src {
                    let title = spec
                        .get("label")
                        .or_else(|| spec.get("title"))
                        .and_then(|v| v.as_str())
                        .unwrap_or(id);
                    let fields: Vec<String> = spec
                        .get("fields")
                        .and_then(|v| v.as_object())
                        .map(|m| m.keys().cloned().collect())
                        .unwrap_or_default();
                    // `by_sentence` says whether a SENTENCE can reach this intent.
                    // A plugin adds intents to the schema and this list IS the
                    // schema, so an unreachable one is marked rather than hidden:
                    // the API genuinely can drive it.
                    let reachable = crate::sentences::intent_is_reachable(id);
                    let fjson: Vec<String> =
                        fields.iter().map(|f| format!("\"{}\"", json_escape(f))).collect();
                    intents.push(format!(
                        "{{\"id\":\"{}\",\"title\":\"{}\",\"fields\":[{}],\"by_sentence\":{}}}",
                        json_escape(id),
                        json_escape(title),
                        fjson.join(","),
                        reachable
                    ));
                }
                let mods = match crate::mods::profile_root() {
                    Some(p) => crate::mods::read_mods(&p).unwrap_or_default(),
                    None => Vec::new(),
                };
                let cfg = crate::ai::config();
                let (avail, model) = match &cfg {
                    Some(c) => ("true", format!("\"{}\"", json_escape(&c.model))),
                    None => ("false", "null".to_string()),
                };
                let json = format!(
                    "{{\"ok\":true,\"version\":\"native\",\"civs\":[{}],\
                     \"intents\":[{}],\"mods\":{},\"available\":{},\
                     \"model\":{},\"unit_count\":{},\"tech_count\":{},\
                     \"graphic_count\":{},\"raw_bytes\":{},\"parse_ms\":{}}}",
                    civs.join(","),
                    intents.join(","),
                    crate::mods::to_json(&mods),
                    avail,
                    model,
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
                b"{\"ok\":false,\"error\":\"\xe8\xbf\x98\xe5\x9c\xa8\xe8\xaf\xbb\xe5\x8f\x96\xe6\xb8\xb8\xe6\x88\x8f\xe6\x95\xb0\xe6\x8d\xae\",\"intents\":[],\"civs\":[],\"mods\":[],\"available\":false,\"model\":null}".to_vec(),
            ),
        },
        "/api/mods" => match crate::mods::profile_root() {
            Some(root) => match crate::mods::read_mods(&root) {
                Ok(rows) => {
                    let json = format!(
                        "{{\"ok\":true,\"mods\":{}}}",
                        crate::mods::to_json(&rows)
                    );
                    (200, "application/json; charset=utf-8", json.into_bytes())
                }
                Err(e) => (
                    200,
                    "application/json; charset=utf-8",
                    format!(
                        "{{\"ok\":false,\"error\":\"{}\"}}",
                        json_escape(&e.to_string())
                    )
                    .into_bytes(),
                ),
            },
            None => (
                200,
                "application/json; charset=utf-8",
                format!(
                    "{{\"ok\":false,\"error\":\"{}\"}}",
                    json_escape("找不到玩家档案目录")
                )
                .into_bytes(),
            ),
        },
        "/api/install" => {
            // The page builds first (`/api/build`), then asks for the install as a
            // SEPARATE step. That split is deliberate in this product: building is
            // reversible and lives in the caller's own folder, while installing
            // writes into the player's profile and changes what the game loads.
            // Folding it into build (which this server also supports via
            // `install: true`) must not remove the standalone step.
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => {
                    return (
                        400,
                        "application/json; charset=utf-8",
                        b"{\"ok\":false}".to_vec(),
                    )
                }
            };
            let dir = req.get("mod_dir").and_then(|v| v.as_str()).unwrap_or("");
            let name = req
                .get("name")
                .and_then(|v| v.as_str())
                .filter(|s| !s.trim().is_empty())
                .map(|s| s.to_string())
                .unwrap_or_else(|| {
                    std::path::Path::new(dir)
                        .file_name()
                        .map(|f| f.to_string_lossy().into_owned())
                        .unwrap_or_default()
                });
            let json = if dir.is_empty() || !std::path::Path::new(dir).is_dir() {
                format!(
                    "{{\"ok\":false,\"error\":\"{}\"}}",
                    json_escape("要装的模组文件夹不存在；先生成再安装")
                )
            } else {
                match crate::mods::profile_root() {
                    None => format!(
                        "{{\"ok\":false,\"error\":\"{}\"}}",
                        json_escape("找不到玩家档案目录")
                    ),
                    Some(prof) => {
                        let built = crate::build::Built {
                            dir: std::path::PathBuf::from(dir),
                            title: name.clone(),
                            dat_bytes: 0,
                            compressed: Vec::new(),
                        };
                        match crate::build::install_local(&prof, &built, &name) {
                            Ok(dest) => {
                                let rows = crate::mods::read_mods(&prof).unwrap_or_default();
                                format!(
                                    "{{\"ok\":true,\"installed\":\"{}\",\"mods\":{}}}",
                                    json_escape(&dest.display().to_string()),
                                    crate::mods::to_json(&rows)
                                )
                            }
                            Err(e) => format!(
                                "{{\"ok\":false,\"error\":\"{}\"}}",
                                json_escape(&e)
                            ),
                        }
                    }
                }
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
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
        "/api/rebuild" => {
            let req: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => return (400, "application/json; charset=utf-8", b"{\"ok\":false}".to_vec()),
            };
            let title = req.get("title").and_then(|v| v.as_str()).unwrap_or("");
            let json = match crate::rebuild::rebuild(server, title) {
                Ok(v) => v.to_string(),
                Err(e) => format!(
                    "{{\"ok\":false,\"error\":\"{}\"}}",
                    json_escape(&e)
                ),
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
        "/api/ai-meta" => {
            // Keyless and makes no call: the page reads `available` to decide
            // whether to draw the AI box at all.
            let app_dir = app_dir_of(&server.root);
            let v = crate::ai::meta_json(&app_dir);
            (200, "application/json; charset=utf-8", v.to_string().into_bytes())
        }
        "/api/browse" => {
            // `?kind=unit&limit=400&q=...&offset=0`
            let q: std::collections::HashMap<String, String> = _query
                .split('&')
                .filter_map(|kv| kv.split_once('='))
                .map(|(k, v)| (k.to_string(), percent_decode(v)))
                .collect();
            let kind = q.get("kind").cloned().unwrap_or_else(|| "unit".into());
            let query = q.get("q").cloned().unwrap_or_default();
            let limit: usize = q.get("limit").and_then(|v| v.parse().ok()).unwrap_or(60);
            let offset: usize = q.get("offset").and_then(|v| v.parse().ok()).unwrap_or(0);
            let names = crate::describe::entity_names();
            let icon_ids = {
                let root = crate::game_root();
                match root {
                    Some(r) => {
                        let dat = r.join("resources/_common/dat/empires2_x2_p1.dat");
                        match aoe2mod_dat::load_dat(&dat) {
                            Ok((raw, _)) => {
                                let table = crate::stats::StatTable::load(&crate::stats_path())
                                    .unwrap_or_else(|_| empty_stat_table());
                                crate::browse::icon_ids_from_dat(&raw, &table)
                            }
                            Err(_) => std::collections::HashMap::new(),
                        }
                    }
                    None => std::collections::HashMap::new(),
                }
            };
            let v = crate::browse::browse(&names, &icon_ids, &kind, &query, limit, offset);
            (200, "application/json; charset=utf-8", v.to_string().into_bytes())
        }
        "/api/describe" => {
            let q: std::collections::HashMap<String, String> = _query
                .split('&')
                .filter_map(|kv| kv.split_once('='))
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect();
            let kind = q.get("kind").cloned().unwrap_or_else(|| "unit".into());
            let id: i16 = q.get("id").and_then(|v| v.parse().ok()).unwrap_or(-1);
            let json = match server.parsed.lock().unwrap().clone() {
                None => format!(
                    "{{\"ok\":false,\"error\":\"{}\"}}",
                    json_escape("游戏数据还没读完")
                ),
                Some(parsed) => {
                    let offsets_path = crate::stats_path();
                    match crate::stats::StatTable::load(&offsets_path) {
                        Err(e) => format!(
                            "{{\"ok\":false,\"error\":\"{}\"}}",
                            json_escape(&format!("读不到属性偏移表：{e}"))
                        ),
                        Ok(table) => {
                            let root = crate::game_root();
                            let raw = root
                                .as_ref()
                                .and_then(|r| {
                                    aoe2mod_dat::load_dat(
                                        &r.join("resources/_common/dat/empires2_x2_p1.dat"),
                                    )
                                    .ok()
                                })
                                .map(|(b, _)| b)
                                .unwrap_or_default();
                            let names = crate::describe::entity_names();
                            match crate::describe::describe(
                                &parsed, &table, &raw, &names, &kind, id,
                            ) {
                                Ok(v) => {
                                    format!("{{\"ok\":true,\"entity\":{}}}", v)
                                }
                                Err(e) => format!(
                                    "{{\"ok\":false,\"error\":\"{}\"}}",
                                    json_escape(&e)
                                ),
                            }
                        }
                    }
                }
            };
            (200, "application/json; charset=utf-8", json.into_bytes())
        }
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
