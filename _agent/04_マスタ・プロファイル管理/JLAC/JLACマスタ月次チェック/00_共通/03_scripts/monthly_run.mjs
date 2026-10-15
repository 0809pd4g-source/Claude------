// JLACマスタ月次チェックの1回実行（月次実行.ps1 から呼ぶ。直接呼んでもよい）。設計：00_共通/02_output/_wip/20261009_月次チェック1回実行化_設計案_v1.md
// 判定はチェックツールHTMLの jlac-core（run_check.mjs の runFiles）をそのまま使う。ここでは判定を書き写さない（月次の CLAUDE.md の決まり）。
//
// 使い方:
//   node monthly_run.mjs run    --month <YYYYMM提出分フォルダ> [--settings <今月の設定.txt>] [--out <出力フォルダ>] [--tool <html>] [--carryover <引継ぎ.txt>]
//       設定の点検 → ツールの実行 → 送付用・ACN確認用・報告・明細.json を出す（vN は自動で +1。上書きしない）→ 前月からの引継ぎの確認
//       設定に「止める」の問題があれば、実行せずに終了コード 2 で止まる
//   node monthly_run.mjs report --state <明細.json> [--dc <照合.json>] [--dcstatus <文>]
//       「月次実行の結果.md」を書く（ダブルチェックの照合結果があれば冒頭に）
//   node monthly_run.mjs sync   --send <送付用.xlsx> --acn <ACN確認用.xlsx>
//       送付用のコメント列とACN確認用のコメント列（見出し「JLACセンター向けコメント」）を全行比べる（読み取りだけ。Rvの反映後に使う）
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { latestTool, loadCore, codec, runFiles } from './run_check.mjs';

const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'); // 00_共通
const ROOT = path.resolve(BASE, '..'); // JLACマスタ月次チェック
const LIST11_DIR = path.resolve(ROOT, '..', '20260930_JLACマスター新旧対応表確認', '01_input');

// ---------- 今月の設定 ----------
// 判断待ちの切り替え（本田さん未決定）。既定は「今のまま」＝今の振る舞いを変えない
export const SWITCHES = {
  '判断の線引き': ['今のまま', '案'],
  '000コードの適用開始日': ['今のまま', 'その月の15日'],
  '17桁コードリストの取り直し': ['今のまま', '毎月'],
};
export const KEYS = ['対象月', '提出ファイル', '提出日', '前月公開版', 'JLAC10コード表', 'JLAC11コード表', '17桁コードリスト', '17桁コードリストの取得日',
  '公開日', '公開日が15日でない理由', '新規行の開始行', '前月の表示名', 'JLACセンターの連絡（メール本文）', '連携メモ', '連携済みの変更', 'Rv用の見解', '別シートの理由',
  '共有対象外のシート', '削除行は依頼済み', '確認したいJLAC11コード', '前月からの引継ぎ', 'ツールの版', ...Object.keys(SWITCHES)];

export function parseSettings(text) {
  const out = {}, unknown = [];
  const lines = text.replace(/^﻿/, '').split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (!l.trim() || /^\s*#/.test(l)) continue;
    const m = /^\s*([^:：]+?)\s*[:：]\s?(.*)$/.exec(l);
    if (!m) { unknown.push(`${i + 1}行目「${l.trim().slice(0, 30)}」（「キー: 値」の形でない）`); continue; }
    let [, k, v] = m;
    if (v.trim() === '<<<') { // 複数行：「キー: <<<」〜「>>>」
      const buf = [];
      const open = i + 1;
      for (i++; i < lines.length && lines[i].trim() !== '>>>'; i++) buf.push(lines[i]);
      if (i >= lines.length) unknown.push(`${open}行目の「${k}: <<<」が「>>>」で閉じられていません（ファイルの最後まで読みました）`);
      v = buf.join('\n');
    }
    if (!KEYS.includes(k)) unknown.push(`${i + 1}行目のキー「${k}」（知らないキー）`);
    out[k] = v.trim();
  }
  return { values: out, unknown };
}

const isYmd = (s) => /^20\d{6}$/.test(s) && !Number.isNaN(Date.parse(`${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6)}`));
function findFile(name, dirs) {
  if (!name) return null;
  if (path.isAbsolute(name)) return fs.existsSync(name) ? name : null;
  for (const d of dirs) { const p = path.resolve(d, name); if (fs.existsSync(p)) return p; }
  return null;
}
// 値がファイル名（.txt）で、04_reference にあれば中身を読む。無ければ値そのもの
function textOrFile(v, refDir) {
  if (!v) return '';
  if (/\.txt$/i.test(v)) { const p = findFile(v, [refDir]); return p ? fs.readFileSync(p, 'utf8').replace(/^﻿/, '') : null; }
  return v;
}

// 設定の点検。level：'止める'（実行しない）／'注意'（実行する）／'OK'
export function checkSettings(S, monthDir) {
  const v = S.values, out = [];
  const add = (level, item, msg) => out.push({ level, item, msg });
  for (const u of S.unknown) add('止める', '設定ファイルの書き方', u);
  const folderMonth = (/^(\d{6})提出分$/.exec(path.basename(monthDir)) || [])[1] || '';
  const inDir = path.join(monthDir, '01_input'), refDir = path.join(monthDir, '04_reference');
  if (!v['対象月']) add('止める', '対象月', '「対象月」がありません（YYYYMM）。前月の設定ファイルを流用していないかの確認に使います');
  else if (v['対象月'] !== folderMonth) add('止める', '対象月', `設定の対象月「${v['対象月']}」が月フォルダ「${path.basename(monthDir)}」と違います。前月の設定のままの可能性があります（前月の値は流用しない。月次の CLAUDE.md）`);
  else add('OK', '対象月', v['対象月']);
  const files = {};
  for (const [k, role, req, dirs] of [['提出ファイル', 'target', true, [inDir]], ['前月公開版', 'prev', true, [inDir]], ['JLAC10コード表', 'jlac10', true, [inDir]], ['JLAC11コード表', 'jlac11', true, [inDir]], ['17桁コードリスト', 'list11', false, [inDir, LIST11_DIR]]]) {
    if (!v[k]) { if (req) add('止める', k, `「${k}」が空です`); else add('注意', k, '空のため、KA-08（測定法）を確認しません'); continue; }
    const p = findFile(v[k], [...dirs, monthDir]);
    if (!p) add('止める', k, `ファイルが見つかりません：${v[k]}（探した場所：${dirs.map(d => path.relative(ROOT, d) || '.').join('、')}）`);
    else { files[role] = p; add('OK', k, path.relative(ROOT, p)); }
  }
  // 前月公開版の名前に前月のYYYYMMがあるか（日付8桁の一部〔20260915の202609〕は数えない。前々月のファイルの取り違えに気づくため。注意のみ）
  if (files.prev && /^\d{6}$/.test(v['対象月'] || '')) {
    const y = +v['対象月'].slice(0, 4), m = +v['対象月'].slice(4, 6), pm = m === 1 ? `${y - 1}12` : `${y}${String(m - 1).padStart(2, '0')}`;
    if (!new RegExp(`(^|[^0-9])${pm}([^0-9]|$)`).test(path.basename(files.prev))) add('注意', '前月公開版', `ファイル名に前月の「${pm}」がありません。前月に公開した版か確かめてください：${path.basename(files.prev)}`);
  }
  const sub = v['提出日'] || '';
  if (!isYmd(sub)) add('止める', '提出日', `「提出日」が8桁の日付ではありません：「${sub}」`);
  else if (v['対象月'] && sub.slice(0, 6) !== v['対象月']) add('止める', '提出日', `提出日「${sub}」が対象月「${v['対象月']}」と違います。前月の値のままの可能性があります`);
  else add('OK', '提出日', sub);
  const pub = v['公開日'] || '';
  if (!isYmd(pub)) add('止める', '公開日', `「公開日」が空、または8桁の日付ではありません：「${pub}」。空のままにするとツールはファイル名の日付から推定し、10/6再提出では9/15と誤って新規行85行を指摘しました`);
  else if (v['対象月'] && pub.slice(0, 6) !== v['対象月']) add('止める', '公開日', `公開日「${pub}」が対象月「${v['対象月']}」と違います`);
  else if (pub.slice(6) !== '15' && !v['公開日が15日でない理由']) add('止める', '公開日', `公開日「${pub}」が15日ではありません。理由を「公開日が15日でない理由」に書いてください`);
  else add('OK', '公開日', pub + (pub.slice(6) !== '15' ? `（理由：${v['公開日が15日でない理由']}）` : ''));
  const mail = v['JLACセンターの連絡（メール本文）'] || '';
  const nr = v['新規行の開始行'] || '';
  if (nr && !/^\d+$/.test(nr)) add('止める', '新規行の開始行', `数字ではありません：「${nr}」`);
  else if (!nr && /行目/.test(mail)) add('止める', '新規行の開始行', '空ですが、JLACセンターの連絡に「行目」があります。新規行の開始行が書かれていないか確かめて入れてください（入れないと旧コードの再掲載行が既存行として比べられる）');
  else if (!nr) add('注意', '新規行の開始行', '空（前月に同じJLAC11コードが無い行だけを新規行とします）');
  else add('OK', '新規行の開始行', nr);
  if (!mail) add('注意', 'JLACセンターの連絡（メール本文）', '空です（根拠の記録用。貼っておくと新規行の開始行の入れ忘れを止められます）');
  const texts = {};
  for (const k of ['連携メモ', '連携済みの変更', 'Rv用の見解', '別シートの理由', '前月からの引継ぎ']) {
    if (!v[k]) continue;
    const t = textOrFile(v[k], refDir);
    if (t === null) add('止める', k, `ファイルが見つかりません：${v[k]}（04_reference）`);
    else { texts[k] = t; if (/\.txt$/i.test(v[k])) texts[k + '_path'] = findFile(v[k], [refDir]); }
  }
  if (!v['前月からの引継ぎ']) add('注意', '前月からの引継ぎ', '空です（前月に依頼したことが反映されたかを確かめません）');
  const dr = v['削除行は依頼済み'] || 'いいえ';
  if (!['はい', 'いいえ'].includes(dr)) add('止める', '削除行は依頼済み', `「はい」か「いいえ」：「${dr}」`);
  const sw = {};
  for (const [k, vals] of Object.entries(SWITCHES)) {
    const x = v[k] || '今のまま';
    if (!vals.includes(x)) add('止める', k, `「${vals.join('」か「')}」のどれか：「${x}」`);
    sw[k] = x;
  }
  const got = v['17桁コードリストの取得日'] || '';
  if (got && !isYmd(got)) add('止める', '17桁コードリストの取得日', `8桁の日付ではありません：「${got}」`);
  if (sw['17桁コードリストの取り直し'] === '毎月') {
    const firstPrev = isYmd(sub) ? (() => { const d = new Date(Date.UTC(+sub.slice(0, 4), +sub.slice(4, 6) - 2, 1)); return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, '0')}01`; })() : '';
    if (!got) add('止める', '17桁コードリストの取得日', '「17桁コードリストの取り直し: 毎月」のため、取得日が必要です');
    else if (firstPrev && got < firstPrev) add('止める', '17桁コードリストの取得日', `取得日「${got}」が古い（${firstPrev}より前）。最新のリストを取り直してください`);
  } else if (!got && files.list11) add('注意', '17桁コードリストの取得日', '空です。古いリストだと、その月に決まったコードがKA-08で「参考」として出ます（手順書8-2）');
  if (sw['000コードの適用開始日'] !== '今のまま') add('注意', '000コードの適用開始日', `「${sw['000コードの適用開始日']}」が指定されていますが、1回実行のMVPでは000コードの候補を作っていません（設定は記録のみ）`);
  return { checks: out, files, texts, switches: sw, folderMonth };
}

// ---------- 前月からの引継ぎの確認（チェックロジック外。jlac-core の判定には入れない） ----------
// 1行1件「JLAC11コード ｜ 期待する状態 ｜ メモ」。期待する状態：含まれる／含まれない／有効な行がある（適用終了日99999999の行）／1行だけ／適用開始日 YYYYMMDD／適用終了日 YYYYMMDD／列なし 見出し名（コードの欄は「（列）」）
export function checkCarryover(text, rows, prevHeader, C) {
  const res = [];
  const d8 = (x) => (/^\d+$/.test(x) ? x.padStart(8, '0') : x);
  const at = (r) => `${r.xrow}行目（適用開始日${r.s[C.START]}・適用終了日${r.s[C.END]}）`;
  for (const [i, line] of String(text || '').split(/\r?\n/).entries()) {
    if (!line.trim() || /^\s*#/.test(line)) continue;
    const a = line.split(/[|｜]/).map(x => x.trim());
    const codeRaw = a[0] || '', want = a[1] || '', memo = a.slice(2).join('｜');
    const code = codeRaw.replace(/[（(].*?[）)]/g, '').trim();
    const hit = rows.filter(r => r.code === code);
    let state = '確認できない', detail = '';
    if (codeRaw.startsWith('（列）') || codeRaw === '(列)') {
      const m = /^列なし\s*(.+)$/.exec(want);
      if (!m) detail = `期待する状態「${want}」は列の確認では使えません（「列なし 見出し名」）`;
      else { const has = prevHeader.some(h => String(h || '').trim() === m[1].trim()); state = has ? '未反映' : '反映済み'; detail = `前月公開版の見出しに「${m[1]}」が${has ? 'ある' : '無い'}`; }
    } else if (!/^[0-9A-Z]{17}$/.test(code)) detail = `JLAC11コード「${codeRaw}」が17桁ではありません`;
    else if (want === '含まれる') { state = hit.length ? '反映済み' : '未反映'; detail = hit.length ? hit.map(at).join('、') : '今回の提出に無い'; }
    else if (want === '含まれない') { state = hit.length ? '未反映' : '反映済み'; detail = hit.length ? hit.map(at).join('、') : '今回の提出に無い'; }
    else if (want === '有効な行がある') { const ok = hit.filter(r => r.s[C.END] === '99999999'); state = ok.length ? '反映済み' : '未反映'; detail = hit.length ? hit.map(at).join('、') : '今回の提出に無い'; }
    else if (want === '1行だけ') { state = hit.length === 1 ? '反映済み' : '未反映'; detail = `今回の提出に${hit.length}行${hit.length ? '：' + hit.map(at).join('、') : ''}`; }
    else if (/^適用(開始|終了)日\s*\d{8}$/.test(want)) {
      const col = want.startsWith('適用開始日') ? C.START : C.END, val = want.replace(/\D/g, '');
      if (!hit.length) { state = '未反映'; detail = '今回の提出に無い'; }
      else { const bad = hit.filter(r => d8(r.s[col]) !== val); state = bad.length ? '未反映' : '反映済み'; detail = hit.map(at).join('、'); }
    } else detail = `期待する状態「${want}」が分かりません（含まれる／含まれない／有効な行がある／1行だけ／適用開始日 YYYYMMDD／適用終了日 YYYYMMDD／列なし 見出し名）`;
    res.push({ line: i + 1, code: codeRaw, want, memo, state, detail });
  }
  return res;
}

// ---------- 出力名（同じ名前の最大の番号＋1。上書きしない） ----------
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export function nextName(dir, stem, ext, today) {
  const re = new RegExp(`^(\\d{8})_${esc(stem)}_v(\\d+)\\.${ext}$`);
  let max = 0, date = today;
  for (const f of fs.existsSync(dir) ? fs.readdirSync(dir) : []) { const m = re.exec(f); if (m && +m[2] > max) { max = +m[2]; date = m[1]; } }
  return path.join(dir, `${date}_${stem}_v${max + 1}.${ext}`);
}
function writeNew(p, data, enc) {
  if (fs.existsSync(p)) throw new Error(`上書きしません（すでにある）：${p}`);
  fs.writeFileSync(p, data, enc);
}
const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 12);
const ymd = () => { const d = new Date(); return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`; };

// ---------- run ----------
async function cmdRun(opt) {
  if (!opt.month) throw new Error('--month <YYYYMM提出分フォルダ> を指定してください');
  const monthDir = path.resolve(opt.month.includes(path.sep) || opt.month.includes('/') ? opt.month : path.join(ROOT, opt.month));
  const settingsPath = path.resolve(opt.settings || path.join(monthDir, '04_reference', '今月の設定.txt'));
  const outDir = path.resolve(opt.out || path.join(monthDir, '02_output'));
  if (!fs.existsSync(settingsPath)) { console.error(`中止：設定ファイルがありません：${settingsPath}\n00_共通/02_output の月次実行の使い方を見て、04_reference/今月の設定.txt を作ってください`); process.exit(2); }
  const S = parseSettings(fs.readFileSync(settingsPath, 'utf8'));
  const P = checkSettings(S, monthDir);
  const v = S.values;
  if (opt.carryover) {
    const p = path.resolve(opt.carryover);
    P.texts['前月からの引継ぎ'] = fs.readFileSync(p, 'utf8'); P.texts['前月からの引継ぎ_path'] = p;
    P.checks = P.checks.filter(c => c.item !== '前月からの引継ぎ');
    P.checks.push({ level: '注意', item: '前月からの引継ぎ', msg: `コマンドの --carryover で差し替え：${p}` });
  }
  const toolPath = opt.tool ? path.resolve(opt.tool) : (v['ツールの版'] && v['ツールの版'] !== '最新' ? findFile(v['ツールの版'], [path.join(BASE, '02_output')]) : latestTool());
  if (!toolPath) P.checks.push({ level: '止める', item: 'ツールの版', msg: `ツールが見つかりません：${v['ツールの版']}` });
  const J = toolPath ? loadCore(toolPath) : null;
  // ファイルの役割（ツールの自動判定）が設定と合うか
  if (J) {
    for (const [role, p] of Object.entries(P.files)) {
      const wb = await J.openWorkbook(new Uint8Array(fs.readFileSync(p)), path.basename(p), codec);
      const g = J.guessRole(wb);
      if (g !== role) P.checks.push({ level: '止める', item: 'ファイルの役割', msg: `${path.basename(p)} はツールの判定では「${J.ROLES[g].label}」です（設定では「${J.ROLES[role].label}」）` });
    }
  }
  const stops = P.checks.filter(c => c.level === '止める');
  console.error('設定の点検：');
  for (const c of P.checks) console.error(`  [${c.level}] ${c.item}：${c.msg}`);
  if (stops.length) { console.error(`\n中止：設定に直すところが${stops.length}件あります。実行していません。`); process.exit(2); }

  const o = { quiet: true, submit: v['提出日'], start: v['公開日'] };
  if (v['新規行の開始行']) o.newrow = v['新規行の開始行'];
  if (v['前月の表示名']) o.label = v['前月の表示名'];
  if (v['共有対象外のシート']) o.exclude = v['共有対象外のシート'];
  if (v['削除行は依頼済み'] === 'はい') o.delreq = '1';
  if (v['確認したいJLAC11コード']) o.watch = v['確認したいJLAC11コード'];
  if (P.texts['連携メモ']) o.memo = P.texts['連携メモ'];
  if (P.texts['連携済みの変更']) o.shared = P.texts['連携済みの変更'];
  if (P.texts['Rv用の見解_path'] || P.texts['Rv用の見解']) o.notes = P.texts['Rv用の見解_path'] || writeTmp(P.texts['Rv用の見解']);
  if (P.texts['別シートの理由_path'] || P.texts['別シートの理由']) o.sheetreason = P.texts['別シートの理由_path'] || writeTmp(P.texts['別シートの理由']);
  if (P.switches['判断の線引き'] === '案') o.judgeLine = '案';
  const order = ['target', 'prev', 'jlac10', 'jlac11', 'list11'].filter(k => P.files[k]);
  const t0 = Date.now();
  const { R } = await runFiles(J, order.map(k => P.files[k]), o);
  const secs = Math.round((Date.now() - t0) / 1000);

  fs.mkdirSync(outDir, { recursive: true });
  const today = ymd(), tag = `JLACセンター${v['提出日']}提出版`;
  const out = {
    send: nextName(outDir, `JLACマスタ確認事項一覧_${tag}`, 'xlsx', today),
    acn: nextName(outDir, `JLACマスタ確認事項一覧_ACN確認用_${tag}`, 'xlsx', today),
    report: nextName(outDir, `JLACマスタチェック結果_${tag}`, 'md', today),
    state: nextName(outDir, `月次実行の明細_${tag}`, 'json', today),
    dc: nextName(outDir, `JLACマスタ確認結果ダブルチェック_${tag}`, 'xlsx', today),
    summary: nextName(outDir, `月次実行の結果_${tag}`, 'md', today),
  };
  writeNew(out.send, await J.buildOutput(R, codec));
  writeNew(out.acn, await J.buildOutput(R, codec, { internal: true }));
  writeNew(out.report, J.reportMarkdown(R), 'utf8');

  // 前月からの引継ぎ
  let carry = null;
  if (P.texts['前月からの引継ぎ']) {
    const head = ((await R.inp.prev.rawRows(R.settings.baseSheet)).find(x => x.r === 1) || { vals: [] }).vals;
    carry = checkCarryover(P.texts['前月からの引継ぎ'], R.newRows, head, J.C);
  }
  const comments = {};
  for (const [k, val] of R.comments) comments[k.replace('\u0000', '!')] = J.commentText(val);
  const noteCols = Object.values(R.noteHdr || {})[0];
  const state = {
    createdAt: new Date().toISOString(), month: path.basename(monthDir), monthDir, settingsPath, settingsSha: sha(settingsPath),
    tool: { path: toolPath, version: J.VERSION, sha: sha(toolPath) }, seconds: secs,
    files: Object.fromEntries(order.map(k => [k, P.files[k]])), fileSha: Object.fromEntries(order.map(k => [k, sha(P.files[k])])),
    label: `JLACセンター ${v['提出日'].slice(0, 4)}-${v['提出日'].slice(4, 6)}-${v['提出日'].slice(6)}提出版`, noteCol: noteCols ? noteCols[0][0] : null,
    checks: P.checks, switches: P.switches, values: Object.fromEntries(Object.entries(v).filter(([k]) => k !== 'JLACセンターの連絡（メール本文）')),
    outputs: out, carryover: carry,
    version: R.version, settings: { ...R.settings }, notices: R.notices, findings: R.findings, comments,
    commentRows: R.commentRows, newCodes: R.newCodes.length,
  };
  writeNew(out.state, JSON.stringify(state, null, 1), 'utf8');
  console.error(`ツール ${J.VERSION}：コメント ${R.commentRows}行、新規行 ${R.newCodes.length}行、通知 ${R.notices.length}件（${secs}秒）`);
  for (const [k, p] of Object.entries(out)) if (fs.existsSync(p)) console.error(`  出力：${path.basename(p)}`);
  console.log('RESULT ' + JSON.stringify({ state: out.state, acn: out.acn, send: out.send, dc: out.dc, summary: out.summary, csvPrev: /\.csv$/i.test(P.files.prev) }));
}
function writeTmp(text) {
  const p = path.join(process.env.TEMP || process.env.TMP || '.', `jlac_monthly_${process.pid}_${Math.random().toString(36).slice(2)}.txt`);
  fs.writeFileSync(p, text, 'utf8');
  return p;
}

// ---------- report ----------
const mdc = (s) => String(s ?? '').replace(/\|/g, '｜').replace(/\r?\n/g, ' ');
function cmdReport(opt) {
  const st = JSON.parse(fs.readFileSync(opt.state, 'utf8'));
  const dc = opt.dc && fs.existsSync(opt.dc) ? JSON.parse(fs.readFileSync(opt.dc, 'utf8')) : null;
  const dcStatus = opt.dcstatus || (dc ? '' : 'ダブルチェックは作っていない');
  const L = [], o = st.outputs, b = (p) => path.basename(p);
  const s = st.settings, today = ymd();
  L.push(`# 月次実行の結果（${st.label}）`, '');
  L.push(`> 作成日: ${today.slice(0, 4)}-${today.slice(4, 6)}-${today.slice(6)}（monthly_run.mjs・チェックツール ${st.tool.version}）`);
  L.push(`> 月フォルダ: ${st.month}`, '');
  const mis = dc && dc.status === '計算済み' ? dc.mismatch.length : null;
  // 比べられる項目が減ったら、何を測らなくなったかを見落とさないよう冒頭に出す（2026-10-08の10月分は54項目）
  if (dc && dc.status === '計算済み' && dc.comparable < 54) L.push(`> ⚠️ **ダブルチェックの比較できる項目が${dc.comparable}件で、10月分（54件）より少なくなっています**。どの項目が「—」（比較できない）になったかを照合シートで確かめてください。`, '');
  if (!dc || dc.status !== '計算済み') {
    L.push(`> ⚠️ **ダブルチェックの照合が済んでいません**（${dcStatus || (dc ? dc.status : '')}）。照合が済むまで、指摘の説明文（Rv用の見解・関係者への説明）は確定しないでください。`, '');
  } else if (mis > 0 || dc.rowMismatch.some(x => x.count > 0)) {
    L.push(`> ⚠️ **ダブルチェックで不一致が${mis}項目あります**${dc.rowMismatch.some(x => x.count > 0) ? '（行ごとの不一致もあり）' : ''}。検算式とツールのどちらが正しいかを原因まで調べてから、説明文を確定してください。`, '');
  } else L.push(`> ✅ ダブルチェック：比較できる${dc.comparable}項目すべて一致（行ごとの不一致 0）。`, '');
  L.push('## 1. 使ったファイル・設定・ツール', '', '| 区分 | ファイル | 指紋（SHA-256先頭12桁） |', '|---|---|---|');
  const lab = { target: '今回の提出', prev: '前月公開版', jlac10: 'JLAC10コード表', jlac11: 'JLAC11コード表', list11: '17桁コードリスト' };
  for (const [k, p] of Object.entries(st.files)) L.push(`| ${lab[k]} | ${mdc(b(p))} | ${st.fileSha[k]} |`);
  L.push(`| 今月の設定 | ${mdc(path.relative(st.monthDir, st.settingsPath))} | ${st.settingsSha} |`, `| チェックツール | ${mdc(b(st.tool.path))}（${st.tool.version}） | ${st.tool.sha} |`, '');
  L.push(`- 提出日 ${s.submitDate}／公開日 ${s.expectedStart}（切替日前日 ${s.expectedEnd}）／新規行の開始行 ${s.newFromRow || 'なし'}／前月の表示 ${s.prevLabel}／対象シート ${s.targetSheets.join('、')}`);
  L.push(`- 判断待ちの切り替え（本田さん未決定。既定は今のまま）：${Object.entries(st.switches).map(([k, x]) => `${k}＝${x}`).join('／')}`, '');
  L.push('## 2. 設定の点検', '');
  for (const c of st.checks) L.push(`- [${c.level}] ${c.item}：${c.msg}`);
  L.push('', '## 3. 結果の概要', '');
  L.push(`- コメントを付けた行：**${st.commentRows}行**／新規行：${st.newCodes}行／実行時間：${st.seconds}秒`);
  L.push(`- 要確認の通知：${st.notices.filter(n => n.level === '要確認').length}件`);
  for (const n of st.notices.filter(n => n.level === '要確認')) L.push(`  - ${mdc(n.title)}`);
  L.push('', '## 4. ダブルチェックの結果', '');
  if (!dc) L.push(`- ${dcStatus}`);
  else {
    L.push(`- ファイル：${b(dc.file)}／状態：${dc.status}${dc.seconds != null ? `（Excelでの計算 ${dc.seconds}秒）` : ''}`);
    if (dc.status === '計算済み') {
      L.push(`- 照合の項目 ${dc.total}件：一致 ${dc.match}・不一致 ${dc.mismatch.length}・比較できない（—）${dc.dash}（比較できる項目 ${dc.comparable}。10/8の10月分は54項目。減っていたら何を測らなくなったか確かめる）`);
      L.push(`- 使った設定（照合シートの先頭）：${mdc(dc.title)}`);
      if (dc.mismatch.length) { L.push('', '| 区分 | 項目 | Excel | ツール |', '|---|---|---:|---:|'); for (const m of dc.mismatch) L.push(`| ${mdc(m.kind)} | ${mdc(m.item)} | ${m.excel} | ${m.tool} |`); }
      for (const x of dc.rowMismatch) if (x.count) L.push(`- 行ごとの不一致「${x.title}」${x.count}行：${x.rows.map(r => `${r.row}行目（${r.code || '空欄'}）`).join('、')}${x.count > x.rows.length ? ' ほか' : ''}`);
    }
  }
  L.push('', '## 5. 前月からの引継ぎの確認', '');
  if (!st.carryover) L.push('- 引継ぎファイルの指定なし（確認していない）');
  else {
    const cnt = (x) => st.carryover.filter(c => c.state === x).length;
    L.push(`- 反映済み ${cnt('反映済み')}件・**未反映 ${cnt('未反映')}件**・確認できない ${cnt('確認できない')}件。未反映は一次Rvの候補に「残指摘〔前月の依頼から〕」として足す（MVPでは手で足す）`, '', '| JLAC11コード | 期待する状態 | 結果 | 今回の提出 | メモ |', '|---|---|---|---|---|');
    for (const c of st.carryover) L.push(`| ${mdc(c.code)} | ${mdc(c.want)} | ${c.state === '未反映' ? '**未反映**' : c.state} | ${mdc(c.detail)} | ${mdc(c.memo)} |`);
  }
  L.push('', '## 6. 指摘の根拠の要約（全件はACN確認用の「指摘の根拠」シート）', '');
  const tgt = st.findings.filter(f => f.level === 'strict' && !f.known);
  const by = new Map();
  for (const f of tgt) { if (!by.has(f.check)) by.set(f.check, []); by.get(f.check).push(f); }
  L.push('| チェック | 件数 | 新規行 | 既存行（前月は該当なし） | 既存行（前月も該当・文面が違う） | その他 | 説明文の下書き（代表1件） |', '|---|---:|---:|---:|---:|---:|---|');
  for (const [cid, fs_] of [...by.entries()].sort((a, c) => c[1].length - a[1].length)) {
    const n = (p) => fs_.filter(p).length;
    const nn = n(f => f.status === '新規行'), a = n(f => f.status !== '新規行' && f.basis && f.basis.prevSame === '該当なし'), c = n(f => f.status !== '新規行' && f.basis && f.basis.prevSame === '該当（文面が違う）');
    const rep = fs_.find(f => f.basis && f.basis.prevSame === '該当（文面が違う）') || fs_.find(f => f.basis && f.basis.draft);
    L.push(`| ${cid} | ${fs_.length} | ${nn} | ${a} | ${c} | ${fs_.length - nn - a - c} | ${rep ? mdc(`${rep.row}行目：${rep.basis.draft}`) : ''} |`);
  }
  L.push('', '- 説明文の下書きは判定の材料から決まった型で作った文。**ダブルチェックの照合が済んでから**使う（2026-10-06のKA-08の説明の誤りの再発防止）', '');
  L.push('## 7. 出したファイルと、送付前に人がすること', '');
  for (const [k, lab2] of [['send', '送付用'], ['acn', 'ACN確認用'], ['report', 'チェック結果報告'], ['state', '明細（根拠を含む）'], ['dc', 'ダブルチェック']]) if (fs.existsSync(o[k])) L.push(`- ${lab2}：${b(o[k])}`);
  L.push('', '1. この結果のダブルチェックに不一致があれば、原因を調べる（説明文はその後）',
    '2. ACN確認用の「送付前確認事項_一次Rv」を整える（候補・説明文の下書きの代表1件が入っている。前月からの引継ぎの未反映は手で足す）',
    '3. 本田さんにRvを依頼する（見てほしいシート・見なくてよいシートを書く）',
    '4. Rvを反映したら、送付用とACN確認用のコメントのずれを確かめる：`node 00_共通/03_scripts/monthly_run.mjs sync --send <送付用> --acn <ACN確認用>`',
    '5. `python _agent/_基盤/_ツール/送付前チェック.py <送付用> --clean` で送付用を作って送る（PowerPoint・Word・Excelを閉じてから）', '');
  L.push('## やったこと・やっていないこと', '');
  L.push(`- やったこと：設定の点検、チェックツール ${st.tool.version} での判定（送付用・ACN確認用・報告・明細）、${dc && dc.status === '計算済み' ? 'ダブルチェック（Excelで計算・照合）、' : ''}${st.carryover ? '前月からの引継ぎの確認、' : ''}この結果のまとめ。`);
  L.push(`- やっていないこと：${!dc || dc.status !== '計算済み' ? 'ダブルチェックの照合（上の理由）、' : ''}000（その他の測定法）コードの候補づくり（MVPの範囲外）、送付前確認事項の整理・本田さんRv・送付。`);
  writeNew(o.summary, L.join('\n') + '\n', 'utf8');
  console.error('  出力：' + b(o.summary));
  console.log('SUMMARY ' + o.summary);
}

// ---------- sync ----------
async function cmdSync(opt) {
  const J = loadCore(opt.tool ? path.resolve(opt.tool) : latestTool());
  const col = async (p) => {
    const wb = await J.openWorkbook(new Uint8Array(fs.readFileSync(p)), path.basename(p), codec);
    const sh = wb.sheets.find(x => x.name === 'JLACセンター向けコメント_確認用');
    if (!sh) throw new Error(`「JLACセンター向けコメント_確認用」シートがありません：${p}`);
    const raw = await wb.rawRows(sh.name), h = (raw.find(x => x.r === 1) || { vals: [] }).vals;
    const ci = h.findIndex(x => String(x ?? '').trim() === 'JLACセンター向けコメント');
    if (ci < 0) throw new Error(`見出し「JLACセンター向けコメント」の列がありません：${p}`);
    const m = new Map();
    for (const x of raw) if (x.r > 1) m.set(x.r, [String(x.vals[ci] ?? '').trim(), String(x.vals[12] ?? '').trim()]);
    return { m, letter: ci };
  };
  const a = await col(path.resolve(opt.send)), c = await col(path.resolve(opt.acn));
  const rows = [...new Set([...a.m.keys(), ...c.m.keys()])].sort((x, y) => x - y), diff = [];
  for (const r of rows) { const x = (a.m.get(r) || [''])[0], y = (c.m.get(r) || [''])[0]; if (x !== y) diff.push([r, (a.m.get(r) || c.m.get(r))[1], x, y]); }
  console.log(`送付用とACN確認用のコメント（見出し「JLACセンター向けコメント」）：${rows.length}行を比べ、違う行 ${diff.length}行`);
  for (const [r, code, x, y] of diff.slice(0, 50)) console.log(`  ${r}行目（${code}）\n    送付用：${x.slice(0, 120)}\n    ACN  ：${y.slice(0, 120)}`);
  process.exit(diff.length ? 1 : 0);
}

async function main() {
  const [cmd, ...args] = process.argv.slice(2), opt = {};
  for (let i = 0; i < args.length; i++) if (args[i].startsWith('--')) opt[args[i].slice(2)] = args[++i];
  if (cmd === 'run') return cmdRun(opt);
  if (cmd === 'report') return cmdReport(opt);
  if (cmd === 'sync') return cmdSync(opt);
  console.error('使い方: node monthly_run.mjs run|report|sync …（ファイル冒頭の説明を参照）');
  process.exit(1);
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(e => { console.error(e.stack || e.message); process.exit(1); });
}
