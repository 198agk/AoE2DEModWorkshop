//! Handing the player's workshop session to the engine.
//!
//! Why this exists
//! ---------------
//! `https://api.ageofempires.com/api/v4/mods/Find` answers 401 to everyone who
//! is not signed in -- measured 2026-11-15: `errorCode 900`, `"Access Denied -
//! User not authenticated."`, with both flat and nested bodies.  There is no
//! anonymous listing at all; the marketing site's own `/mods/` page fires zero
//! requests to that API until the browser holds a session, and paints an empty
//! list otherwise.
//!
//! What the session actually *is*
//! ------------------------------
//! Cookies, nothing else.  The theme bundle (`main.2dd3a1.js`) contains no
//! `Authorization` header, no CSRF token, no `beforeSend` hook -- it sets
//! `xhrFields.withCredentials = true` and lets the browser attach the cookie.
//! So the only way to reproduce a signed-in request from outside a browser is
//! to obtain the same cookie values.
//!
//! Why it has to come from Rust and not from the page
//! --------------------------------------------------
//! The session cookies are `HttpOnly` (measured: `AgeAuthSession=...; path=/;
//! secure; samesite=none; httponly`), so page JavaScript cannot read them, and
//! `document.cookie` cannot set them either.  WebView2 can, through the host's
//! cookie manager -- which is what `WebviewWindow::cookies_for_url` wraps.
//!
//! What crosses the boundary
//! -------------------------
//! The cookie values go to disk in the state directory the Python engine
//! already owns (`%LOCALAPPDATA%\aoe2de-mod-workshop\`), and the values are
//! NEVER returned to the page: `SessionInfo` carries names and counts only.
//! A page that could read the values could exfiltrate the player's account
//! session to any origin it liked; a page that can only learn "8 cookies were
//! saved" cannot.
//!
//! The file is written into `LOCALAPPDATA`, which Windows already restricts to
//! the current user, and it is overwritten on every call rather than merged, so
//! a signed-out state cannot leave a stale cookie behind.

use std::io::Write;
use std::time::{SystemTime, UNIX_EPOCH};

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

/// Where the Python engine looks.  Kept identical to
/// `aoe2mod/mod/provenance.py:85 state_dir()`, including the two environment
/// overrides, because a test that sandboxes the state directory must not end up
/// writing a real session cookie into the player's profile.
fn state_dir() -> std::path::PathBuf {
    for key in ["AOE2MOD_STATE_DIR", "AOE2MOD_STATE"] {
        if let Ok(v) = std::env::var(key) {
            if !v.is_empty() {
                return std::path::PathBuf::from(v);
            }
        }
    }
    let base = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| {
        let home = std::env::var("USERPROFILE").unwrap_or_default();
        format!("{home}\\.local\\share")
    });
    std::path::PathBuf::from(base).join("aoe2de-mod-workshop")
}

pub fn session_path() -> std::path::PathBuf {
    state_dir().join("online-session.json")
}

/// The two origins whose cookies matter, and the key each is filed under.
///
/// `api` is what `/Find` needs.  `auth` is what `checklogin` needs, and it is a
/// different host, so asking for one URL would miss the other: `cookies_for_url`
/// filters by the URL, and the session cookie is scoped to `.ageofempires.com`
/// with `path=/` for the auth one and `path=/signin-steam` for the correlation
/// cookie.
const ORIGINS: [(&str, &str); 2] = [
    ("api", "https://api.ageofempires.com"),
    ("auth", "https://auth.ageofempires.com"),
];

#[derive(serde::Serialize, Clone)]
pub struct SessionInfo {
    /// Whether at least one cookie was found and written.
    pub saved: bool,
    /// Unix seconds, so the page can say "两分钟前" without trusting its clock
    /// against the engine's.
    pub at: u64,
    /// Cookie names only.  Never values -- see the module comment.
    pub names: Vec<String>,
    /// Absolute path of the file, for the "where did it go" line in settings.
    pub path: String,
}

/// Read the session cookies out of the app's own webview and file them for the
/// engine, then report what was found.
///
/// `async` is not a style choice.  Tauri's own doc comment on
/// `cookies_for_url` says: "On Windows, this function deadlocks when used in a
/// synchronous command or event handlers ... You should use `async` commands and
/// separate threads when reading cookies."  A plain `fn` here compiles and then
/// hangs the IPC thread on the first click.
#[tauri::command]
pub async fn online_session(app: AppHandle) -> Result<SessionInfo, String> {
    let win = app
        .get_webview_window("workshop")
        .ok_or_else(|| "找不到主窗口，会话读不出来。".to_string())?;

    let mut pairs: Vec<(String, String)> = Vec::new();
    let mut names: Vec<String> = Vec::new();
    let mut seen: Vec<String> = Vec::new();

    for (key, origin) in ORIGINS {
        let url = origin
            .parse()
            .map_err(|e| format!("地址读不懂（{origin}）：{e}"))?;
        let jar = win
            .cookies_for_url(url)
            .map_err(|e| format!("读 cookie 失败：{e}"))?;
        if jar.is_empty() {
            continue;
        }
        let mut header = String::new();
        for c in &jar {
            if !header.is_empty() {
                header.push_str("; ");
            }
            header.push_str(c.name());
            header.push('=');
            header.push_str(c.value());
            // The same cookie can come back for both origins; report each name
            // once so the count means "cookies", not "cookies times hosts".
            if !seen.iter().any(|n| n == c.name()) {
                seen.push(c.name().to_string());
                names.push(c.name().to_string());
            }
        }
        pairs.push((key.to_string(), header));
    }

    let at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    if pairs.is_empty() {
        // Nothing to write.  Do not touch a file that might hold a session the
        // login window has not landed in yet -- an empty read during the OAuth
        // redirect would otherwise erase a working session.
        return Ok(SessionInfo {
            saved: false,
            at,
            names,
            path: session_path().to_string_lossy().to_string(),
        });
    }

    let dir = state_dir();
    std::fs::create_dir_all(&dir).map_err(|e| format!("建不了状态目录 {dir:?}：{e}"))?;
    let path = session_path();

    // Hand-rolled so the shape is obvious and stable for the Python reader:
    //   {"savedAt": 1763..., "cookies": {"api": "a=b; c=d", "auth": "..."}}
    let mut body = String::from("{\"savedAt\":");
    body.push_str(&at.to_string());
    body.push_str(",\"cookies\":{");
    for (i, (k, v)) in pairs.iter().enumerate() {
        if i > 0 {
            body.push(',');
        }
        body.push('"');
        body.push_str(k);
        body.push_str("\":\"");
        for ch in v.chars() {
            // Cookie values are already header-safe, but a stray quote or
            // backslash would produce a file that reads as corrupt and silently
            // signs the player out; escape rather than hope.
            match ch {
                '"' => body.push_str("\\\""),
                '\\' => body.push_str("\\\\"),
                '\n' => body.push_str("\\n"),
                '\r' => body.push_str("\\r"),
                c => body.push(c),
            }
        }
        body.push('"');
    }
    body.push_str("}}");

    let tmp = path.with_extension("json.tmp");
    {
        let mut fh = std::fs::File::create(&tmp)
            .map_err(|e| format!("写不了会话文件 {tmp:?}：{e}"))?;
        fh.write_all(body.as_bytes())
            .map_err(|e| format!("写会话文件失败：{e}"))?;
        fh.flush().map_err(|e| format!("落盘失败：{e}"))?;
    }
    // Rename over the old one: a reader never sees half a file, and a crash
    // between create and flush leaves the previous session intact.
    std::fs::rename(&tmp, &path).map_err(|e| format!("替换会话文件失败：{e}"))?;

    Ok(SessionInfo {
        saved: true,
        at,
        names,
        path: path.to_string_lossy().to_string(),
    })
}

/// Open the official sign-in page in a real webview of its own.
///
/// Not a link in the player's browser, because the cookie has to land in THIS
/// app's WebView2 profile for `online_session` to read it.  Not an iframe in the
/// page either: `www.ageofempires.com` sends `X-Frame-Options: SAMEORIGIN` and
/// `Content-Security-Policy: frame-ancestors 'none'`, so a frame is refused
/// outright (measured 2026-11-15).
///
/// Decorations stay ON here, unlike the main window.  This window shows a
/// third-party page whose own close button does not exist, and without a frame
/// there is no way to dismiss it if the login stalls.
///
/// `provider` picks the door, because the two accounts are not interchangeable:
/// a Steam copy signs in through Steam's OpenID and a Microsoft/Game Pass copy
/// through `login.microsoftonline.com`.  Asking the wrong one lands on a form
/// for an account the player does not have.  Measured 2026-11-15:
///
/// - `auth.ageofempires.com/loginsteam` -> 302 to `steamcommunity.com/openid/`
/// - `auth.ageofempires.com/`           -> 302 to `login.microsoftonline.com`
///
/// `loginxbox`, `loginmicrosoft`, `login` are all 404, so the bare root is the
/// only Microsoft door.
#[tauri::command]
pub async fn online_login(app: AppHandle, provider: Option<String>) -> Result<(), String> {
    let steam = provider.as_deref() != Some("microsoft");
    let (url, title) = if steam {
        (
            "https://auth.ageofempires.com/loginsteam",
            "登录 Age of Empires 账号 · Steam",
        )
    } else {
        (
            "https://auth.ageofempires.com/",
            "登录 Age of Empires 账号 · 微软",
        )
    };
    if let Some(w) = app.get_webview_window("aoe-login") {
        // Re-use the window, but send it to the right door: a player who first
        // picked Steam and then said "no, I use Microsoft" should not have to
        // close it by hand.
        let _ = w.navigate(url.parse().map_err(|e| format!("登录地址读不懂：{e}"))?);
        let _ = w.set_title(title);
        let _ = w.unminimize();
        let _ = w.set_focus();
        return Ok(());
    }
    WebviewWindowBuilder::new(
        &app,
        "aoe-login",
        WebviewUrl::External(url.parse().map_err(|e| format!("登录地址读不懂：{e}"))?),
    )
    .title(title)
    .inner_size(520.0, 760.0)
    .min_inner_size(420.0, 560.0)
    .center()
    .decorations(true)
    .build()
    .map_err(|e| format!("打不开登录窗：{e}"))?;
    Ok(())
}

/// What a sign-out actually removed, so the page can say it out loud instead of
/// pretending the button worked.
#[derive(serde::Serialize, Clone)]
pub struct SignOut {
    /// Cookies the webview acknowledged deleting (both origins, deduplicated).
    pub cookies: usize,
    /// Cookie names, never values -- same rule as [`SessionInfo::names`].
    pub names: Vec<String>,
    /// Whether the session file that the engine reads still exists afterwards.
    pub file: bool,
    /// Close the login window if it was somehow still open.
    pub window: bool,
}

/// Sign the player out: delete the Age of Empires cookies from this app's own
/// WebView2 profile and remove the session file the engine reads.
///
/// Two halves, because the credential lives in two places:
///
///   1. The webview's cookie jar.  `cookies_for_url` returns each cookie with
///      the domain, path, secure and same-site flags already filled in, and
///      wry's Windows `delete_cookie` rebuilds an `ICoreWebView2Cookie` from
///      exactly those fields before calling `DeleteCookie` -- so reading them
///      out and handing them straight back deletes the right cookie, not "a
///      cookie with the same name somewhere else".
///   2. `%LOCALAPPDATA%\aoe2de-mod-workshop\online-session.json`, which is what
///      the Python engine reads on every call.  Deleting the cookies alone
///      would leave a signed-in header on disk until the next
///      `online_session`, and that file is the one a user would point at when
///      asking "is this thing still holding my account?".
///
/// `clear_all_browsing_data` is deliberately NOT used: it also wipes local
/// storage, and the page keeps its own preferences there -- the player's theme,
/// window size and column state would vanish along with the login.
///
/// `async` for the same reason as [`online_session`]: touching cookies from a
/// synchronous command deadlocks the IPC thread on Windows.
#[tauri::command]
pub async fn online_signout(app: AppHandle) -> Result<SignOut, String> {
    let win = app
        .get_webview_window("workshop")
        .ok_or_else(|| "找不到主窗口，退不出去。".to_string())?;

    let mut names: Vec<String> = Vec::new();
    let mut count = 0usize;

    for (_key, origin) in ORIGINS {
        let url = origin
            .parse()
            .map_err(|e| format!("地址读不懂（{origin}）：{e}"))?;
        let jar = win
            .cookies_for_url(url)
            .map_err(|e| format!("读 cookie 失败：{e}"))?;
        for cookie in jar {
            let name = cookie.name().to_string();
            // A cookie scoped to `.ageofempires.com` comes back for BOTH
            // origins.  Deleting it twice is harmless but counting it twice
            // would make the receipt wrong.
            if names.iter().any(|n| n == &name) {
                continue;
            }
            match win.delete_cookie(cookie) {
                Ok(()) => {
                    count += 1;
                    names.push(name);
                }
                // One stubborn cookie must not abort the sign-out: the rest
                // still have to go, and the session file below is the part the
                // engine actually trusts.
                Err(_) => {}
            }
        }
    }

    let path = session_path();
    let file = path.exists();
    if file {
        std::fs::remove_file(&path).map_err(|e| format!("删不掉会话文件 {path:?}：{e}"))?;
    }

    let mut window = false;
    if let Some(w) = app.get_webview_window("aoe-login") {
        let _ = w.close();
        window = true;
    }

    Ok(SignOut {
        cookies: count,
        names,
        file: !path.exists(),
        window,
    })
}
