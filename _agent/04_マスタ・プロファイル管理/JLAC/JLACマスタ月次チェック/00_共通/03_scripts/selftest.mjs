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
// v17〜：新規行1行と既設行1行の重複は、既設行に削除・新規行に適用開始日の修正を依頼する文面にする（隣の条件は従来の文面）
{
  const oldR = clone(good); oldR.xrow = 100; oldR.s[C.START] = '00000000';
  const newR = clone(good); newR.xrow = 200; newR.s[C.START] = '20261015';
  const isNew = (r) => r.xrow >= 200;
  const m = (rows) => new Map(T_.groupFindings(rows, [good], isNew).filter(f => f[1] === 'KA-31').map(f => [f[0].xrow, f[2]]));
  const a = m([oldR, newR]);
  const same = m([oldR, Object.assign(clone(newR), { s: Object.assign([...newR.s], { [C.START]: '00000000' }) })]);
  const three = m([oldR, newR, Object.assign(clone(oldR), { xrow: 150 })]);
  const bothNew = m([Object.assign(clone(newR), { xrow: 201 }), newR]);
  const nodef = new Map(T_.groupFindings([oldR, newR], [good]).filter(f => f[1] === 'KA-31').map(f => [f[0].xrow, f[2]]));
  for (const [label, ok] of [
    ['新規×既設：既設行に削除を依頼', /200行目に別途新規の行として起票.*本行は削除いただけますでしょうか/.test(a.get(100) || '')],
    ['新規×既設：新規行に開始日の修正を依頼', /100行目（既設行）と重複.*適用開始日（00000000）に合わせて修正/.test(a.get(200) || '')],
    ['開始日が同じなら修正の依頼を外す', !/適用開始日/.test(same.get(200) || 'x') && /削除をお願いしております/.test(same.get(200) || '')],
    ['3行の重複は従来の文面', [...three.values()].every(t => t.includes('3行あります'))],
    ['新規どうしの重複は従来の文面', [...bothNew.values()].every(t => t.includes('2行あります'))],
    ['新規の判定を渡さない呼び出しは従来の文面', [...nodef.values()].every(t => t.includes('2行あります'))],
  ]) { fail += !ok; console.log((ok ? 'OK ' : 'NG ') + 'KA-31依頼文'.padEnd(12) + label); }
}
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
// v19〜：測定法だけ変わり販売名称が前月のままなら、販売名称の確認（その他6）を出す
{
  const pv = mut(C.HANBAI, 'テスト試薬 A‐1'); pv.s[C.METH11] = 'テスト法_テスト試薬 A‐1';
  const nMeth = clone(pv); nMeth.s[C.METH11] = 'テスト法_テスト試薬 A-1';
  const nBoth = clone(nMeth); nBoth.s[C.HANBAI] = 'テスト試薬 A-1';
  const pvU = clone(pv); pvU.s[C.HANBAI] = '別の名前'; const nU = clone(pvU); nU.s[C.METH11] = 'テスト法_テスト試薬 A-1';
  const has = (n, p) => T_.comparePrev(n, p, S).some(c => c[0] === 'STEP1-HANBAI');
  for (const [label, ok] of [['測定法だけ変わり販売名称が前月のまま→確認を出す', has(nMeth, pv)], ['販売名称も変わった行には出さない', !has(nBoth, pv)],
    ['測定法と販売名称が対応しない行には出さない', !has(nU, pvU)], ['測定法が変わっていない行には出さない', !has(clone(pv), pv)]]) { fail += !ok; console.log((ok ? 'OK ' : 'NG ') + 'その他6'.padEnd(13) + label); }
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
    let rr = 0, noteRow = 0, extraRow = 0, zeroRow = 0, noteOkRow = 0, noteNgRow = 0;
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
      if (rr === 7 && String(vals[C.JLAC11] ?? '').trim() !== '' && String(vals[C.START]) === '00000000') { vals[C.START] = 0; zeroRow = rr; }
      // v18〜：連絡用の列のコメントと差分の照合（書いたとおりの変更＝連携済み／違う値＝指摘）
      if ((rr === 8 || rr === 9) && String(vals[C.JLAC11] ?? '').trim() !== '') {
        const old = String(vals[C.HANBAI] ?? ''), nw = old + '改';
        vals[C.HANBAI] = nw;
        vals[32] = `販売名称を${old}から${rr === 8 ? nw : old + '別'}に変更しました。`;
        if (rr === 8) noteOkRow = rr; else noteNgRow = rr;
      }
      raw.push({ r: rr, vals });
    }
    // 新規行の開始行（JLACセンター連絡）以降に、前月と同じコードの行を再掲載する（v16〜：連絡を優先して新規行として扱う）
    const src = raw.find(x => x.r > 10 && String(x.vals[C.JLAC11] ?? '').trim() !== '' && x.vals[C.START] !== 0);
    const dupRow = raw.length + 1;
    raw.push({ r: dupRow, vals: Object.assign([...src.vals], { [C.START]: '20261015', [C.END]: '99999999' }) });
    const name = '模擬提出';
    const fake = { fileName: '模擬提出_20261006.xlsx', sheets: [{ name }], rawRows: async () => raw, headerOf: async () => raw[0].vals };
    const inp2 = { ...inp, target: fake, prev: prevCsv };
    const st2 = await J.defaultSettings(inp2);
    st2.newFromRow = String(dupRow);
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
      // v14で文面を変えた際、文面で数えていたこの通知が出なくなった（v15で修正）。文面に頼らず出ることを確かめる
      ['連絡された新規行は前月に同じコードがあっても新規行として扱う', F.some(f => f.row === dupRow && f.status === '新規行') && !F.some(f => f.row === dupRow && f.status === '既存行'), `${dupRow}行目`],
      ['その行に既存行向けの指摘（KA-M2・M3・その他2〜4）を出さない', !F.some(f => f.row === dupRow && /^(KA-M2|KA-M3|STEP1-)/.test(f.check)), ''],
      ['その行の重複（KA-31）は指摘する', F.some(f => f.row === dupRow && f.check === 'KA-31' && !f.known), ''],
      ['その行について要確認の通知を出す', R.notices.some(n => n.level === '要確認' && n.title.includes('前月FIXに同じJLAC11コードの行がある行')), ''],
      ['コメントどおりの変更は連携済み（指摘しない）', noteOkRow > 0 && F.some(f => f.row === noteOkRow && f.check === 'STEP1-DIFF' && f.known && f.note === '連携済み') && !F.some(f => f.row === noteOkRow && f.check === 'STEP1-DIFF' && !f.known), `${noteOkRow}行目`],
      ['コメントと違う値への変更は指摘する', noteNgRow > 0 && F.some(f => f.row === noteNgRow && f.check === 'STEP1-DIFF' && !f.known), `${noteNgRow}行目`],
      ['コメントがあるのに値が変わっていない行を要確認で通知', R.notices.some(n => n.level === '要確認' && n.title.includes('前月から値が変わっていない行')), `${noteRow}行目`],
      ['適用開始日が数値の0の行で要確認の通知を出す', zeroRow > 0 && F.some(f => f.check === 'KA-18' && f.row === zeroRow && !f.known) && R.notices.some(n => n.level === '要確認' && n.title.includes('数値の0')), zeroRow ? `${zeroRow}行目` : '模擬行を作れず'],
    ];
    for (const [label, ok, info] of chk) { fail += !ok; console.log((ok ? 'OK ' : 'NG ') + '新旧混合'.padEnd(12) + label + ' ' + info); }
  }
}
console.log(`ツール ${J.VERSION}  FAIL ${fail}`);
process.exit(fail ? 1 : 0);
