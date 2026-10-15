// 1回実行化（monthly_run.mjs・ツールv21の根拠の記録）の試験。設計案 5章の T6〜T9 と、出力名の上書き防止。
// 使い方: node 00_共通/03_scripts/test_monthly_run.mjs --json <10/6再提出分の明細.json> [--month 202610提出分]
//   --json に旧版（v20）の明細を渡すと、T6・T7 は不合格になる（根拠の項目が無いため。旧版で落ちることの確認）
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseSettings, checkSettings, checkCarryover, nextName } from './monthly_run.mjs';
import { latestTool, loadCore, codec } from './run_check.mjs';

const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = path.resolve(BASE, '..');
const args = process.argv.slice(2), opt = {};
for (let i = 0; i < args.length; i++) if (args[i].startsWith('--')) opt[args[i].slice(2)] = args[++i];
const MONTH = path.join(ROOT, opt.month || '202610提出分');
let fail = 0;
const ok = (cond, label, info) => { fail += !cond; console.log(`${cond ? 'OK ' : 'NG '}${label}${info ? '  ' + info : ''}`); };

// ---- T6・T7：指摘の根拠（10/6再提出分の明細） ----
if (opt.json) {
  const d = JSON.parse(fs.readFileSync(opt.json, 'utf8'));
  console.log(`明細：${path.basename(opt.json)}（ツール ${d.version}）`);
  const F = d.findings;
  for (const row of [1104, 1138, 1165, 8790, 8814]) {
    const f = F.find(x => x.row === row && x.check === 'KA-08' && x.level === 'strict');
    const b = f && f.basis;
    ok(!!(f && !f.known && b && b.prevSame === '該当（文面が違う）' && /前月も該当/.test(b.knownWhy) && /該当していた既知の行/.test(b.draft) && /変わったため、指摘の文面が前月と変わり/.test(b.draft) && b.prevRow === String(row)),
      `T6 KA-08 既存行 ${row}行目：根拠が「前月も該当・値が変わったため文面が違う」`, b ? `［${b.prevSame}］${b.draft.slice(0, 60)}…` : '根拠なし');
  }
  const f13527 = F.find(x => x.row === 13527 && x.check === 'KA-31');
  ok(!!(f13527 && f13527.basis && /新規行の開始行（13436行目）以降/.test(f13527.basis.newReason)), 'T7 13527行目（開始行以降で前月に同じコード）：新規の理由が「連絡の新規行の開始行以降」', f13527 && f13527.basis ? f13527.basis.newReason : '根拠なし');
  const fNew = F.find(x => x.status === '新規行' && x.level === 'strict' && !x.known && x.row !== 13527);
  ok(!!(fNew && fNew.basis && /同じJLAC11コードが無い/.test(fNew.basis.newReason)), 'T7 新規行：新規の理由が「前月に同じコードが無い」', fNew && fNew.basis ? `${fNew.row}行目 ${fNew.basis.newReason}` : '根拠なし');
  // 前月は該当なし：10/6再提出分には該当行が無いため、既存行で前月比較以外の指摘に「該当なし」の型があるか、無ければ10/1提出版で確かめる旨を出す
  const known = F.filter(x => x.level === 'strict' && x.known && x.basis && x.basis.prevSame === '該当（同じ文面）');
  ok(known.length > 0 && known.every(x => /前月も同じ文面/.test(x.basis.knownWhy)), `T7 既知（前月と同じ文面）の指摘 ${known.length}件：根拠が「前月も同じ文面で該当（既知）」`);
  const strictRow = F.filter(x => x.level === 'strict' && !x.known);
  ok(strictRow.length > 0 && strictRow.every(x => x.basis && x.basis.draft), `T7 コメント対象の指摘 ${strictRow.length}件すべてに説明文の下書きがある`);
  checkJudgeVsBasis(F, '10/6');
  // 試験が中身で落ちることの確認：既知の指摘1件の判定を書き換えた明細では、食い違い1件を検出する
  { const G = JSON.parse(JSON.stringify(F)); const t = G.find(x => x.level === 'strict' && !x.note && x.known && x.basis && x.basis.prevSame === '該当（同じ文面）'); t.known = false;
    const r = checkJudgeVsBasis(G, '改ざん', true); ok(r.notButKnown === 1 && r.knownButNot === 0, 'T6/T7 落ちることの確認：既知1件を既知でないに書き換えると、食い違い1件を検出する', `検出 ${r.notButKnown}件`); }
  const k8 = F.find(x => x.row === 1104 && x.check === 'KA-08' && x.level === 'strict');
  ok(!!(k8 && k8.basis && k8.basis.prevHitRow === 1104 && /前月（202609版）の1104行目も/.test(k8.basis.draft)), 'T6 下書きの前月の行番号＝実際にKA-08に当たっていた前月の行（1104行目）', k8 && k8.basis ? `prevHitRow=${k8.basis.prevHitRow}` : '根拠なし');
}
// 判定と根拠の突き合わせ（中身で落ちる試験）：連携済み・共有対象外などの note が無い strict の指摘すべてで、
// 行ごとのチェックは「既知 ⇔ 前月の同じチェック＝該当（同じ文面）」、同じキーのチェックは「既知 ⇔ 前月にも同じ組合せ」。どちら向きの食い違いも0件
function checkJudgeVsBasis(F, label, quiet) {
  const ROWV = new Set(['該当なし', '該当（同じ文面）', '該当（文面が違う）']);
  const tgt = F.filter(x => x.level === 'strict' && !x.note && x.status !== '削除行');
  let nRow = 0, nGrp = 0, knownButNot = 0, notButKnown = 0, missing = 0;
  for (const f of tgt) {
    const b = f.basis;
    if (!b) { missing++; continue; }
    let should;
    if (ROWV.has(b.prevSame)) { nRow++; should = b.prevSame === '該当（同じ文面）'; }
    else if (/組合せ・状態/.test(b.prevSame)) { nGrp++; should = b.prevSame.startsWith('該当'); }
    else continue; // 前月比較そのものの確認（既知の判定をしない）
    if (f.known && !should) knownButNot++;
    if (!f.known && should) notButKnown++;
  }
  if (quiet) return { nRow, nGrp, knownButNot, notButKnown, missing };
  ok(missing === 0 && nRow > 0 && knownButNot === 0 && notButKnown === 0,
    `T6/T7 ${label}：判定（既知か）と根拠が食い違わない（行ごと${nRow}件・同じキー${nGrp}件。既知なのに根拠は既知でない ${knownButNot}件／既知でないのに根拠は既知 ${notButKnown}件／根拠なし ${missing}件）`);
}
if (opt.json2) { // 10/1提出版：「前月は該当なし」の既存行（KA-18 数値の0）
  const d = JSON.parse(fs.readFileSync(opt.json2, 'utf8'));
  const f = d.findings.find(x => x.check === 'KA-18' && x.status === '既存行' && !x.known);
  ok(!!(f && f.basis && f.basis.prevSame === '該当なし' && /該当していません/.test(f.basis.draft) && /「00000000」から「0」/.test(f.basis.draft)), 'T7 前月は該当なしの既存行（10/1提出版のKA-18）：根拠が「前月は該当なし・今回の変更で当たる」', f && f.basis ? f.basis.draft.slice(0, 80) : '根拠なし');
  checkJudgeVsBasis(d.findings, '10/1');
}

// ---- T8：設定の点検（実行せずに止まる） ----
const base = fs.readFileSync(path.join(MONTH, '04_reference', '20261015_今月の設定_202610提出分_1006再提出.txt'), 'utf8');
const stops = (text) => checkSettings(parseSettings(text), MONTH).checks.filter(c => c.level === '止める').map(c => c.item);
ok(stops(base).length === 0, 'T8 10/6再提出の設定：止める0件', stops(base).join('、'));
const cases = [
  ['公開日を空にする', base.replace(/^公開日: .*$/m, '公開日:'), '公開日'],
  ['公開日を15日以外にして理由なし', base.replace(/^公開日: .*$/m, '公開日: 20261016'), '公開日'],
  ['対象月が前月のまま（202609）', base.replace(/^対象月: .*$/m, '対象月: 202609'), '対象月'],
  ['提出日が前月のまま（20260915）', base.replace(/^提出日: .*$/m, '提出日: 20260915'), '提出日'],
  ['新規行の開始行が空でメールに「行目」', base.replace(/^新規行の開始行: .*$/m, '新規行の開始行:'), '新規行の開始行'],
  ['提出ファイルが無い', base.replace(/^提出ファイル: .*$/m, '提出ファイル: 無いファイル.xlsx'), '提出ファイル'],
  ['判断待ちの切り替えに知らない値', base.replace(/^判断の線引き: .*$/m, '判断の線引き: 決めた'), '判断の線引き'],
  ['17桁を毎月取り直す設定で取得日が古い', base.replace(/^17桁コードリストの取り直し: .*$/m, '17桁コードリストの取り直し: 毎月').replace(/^17桁コードリストの取得日: .*$/m, '17桁コードリストの取得日: 20260801'), '17桁コードリストの取得日'],
  ['知らないキー', base + '\n新規開始行: 13436\n', '設定ファイルの書き方'],
];
for (const [label, text, item] of cases) { const s = stops(text); ok(s.includes(item), `T8 ${label} → 止まる`, s.join('、')); }
const fifteen = base.replace(/^公開日: .*$/m, '公開日: 20261016').replace(/^公開日が15日でない理由:.*$/m, '公開日が15日でない理由: 15日が休日のため（例）');
ok(!stops(fifteen).includes('公開日'), 'T8 隣の条件：公開日が15日以外でも理由があれば止まらない');
const sw = checkSettings(parseSettings(base.replace(/^判断の線引き: .*$/m, '')), MONTH).switches;
ok(sw['判断の線引き'] === '今のまま', 'T8 判断待ちの切り替えを書かなければ「今のまま」');
const unclosed = base.replace(/^>>>\s*$/m, '');
ok(stops(unclosed).includes('設定ファイルの書き方'), 'T8 「<<<」の閉じ忘れ（「>>>」が無い）→ 止まる', stops(unclosed).join('、'));
const every = base.replace(/^17桁コードリストの取り直し: .*$/m, '17桁コードリストの取り直し: 毎月');
ok(!stops(every.replace(/^17桁コードリストの取得日: .*$/m, '17桁コードリストの取得日: 20260901')).includes('17桁コードリストの取得日'), 'T8 境目：取得日が提出日の前月1日（20260901）なら止まらない');
ok(stops(every.replace(/^17桁コードリストの取得日: .*$/m, '17桁コードリストの取得日: 20260831')).includes('17桁コードリストの取得日'), 'T8 境目：取得日がその前日（20260831）なら止まる');
const warn = (text) => checkSettings(parseSettings(text), MONTH).checks.filter(c => c.level === '注意').map(c => c.item);
ok(!warn(base).includes('前月公開版'), 'T8 前月公開版の名前に前月の「202609」がある（10/6の設定）→ 注意なし');
const b1001 = fs.readFileSync(path.join(MONTH, '04_reference', '20261015_今月の設定_202610提出分_1001提出.txt'), 'utf8');
ok(warn(b1001).includes('前月公開版') && !stops(b1001).includes('前月公開版'), 'T8 前月公開版の名前に「202609」が無い（10/1の9月FIXのxlsx）→ 注意（止めない）');

// ---- T9：前月からの引継ぎ（10/6再提出の提出ファイルに11月用の引継ぎを当てる／模擬ファイル） ----
const J = loadCore(latestTool());
const tgt = path.join(MONTH, '01_input', '1006再提出［令和8年9月末頃以降本番環境適用開始］共有項目JLACコードマスタ_202609_20260915.xlsx');
const wb = await J.openWorkbook(new Uint8Array(fs.readFileSync(tgt)), path.basename(tgt), codec);
const sh = (await J.masterSheets(wb))[0];
const rows = J._t.toRows(sh, await wb.rawRows(sh));
const carry = fs.readFileSync(path.join(MONTH, '04_reference', '20261015_翌月への引継ぎ_202610提出分.txt'), 'utf8');
const st = (res, code, want) => (res.find(x => x.code.startsWith(code) && x.want === want) || {}).state;
let res = checkCarryover(carry, rows, ['区分名称'], J.C);
ok(st(res, 'V2171000025000248（旧12051', '1行だけ') === '未反映', 'T9 10/6の提出：…248 の「1行だけ」は未反映（12051行目がまだある）');
ok(st(res, 'V2171000025000248（旧13527', '適用開始日 00000000') === '未反映', 'T9 10/6の提出：…248 の適用開始日は未反映（13527行目が20261015）');
ok(st(res, 'B10030000211523G3', '有効な行がある') === '未反映', 'T9 10/6の提出：B10030000211523G3 は有効な行が無いので未反映（旧い行だけある）');
ok(res.every(x => x.state !== '確認できない'), `T9 引継ぎ ${res.length}件すべて判定できる`);
const mock = rows.filter(r => r.xrow !== 12051).map(r => (r.xrow === 13527 ? { ...r, s: Object.assign([...r.s], { [J.C.START]: '00000000' }) } : r));
res = checkCarryover(carry, mock, ['区分名称'], J.C);
ok(st(res, 'V2171000025000248（旧12051', '1行だけ') === '反映済み', 'T9 模擬（12051行目を消し、13527行目の開始日を00000000に）：「1行だけ」は反映済み');
ok(st(res, 'V2171000025000248（旧13527', '適用開始日 00000000') === '反映済み', 'T9 模擬：適用開始日は反映済み');
ok(checkCarryover('（列） ｜ 列なし JLACセンターコメント ｜', [], ['区分名称', 'JLACセンターコメント'], J.C)[0].state === '未反映', 'T9 列がまだある前月公開版：「列なし」は未反映');
// 「有効な行がある」の反映済みの側（000コード15件・B10030000211523G3）
{
  const like = (code, end, xrow) => { const r = rows.find(x => x.code === 'V2171000024000148') || rows[0]; return { ...r, code, xrow, s: Object.assign([...r.s], { [J.C.JLAC11]: code, [J.C.END]: end, [J.C.START]: '20261015' }) }; };
  const codes000 = carry.split(/\r?\n/).filter(l => /有効な行がある ｜ 000コード/.test(l)).map(l => l.split('｜')[0].trim());
  ok(codes000.length === 15, `T9 引継ぎの000コード ${codes000.length}件が「有効な行がある」で書かれている`);
  let r0 = checkCarryover(carry, rows, ['区分名称'], J.C);
  ok(codes000.every(c => st(r0, c, '有効な行がある') === '未反映'), 'T9 10/6の提出：000コード15件は未反映（まだ提出に無い）');
  const added = rows.concat(codes000.map((c, i) => like(c, '99999999', 20000 + i)));
  r0 = checkCarryover(carry, added, ['区分名称'], J.C);
  ok(codes000.every(c => st(r0, c, '有効な行がある') === '反映済み'), 'T9 模擬（000コード15件を適用終了日99999999で足す）：15件とも反映済み');
  const b100 = rows.concat([like('B10030000211523G3', '99999999', 21000)]);
  r0 = checkCarryover(carry, b100, ['区分名称'], J.C);
  ok(st(r0, 'B10030000211523G3', '有効な行がある') === '反映済み', 'T9 模擬（旧い行8030行目〔終了20260812〕と並んで有効な行を足す）：B10030000211523G3 は反映済み');
  const ended = rows.concat(codes000.map((c, i) => like(c, '20261014', 20000 + i)));
  r0 = checkCarryover(carry, ended, ['区分名称'], J.C);
  ok(codes000.every(c => st(r0, c, '有効な行がある') === '未反映'), 'T9 隣の条件（000コードはあるが適用終了日が99999999でない）：未反映');
}

// ---- 出力名：同じ名前の最大の番号＋1（上書きしない） ----
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'jlac_name_'));
fs.writeFileSync(path.join(tmp, '20261006_JLACマスタ確認事項一覧_ACN確認用_JLACセンター20261006提出版_v25.xlsx'), '');
fs.writeFileSync(path.join(tmp, '20261006_JLACマスタ確認事項一覧_ACN確認用_JLACセンター20261006提出版_v3.xlsx'), '');
const nn = path.basename(nextName(tmp, 'JLACマスタ確認事項一覧_ACN確認用_JLACセンター20261006提出版', 'xlsx', '20261015'));
ok(nn === '20261006_JLACマスタ確認事項一覧_ACN確認用_JLACセンター20261006提出版_v26.xlsx', '出力名：既存のv25の次はv26（日付は系列の日付のまま）', nn);
const n1 = path.basename(nextName(tmp, 'JLACマスタ確認事項一覧_JLACセンター20261101提出版', 'xlsx', '20261102'));
ok(n1 === '20261102_JLACマスタ確認事項一覧_JLACセンター20261101提出版_v1.xlsx', '出力名：新しい系列はその日の日付でv1', n1);
fs.rmSync(tmp, { recursive: true, force: true });

console.log(`FAIL ${fail}`);
process.exit(fail ? 1 : 0);
