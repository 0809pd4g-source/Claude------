// チェックツール（最新版HTML）の検出力テスト：正常行に1か所ずつ誤りを入れ、該当チェックが発火することを確認する。
// 使い方: node 00_共通/03_scripts/selftest.mjs [--tool <html>] [--month <YYYYMM提出分フォルダ>]  （コード表・前月版は月フォルダの01_input、17桁コードリストは JLAC/20260930_JLACマスター新旧対応表確認 を使う。--month省略時は最新の月フォルダ）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { latestTool, loadCore, codec } from './run_check.mjs';

const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ti = process.argv.indexOf('--tool');
const tool = ti > 0 ? process.argv[ti + 1] : latestTool();
const J = loadCore(tool);
const T_ = J._t, C = J.C;
const ROOT = path.resolve(BASE, '..');  // JLACマスタ月次チェック
const mi = process.argv.indexOf('--month');
const MONTH = mi > 0 ? path.resolve(process.argv[mi + 1]) : path.join(ROOT, fs.readdirSync(ROOT).filter(d => /^\d{6}提出分$/.test(d)).sort().pop());
const IN = path.join(MONTH, '01_input');
const open = async (f) => J.openWorkbook(new Uint8Array(fs.readFileSync(f)), path.basename(f), codec);
const files = fs.readdirSync(IN).filter(f => f.endsWith('.xlsx')).map(f => path.join(IN, f));
const list11 = path.join(ROOT, '..', '20260930_JLACマスター新旧対応表確認', '01_input', 'jlac11_3_1.1b.xlsx');
const wbs = [];
for (const f of files.concat(fs.existsSync(list11) ? [list11] : [])) { const wb = await open(f); wbs.push([J.guessRole(wb), wb]); }
const inp = Object.fromEntries(['target', 'prev', 'jlac10', 'jlac11', 'list11'].map(k => [k, (wbs.find(x => x[0] === k) || [])[1] || null]));
const T = await T_.loadTables(inp);
const st = await J.defaultSettings(inp);
const rows = T_.toRows(st.targetSheets[0], await inp.target.rawRows(st.targetSheets[0]));

const clone = (r) => JSON.parse(JSON.stringify(r));
const good = clone(rows.find(r => r.s[C.DTYPE] === 'PQ' && T_.rowChecks(Object.assign(clone(r), { s: Object.assign([...r.s], { [C.START]: '00000000' }) }), T).every(c => c[1] !== 'strict')));
good.s[C.START] = '00000000';
const mut = (col, val) => { const r = clone(good); r.s[col] = val; r.code = r.s[C.JLAC11].trim(); return r; };
const ids = (r) => new Set(T_.rowChecks(r, T).map(c => c[0]));
let fail = 0;
const expect = (cid, got, label) => { const ok = got.has(cid); fail += !ok; console.log((ok ? 'OK ' : 'NG ') + cid.padEnd(14) + (label || '') + ' ' + [...got].join(',')); };

const cases = [
  ['KA-01', mut(C.FLG_L, 'L')], ['KA-02', mut(C.JLAC11, good.code.slice(0, 16))], ['KA-03', mut(C.KYUKYU, '2')], ['KA-04', mut(C.DATAKUBUN, '3')],
  ['KA-06', mut(C.UNIT, good.s[C.UNIT].toUpperCase() + 'x')], ['KA-07', mut(C.MAT11, '尿')], ['KA-08', mut(C.METH11, 'でたらめ試薬')],
  ['KA-13', mut(C.DTYPE, 'ST')], ['KA-18', mut(C.START, '0')], ['KA-18', mut(C.START, '20261340')], ['KA-18', mut(C.START, '20250229')],
  ['KA-19', mut(C.END, '9999999')], ['KA-20', mut(C.JLAC10, good.s[C.JLAC10].slice(0, 16))], ['KA-21', mut(C.JLAC10, 'ZZZZZ' + good.s[C.JLAC10].slice(5))],
  ['KA-22', mut(C.MAT10, '尿')], ['KA-23', mut(C.METH10, 'でたらめ法')], ['KA-25', mut(C.FHIRNAME, '#N/A')],
  ['KA-27', mut(C.KUBUN, '')], ['KA-28', mut(C.DAIKOMOKU, ' ')], ['KA-29', mut(C.FHIRNAME, '')], ['KA-30', mut(C.FHIRID, '')],
  ['KA-DUMMY', mut(C.JLAC11, good.code.slice(0, 12) + 'XXX' + good.code.slice(15))], ['KA-K', mut(C.UNIT, 'K')],
];
const cd = mut(C.DTYPE, 'CD');
cases.push(['KA-14', cd], ['KA-15', cd], ['KA-16', cd]);
const r26 = clone(good); r26.extra = [33]; cases.push(['KA-26', r26]);
for (const [cid, r] of cases) expect(cid, ids(r));
// 誤検知しないこと（正常値）
for (const [label, r] of [['正常行', good], ['うるう日', mut(C.START, '20240229')], ['KA-07全角カッコ以外', good]]) {
  const strict = T_.rowChecks(r, T).filter(c => c[1] === 'strict');
  const ok = strict.length === 0; fail += !ok; console.log((ok ? 'OK ' : 'NG ') + '誤検知なし'.padEnd(10) + label + ' ' + strict.map(c => c[0]).join(','));
}
// グループ・前月比較
const g2 = clone(good); g2.code = g2.s[C.JLAC11] = good.code.slice(0, 15) + (good.code.slice(15) !== '00' ? '00' : '01'); g2.s[C.ORDER] = '99999'; g2.s[C.FHIRID] = 'OTHER';
let got = new Set(T_.groupFindings([clone(good), g2], [good]).map(f => f[1]));
for (const cid of ['KA-17', 'KA-32', 'KA-10']) expect(cid, got);
got = new Set(T_.groupFindings([good, clone(good)], [good]).map(f => f[1])); expect('KA-31', got);
const o = clone(good); o.code = o.s[C.JLAC11] = good.code.slice(0, 12) + '000' + good.code.slice(15);
got = new Set(T_.groupFindings([o], []).map(f => f[1])); expect('KA-33', got);
const e1 = clone(good); e1.s[C.END] = '20261014'; const o2 = clone(o); o2.s[C.END] = '20261014';
got = new Set(T_.groupFindings([e1, o2], []).map(f => f[1])); expect('KA-34', got);
const known = T_.groupFindings([clone(good), g2], [clone(good), g2]).every(f => f[3]);
fail += !known; console.log((known ? 'OK ' : 'NG ') + '既知判定'.padEnd(12) + '前月にも同じ不整合があれば既知');
const S = { prevLabel: '202609版', expectedStart: '20261015', expectedEnd: '20261014' };
for (const [cid, n, p] of [['KA-M2', mut(C.START, '20261015'), good], ['KA-M3', good, mut(C.END, '20261014')], ['STEP1-END', mut(C.END, '20261001'), good],
  ['STEP1-DIFF', mut(C.HANBAI, '別名'), good], ['STEP1-DIFF表記', mut(C.HANBAI, good.s[C.HANBAI] + '　'), good]]) {
  expect(cid, new Set(T_.comparePrev(n, p, S).map(c => c[0])));
}
const okEnd = T_.comparePrev(mut(C.END, '20261014'), good, S).map(c => c[0]);
fail += okEnd.includes('STEP1-END'); console.log((okEnd.includes('STEP1-END') ? 'NG ' : 'OK ') + '切替日前日は指摘しない'.padEnd(10) + okEnd.join(','));
// 新旧混合リストの提出（v12〜）：前月の公開CSVを元に提出を模擬し、JLAC11空欄行の突き合わせと連絡用の列を通しで確認
const csvF = fs.readdirSync(IN).find(f => f.endsWith('.csv'));
const prevCsv = csvF ? await open(path.join(IN, csvF)) : null;
if (!prevCsv) { fail++; console.log('NG 新旧混合    前月の公開CSVが01_inputに無いため実行できません'); }
if (prevCsv) {
  const pr = await prevCsv.rawRows(prevCsv.sheets[0].name);
  const blanks = pr.filter(x => x.r > 1 && String(x.vals[C.JLAC11] ?? '').trim() === '');
  if (blanks.length >= 2) {
    const delR = blanks[0].r, modR = blanks[1].r;
    let rr = 0, noteRow = 0, extraRow = 0;
    const raw = [];
    for (const x of pr) {
      if (x.r === delR) continue;
      const vals = [...x.vals];
      while (vals.length < 32) vals.push('');
      if (x.r === 1) vals.push('JLACセンターコメント');
      else if (x.r === modR) vals[C.FHIRNAME] = vals[C.FHIRNAME] + '（変更）';
      rr++;
      if (rr === 5) { vals[32] = '連絡事項'; noteRow = rr; }
      if (rr === 6) { vals[32] = ''; vals[33] = '34列目の値'; extraRow = rr; }
      raw.push({ r: rr, vals });
    }
    const name = '模擬提出';
    const fake = { fileName: '模擬提出_20261006.xlsx', sheets: [{ name }], rawRows: async () => raw, headerOf: async () => raw[0].vals };
    const inp2 = { ...inp, target: fake, prev: prevCsv };
    const st2 = await J.defaultSettings(inp2);
    const R = await J.run(inp2, st2, null);
    const F = R.findings;
    const del = F.filter(f => f.check === 'STEP1-DEL');
    const modRow2 = raw.findIndex(x => x.vals[C.FHIRNAME] && String(x.vals[C.FHIRNAME]).endsWith('（変更）')) + 1;
    const chk = [
      ['空欄行の削除を1行だけ検出', del.length === 1 && del[0].row === delR, `削除行 ${del.length}件`],
      ['空欄行の変更を既存行の変更として検出', F.some(f => f.check === 'STEP1-DIFF' && f.row === modRow2 && f.status === '既存行'), ''],
      ['空欄行を新規扱いしない', !F.some(f => f.status === '新規行' && f.code === ''), ''],
      ['連絡用の列はKA-26で指摘しない', !F.some(f => f.check === 'KA-26' && f.row === noteRow && !f.known) && F.some(f => f.check === 'KA-26' && f.row === noteRow && f.note === '連絡用の列'), ''],
      ['34列目の値は従来どおりKA-26で指摘', F.some(f => f.check === 'KA-26' && f.row === extraRow && !f.known), ''],
      ['前月の問題の解消を誤表示しない', ![...R.rowDiff.values()].some(d => d.label.includes('前月の問題が解消')), ''],
    ];
    for (const [label, ok, info] of chk) { fail += !ok; console.log((ok ? 'OK ' : 'NG ') + '新旧混合'.padEnd(12) + label + ' ' + info); }
  }
}
console.log(`ツール ${J.VERSION}  FAIL ${fail}`);
process.exit(fail ? 1 : 0);
