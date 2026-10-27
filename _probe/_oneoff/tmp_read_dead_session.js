// Show the tail of the dead session: the last few user turns and what the
// assistant was doing when it died.  Streams the zstd file through node's own
// zlib so nothing huge lands in memory or on disk.
const fs = require("fs");
const zlib = require("zlib");

const P = "C:/Users/26913/.dsh/sessions/--D-Software-AI-~5E1D~56FD~9879~76EE--/session-df07a428-71b2-447c-a429-3c956dea51f4/session.v4.jsonl.zstd";
const WANT = Number(process.argv[2] || 12);   // how many trailing records
const FILTER = process.argv[3] || "";         // optional substring filter

const raw = zlib.zstdDecompressSync(fs.readFileSync(P));
const text = raw.toString("utf8");
const lines = text.split("\n").filter(Boolean);
console.log("decompressed " + raw.length + " bytes, " + lines.length + " records");

function brief(obj) {
  // Pull out just enough to see who said what; schema varies, so probe.
  const t = obj.type || obj.kind || obj.event || "?";
  const role = obj.role || (obj.message && obj.message.role) || "";
  let body = "";
  if (obj.text) body = obj.text;
  else if (typeof obj.content === "string") body = obj.content;
  else if (Array.isArray(obj.content)) {
    body = obj.content.map((c) =>
      typeof c === "string" ? c : (c.text || c.content || JSON.stringify(c).slice(0, 200))
    ).join(" | ");
  } else if (obj.message) {
    const m = obj.message;
    if (typeof m.content === "string") body = m.content;
    else if (Array.isArray(m.content)) {
      body = m.content.map((c) =>
        typeof c === "string" ? c : (c.text || JSON.stringify(c).slice(0, 200))
      ).join(" | ");
    }
  } else if (obj.tool) {
    body = obj.tool + " " + JSON.stringify(obj.input || obj.args || {}).slice(0, 300);
  }
  body = String(body).replace(/\s+/g, " ").slice(0, 400);
  return { t, role, body };
}

const out = [];
for (const line of lines) {
  let o;
  try { o = JSON.parse(line); } catch { continue; }
  const b = brief(o);
  if (!b.body) continue;
  if (FILTER && !(b.body.includes(FILTER) || b.t.includes(FILTER))) continue;
  out.push(b);
}
const tail = out.slice(-WANT);
for (const b of tail) {
  console.log("---");
  console.log("[" + b.t + (b.role ? "/" + b.role : "") + "] " + b.body);
}
