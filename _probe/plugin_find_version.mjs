// Ask the market's own "find me a version that works" route for every plugin
// the compatibility engine could not clear.
//
// `POST /dsh-market/find-compatible` is the same call the install button makes
// when the latest version is incompatible: it walks the published versions and
// returns the newest one whose declarations the running kernel satisfies.
// Using it means we do not have to reason about prerelease ranges ourselves.
//
// The route is origin-guarded (`sameOrigin`), so the Origin header must be the
// market's own page origin.
const BASE = 'http://127.0.0.1:19387/dsh-market';
const ORIGIN = 'http://127.0.0.1:19387';

const WANT = process.argv.slice(2).filter(a => !a.startsWith('-'));

async function findCompatible(npmName) {
  const res = await fetch(`${BASE}/find-compatible`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', origin: ORIGIN },
    body: JSON.stringify({ npmName }),
  });
  const text = await res.text();
  let body;
  try { body = JSON.parse(text); } catch { body = { raw: text.slice(0, 200) }; }
  return { http: res.status, ...body };
}

let ok = 0, none = 0, failed = 0;
for (const name of WANT) {
  const r = await findCompatible(name);
  if (r.compatibleVersion) {
    ok += 1;
    console.log(`FOUND     ${name.padEnd(42)} -> ${r.compatibleVersion}`);
  } else if (r.http !== 200) {
    failed += 1;
    console.log(`HTTP ${r.http}  ${name.padEnd(42)} ${r.error ?? r.raw ?? ''}`);
  } else {
    none += 1;
    console.log(`none      ${name.padEnd(42)} reason=${r.reason ?? '-'}`);
  }
}
console.log(`\nfound ${ok}  none ${none}  errors ${failed}  (of ${WANT.length})`);
