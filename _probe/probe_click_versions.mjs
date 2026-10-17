// Compare dsh-click@0.3.19 (installed) against the newest release whose cordis /
// schemastery ranges the host actually satisfies, so the recommendation has
// numbers instead of a version guess.
import { createRequire } from 'node:module';
const require = createRequire('file:///C:/Users/26913/.dsh/profiles/desktop/');
const semver = require('semver');

const HOST = { '@deepseek-ai/cordis': '4.0.4', '@deepseek-ai/schemastery': '3.18.4' };
const WATCH = ['@deepseek-ai/cordis', '@deepseek-ai/schemastery'];

const res = await fetch('https://mirrors.cloud.tencent.com/npm/dsh-click',
  { headers: { accept: 'application/json' } });
const doc = await res.json();
const versions = Object.keys(doc.versions).sort(semver.rcompare);

console.log('host: cordis %s, schemastery %s', HOST['@deepseek-ai/cordis'], HOST['@deepseek-ai/schemastery']);
console.log('');
console.log('version   cordis range                 ok    schemastery range              ok');
for (const v of versions.slice(0, 14)) {
  const peers = doc.versions[v].peerDependencies || {};
  let allOk = true;
  const cells = WATCH.map(p => {
    const range = peers[p] ?? '(none)';
    const ok = range === '(none)' ? true : semver.satisfies(HOST[p], range, { includePrerelease: true });
    if (!ok) allOk = false;
    return [range.padEnd(26), ok ? 'YES' : 'NO '];
  });
  console.log('%s  %s %s  %s %s%s', v.padEnd(9), cells[0][0], cells[0][1], cells[1][0], cells[1][1],
    allOk ? '   <= fits' : '');
}
