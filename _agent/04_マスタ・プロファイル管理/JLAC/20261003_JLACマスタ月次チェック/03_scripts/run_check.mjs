// チェックツールHTML内のロジック（<script id="jlac-core">）をNode.jsで実行する。ブラウザ版と同じコードで同じ結果を出す。
// 使い方: node 03_scripts/run_check.mjs [--tool <html>] [--xlsx <送付用>] [--internal <ACN確認用>] [--md <報告>] [--json <明細>] [--start YYYYMMDD] [--label 202609版] [--newrow 8367] <入力xlsx...>
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const BASE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function latestTool() {
  const dir = path.join(BASE, '02_output');
  const vs = fs.readdirSync(dir).map(f => [f, /_JLACマスタチェックツール_v(\d+)\.html$/.exec(f)]).filter(x => x[1]);
  if (!vs.length) throw new Error('02_output にチェックツールHTMLがありません');
  vs.sort((a, b) => +a[1][1] - +b[1][1]);
  return path.join(dir, vs[vs.length - 1][0]);
}

export function loadCore(toolPath) {
  const html = fs.readFileSync(toolPath, 'utf8');
  const m = /<script id="jlac-core">([\s\S]*?)<\/script>/.exec(html);
  if (!m) throw new Error('jlac-core が見つかりません: ' + toolPath);
  const ctx = vm.createContext({ TextDecoder, TextEncoder });
  vm.runInContext(m[1], ctx, { filename: path.basename(toolPath) });
  return ctx.JLAC;
}

export const codec = {
  inflateRaw: async (u8) => new Uint8Array(zlib.inflateRawSync(u8)),
  deflateRaw: async (u8) => new Uint8Array(zlib.deflateRawSync(u8, { level: 6 })),
};

export async function runFiles(J, files, opt = {}) {
  const wbs = [];
  for (const f of files) {
    const wb = await J.openWorkbook(new Uint8Array(fs.readFileSync(f)), path.basename(f), codec);
    wbs.push({ wb, role: J.guessRole(wb) });
  }
  const pick = (role) => {
    const g = wbs.filter(x => x.role === role);
    if (g.length > 1) throw new Error(`役割「${role}」のファイルが複数あります: ${g.map(x => x.wb.fileName).join(', ')}`);
    return g.length ? g[0].wb : null;
  };
  const inp = { target: pick('target'), prev: pick('prev'), jlac10: pick('jlac10'), jlac11: pick('jlac11'), list11: pick('list11') };
  for (const k of ['target', 'prev', 'jlac10', 'jlac11']) if (!inp[k]) throw new Error(`必須ファイルがありません: ${J.ROLES[k].label}`);
  const st = await J.defaultSettings(inp);
  if (opt.start) { st.expectedStart = opt.start; st.expectedEnd = J.addDays(opt.start, -1); }
  if (opt.label) st.prevLabel = opt.label;
  if (opt.newrow) st.newFromRow = opt.newrow;
  const R = await J.run(inp, st, opt.quiet ? null : async (m) => process.stderr.write(m + '\n'));
  return { R, roles: wbs.map(x => [x.wb.fileName, x.role]) };
}

async function main() {
  const args = process.argv.slice(2), opt = {}, files = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a.startsWith('--')) opt[a.slice(2)] = args[++i];
    else files.push(a);
  }
  const tool = opt.tool || latestTool();
  const J = loadCore(tool);
  process.stderr.write(`ツール: ${path.basename(tool)}（${J.VERSION}）\n`);
  const { R, roles } = await runFiles(J, files, opt);
  for (const [f, r] of roles) process.stderr.write(`  ${J.ROLES[r].label}: ${f}\n`);
  if (opt.xlsx) fs.writeFileSync(opt.xlsx, await J.buildOutput(R, codec));
  if (opt.internal) fs.writeFileSync(opt.internal, await J.buildOutput(R, codec, { internal: true }));
  if (opt.md) fs.writeFileSync(opt.md, J.reportMarkdown(R), 'utf8');
  if (opt.json) {
    const comments = {};
    for (const [k, v] of R.comments) comments[k.replace('\u0000', '!')] = J.commentText(v);
    fs.writeFileSync(opt.json, JSON.stringify({ version: R.version, settings: { ...R.settings }, notices: R.notices, findings: R.findings, comments }, null, 1), 'utf8');
  }
  console.log(JSON.stringify({ commentRows: R.commentRows, newCodes: R.newCodes.length, notices: R.notices.map(n => `【${n.level}】${n.title}`), breakdown: R.breakdown.map(b => [b.status, b.check, b.rows.size]) }, null, 1));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(e => { console.error(e.stack || e.message); process.exit(1); });
}
