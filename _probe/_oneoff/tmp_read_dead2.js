// The dead session, read by structure: user turns in order, then the tail of
// the assistant's work.  Records are typed (`user/message`, `tool/call`, ...),
// which is why the generic field probe came back empty.
const fs = require("fs");
const zlib = require("zlib");

const P = "C:/Users/26913/.dsh/sessions/--D-Software-AI-~5E1D~56FD~9879~76EE--/session-df07a428-71b2-447c-a429-3c956dea51f4/session.v4.jsonl.zstd";
const MODE = process.argv[2] || "users";

const text = zlib.zstdDecompressSync(fs.readFileSync(P)).toString("utf8");
const recs = [];
for (const line of text.split("\n")) {
  if (!line) continue;
  try { recs.push(JSON.parse(line)); } catch { /* partial tail */ }
}

function flat(x, depth) {
  if (x == null) return "";
  if (typeof x === "string") return x;
  if (depth > 3) return "";
  if (Array.isArray(x)) return x.map((v) => flat(v, depth + 1)).filter(Boolean).join(" ");
  if (typeof x === "object") {
    for (const k of ["text", "content", "message", "prompt", "summary", "label"]) {
      if (x[k]) return flat(x[k], depth + 1);
    }
    return "";
  }
  return String(x);
}

if (MODE === "users") {
  const users = recs.filter((r) => r.type === "user/message");
  console.log("user messages: " + users.length);
  users.forEach((r, i) => {
    const ts = new Date(r.time).toISOString().replace("T", " ").slice(0, 19);
    const body = flat(r.data, 0).replace(/\s+/g, " ").slice(0, 300);
    console.log("[" + (i + 1) + "] " + ts + " UTC  " + body);
  });
} else if (MODE === "tail") {
  const want = Number(process.argv[3] || 20);
  const keep = recs.filter((r) =>
    ["assistant/message", "tool/call", "tool/result", "user/message"].includes(r.type));
  for (const r of keep.slice(-want)) {
    const ts = new Date(r.time).toISOString().replace("T", " ").slice(11, 19);
    let body = "";
    if (r.type === "tool/call") {
      body = (r.data.name || r.data.tool || "?") + " " +
        JSON.stringify(r.data.input || r.data.args || {}).slice(0, 260);
    } else if (r.type === "tool/result") {
      const t = flat(r.data, 0);
      body = t.replace(/\s+/g, " ").slice(0, 200);
    } else {
      body = flat(r.data, 0).replace(/\s+/g, " ").slice(0, 260);
    }
    console.log(ts + " [" + r.type + "] " + body);
  }
} else if (MODE === "last") {
  const last = recs[recs.length - 1];
  console.log("last record type: " + last.type + "  seq " + last.seq);
  console.log(new Date(last.time).toISOString());
  console.log(JSON.stringify(last.data).slice(0, 1200));
}
