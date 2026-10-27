const fs = require("fs");
const lines = fs.readFileSync("aoe2mod/ui/static/index.html", "utf8").split("\n");
function txt(a, b) {
  let s = lines.slice(a - 1, b).join("\n");
  s = s.replace(/<!--[\s\S]*?-->/g, "");
  s = s.replace(/<[^>]+>/g, "\n");
  s = s.replace(/[ \t]+/g, "");
  return s.split("\n").map((x) => x.trim()).filter(Boolean);
}
for (const [label, a, b] of [["home-header", 701, 715], ["card1", 717, 798], ["card2", 800, 815]]) {
  const parts = txt(a, b);
  console.log("==", label, "blocks", parts.length, "chars", parts.reduce((n, p) => n + p.length, 0));
  for (const p of parts) console.log("   ", p.length, p.slice(0, 70));
}
