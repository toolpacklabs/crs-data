// Computes expected CRS totals by executing IRCC's own calculator script.
//
// Why this exists: golden cases must not be derived from our app. IRCC publishes the
// calculator's scoring code at a stable URL; running it headlessly is a stronger oracle
// than retyping numbers from screenshots, because anyone can re-run it and get the same
// bytes. Only the DOM is stubbed; every point value and every branch is IRCC's code.
//
// Scope: single applicants with no foreign work, no certificate, no sibling, no second
// official language, no Canadian post-secondary credential, no job offer and no
// high-wage Canadian work. The script itself still contains the pre-2026-11-03 job-offer
// code, which is why the scope excludes job offers.
//
// Usage: node tools/official_crs.mjs fixtures/golden/profiles.csv > fixtures/golden/golden_cases.csv
import crypto from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';

const TOOL_URL = 'https://ircc.canada.ca/english/immigrate/skilled/crs-tool-udit.js';
const TOOL_SHA256 = '2dbc3dc028526afd00f5f40a94444594558916485c7a3175cea77bc4e881ac26';
const CACHE = new URL('./.cache/crs-tool-udit.js', import.meta.url);

async function loadTool() {
  fs.mkdirSync(new URL('./.cache/', import.meta.url), { recursive: true });
  let buf;
  if (fs.existsSync(CACHE)) {
    buf = fs.readFileSync(CACHE);
  } else {
    const res = await fetch(TOOL_URL);
    if (!res.ok) throw new Error(`official tool fetch failed: ${res.status}`);
    buf = Buffer.from(await res.arrayBuffer());
    fs.writeFileSync(CACHE, buf);
  }
  const sha = crypto.createHash('sha256').update(buf).digest('hex');
  if (sha !== TOOL_SHA256) {
    throw new Error(`official tool changed: expected ${TOOL_SHA256}, got ${sha}. Re-read the page before trusting new numbers.`);
  }
  return { src: buf.toString('utf8'), sha };
}

const AGE_VALUE = (() => {
  const m = {};
  const letters = [];
  for (let c = 'A'.charCodeAt(0); c <= 'Z'.charCodeAt(0); c++) letters.push(String.fromCharCode(c));
  letters.push('AA', 'AB', 'AC');
  letters.forEach((letter, i) => { m[17 + i] = letter; }); // A=17 or less ... AC=45 or more
  return m;
})();

const EDUCATION_VALUE = {
  LESS_THAN_SECONDARY: 'A', SECONDARY: 'B', ONE_YEAR: 'C', TWO_YEAR: 'D',
  BACHELOR: 'E', TWO_OR_MORE: 'F', MASTERS: 'G', DOCTORAL: 'H',
};

const CELPIP_VALUE = { 4: 'B', 5: 'C', 6: 'D', 7: 'E', 8: 'F', 9: 'G', 10: 'H' };

function runCase(src, c) {
  if (c.spouse !== 'SINGLE') throw new Error(`${c.case_id}: golden cases must be SINGLE`);
  if (c.french !== 'false') throw new Error(`${c.case_id}: French is not modelled by the official tool the same way`);
  const answers = {};
  function makeNode(sel) {
    const id = (/#([A-Za-z0-9_-]+)/.exec(sel) || [])[1] || '';
    const totalsBox = runCase.box;
    return new Proxy({}, {
      get(_, prop) {
        if (prop === 'val') return () => answers[id] ?? '';
        if (prop === 'submit') return (fn) => { if (id === 'crs-form') runCase.handler = fn; };
        if (typeof prop === 'symbol') return undefined;
        return () => makeNode(sel);
      },
      set(_, prop, value) {
        if (prop === 'innerHTML') totalsBox[id] = value;
        return true;
      },
    });
  }
  const sandbox = {
    console, parseInt, Math, JSON, window: {}, alert: () => {},
    $: (sel) => makeNode(sel),
    document: { getElementById: (id) => makeNode('#' + id) },
  };
  runCase.box = {};
  runCase.handler = null;
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: 'crs-tool-udit.js' });
  if (!runCase.handler) throw new Error('submit handler not captured');
  Object.assign(sandbox, { with_spouse: false, show_spouse: false, fol_lang: 'en' });
  const clbLetter = CELPIP_VALUE[Number(c.first_language_clb)];
  Object.assign(answers, {
    q1: 'F', q2i: 'A', q2ii: 'A',
    q3: AGE_VALUE[Math.min(Number(c.age), 45)],
    q4: EDUCATION_VALUE[c.education],
    q4b: 'A', q4c: 'A',
    q5i: 'A', 'q5i-a': 'A',
    'q5i-b-speaking': clbLetter, 'q5i-b-listening': clbLetter,
    'q5i-b-reading': clbLetter, 'q5i-b-writing': clbLetter,
    q5ii: 'F', 'q5ii-sol-speaking': 'badvalue', 'q5ii-sol-listening': 'badvalue',
    'q5ii-sol-reading': 'badvalue', 'q5ii-sol-writing': 'badvalue',
    q6i: ['A', 'B', 'C', 'D', 'E', 'F'][Math.min(Number(c.canadian_work_years), 5)],
    q6ii: 'A',
    q7: 'A', q8: 'A', q9: 'A', q10i: 'A',
    q10: 'A', q11: 'A', q12i: 'F',
    'q12ii-fol-speaking': 'badvalue', 'q12ii-fol-listening': 'badvalue',
    'q12ii-fol-reading': 'badvalue', 'q12ii-fol-writing': 'badvalue',
  });
  runCase.handler({ preventDefault() {} });
  const text = String(runCase.box.totals || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ');
  const m = /grand total\s*=\s*(\d+)/i.exec(text);
  if (!m) throw new Error(`${c.case_id}: no grand total in official output`);
  return Number(m[1]);
}

const { src, sha } = await loadTool();
const lines = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n');
const header = lines[0].split(',');
const rows = lines.slice(1).map((line) => Object.fromEntries(line.split(',').map((v, i) => [header[i], v])));
const out = ['case_id,age,education,first_language_clb,canadian_work_years,french,spouse,expected_score,source_url,evidence'];
for (const c of rows) {
  const total = runCase(src, c);
  out.push([c.case_id, c.age, c.education, c.first_language_clb, c.canadian_work_years,
    c.french, c.spouse, total,
    'https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score.html',
    `official-crs-tool.js sha256:${sha}`].join(','));
}
console.log(out.join('\n'));
