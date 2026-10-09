"""
案件台帳Excel → 案件台帳.html 生成スクリプト
出力: 02_成果物/20260728_案件台帳_vN.html
"""
import sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import openpyxl

_BASE = Path(__file__).resolve().parent.parent  # プロジェクトフォルダ（移動しても動くようスクリプト位置から求める）
EXCEL_PATH = _BASE / "01_input" / "(原本)【電カル共有】案件台帳_令和8年度_20261009受領.xlsx"
OUT_DIR = _BASE / "02_output"
OUT_NAME = "20260728_案件台帳_v3.html"

# ──────────────────────────────────────────
# 追記: 2026-07-27 会議エントリー
# ──────────────────────────────────────────
EXTRA_ENTRIES = {
    "036": {
        "date": "2026-07-27",
        "title": "開発進捗連絡会議／開発課題検討会 - 介護連携IF方式決定",
        "body": "JAHISアンケート（6社）結果報告。6社から方式採用を妨げる実装懸念なし（NEC・富士通Japanは個別回答予定）。医療機関向けIFと介護事業所向けIFを完全分離するAPI分離方式（案②）を正式決定。保守性・可用性・拡張性で優位と評価。別途、7/23に厚労省渋谷様より「PMHキーが利用できない見込み」との情報共有あり。Todo#1124（基金中間サーバーチームに特定個人情報保護評価書の変更前提事項を確認）、Todo#1125（デジタル庁との調整の要否を確認）を起票。",
    },
    "158": {
        "date": "2026-07-27",
        "title": "開発課題検討会 - DVフラグ設定時の登録方針確認",
        "body": "自己情報提供不可フラグ設定時の臨床情報・患者サマリーの登録方針を確認・整理。臨床情報：自己情報提供不可フラグ設定時も登録許容（現仕様から変更なし）。患者サマリー：自己情報提供不可フラグ設定時は登録不可とするシステム制御追加が望ましい。患者サマリーの閲覧可能期間は過去180日のため、フラグ解除前に閲覧期間が終了するケースも想定。診療報酬（生活習慣病管理料の算定要件）との関係も要確認。",
    },
    "162": {
        "date": "2026-07-27",
        "title": "開発課題検討会 - 不開示フラグ対応方針再確認",
        "body": "不開示該当フラグ設定患者への対応方針を再確認。不開示該当フラグ設定患者の文書は医療機関が取得不可とする運用・仕様方針を確認（20251217開発課題検討会の整理を再掲）。",
    },
    "201": {
        "date": "2026-07-27",
        "title": "開発課題検討会（厚労省付議） - 43+5項目 Component対応方針決定",
        "body": "Observation.component要素に記述された43+5項目がベースチェックされない問題の対応方針を確定。方針：アドオンチェック採用（7/21基金‐厚労間合意済み）。ベースチェックは最速でR9年度12月リリースのため採用せず。実装：Observation.component要素に記述された検査結果はオン資へ抽出しない。誤登録時はエラーで返却。マイルストン：2027年1月～3月 案1/案2リリース目標。",
    },
    "203": {
        "date": "2026-07-27",
        "title": "開発課題検討会（厚労省付議） - Component記述時の登録エラー返却方針確認",
        "body": "案件201と連動。Componentに記述された43+5項目のデータ登録時にエラーで返却する方針を確認（7/21開発課題検討会で基金‐厚労間合意済み）。アドオンチェック方式で実装する。",
    },
}

# ──────────────────────────────────────────
# Excel 読み取り
# ──────────────────────────────────────────
def get_status(jisso):
    if not jisso:
        return "active"
    s = str(jisso).strip()
    if s == "取り下げ":
        return "done"
    if s == "検討中":
        return "hold"
    return "active"

def fmt_date(v):
    if v is None:
        return ""
    s = str(v)
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s[:10]

def parse_history(text):
    """更新履歴テキスト → [{date, title, body}]"""
    if not text:
        return []
    text = str(text).strip()
    parts = re.split(r"(\d{4}/\d{1,2}/\d{1,2})", text)
    entries = []
    i = 1
    while i < len(parts):
        raw_date = parts[i]
        body_raw = parts[i + 1].strip() if i + 1 < len(parts) else ""
        # parse date
        m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", raw_date)
        date_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else raw_date
        # first line → title, rest → body
        lines = [l.strip() for l in body_raw.split("\n") if l.strip()]
        title = lines[0][:80] if lines else "(記録)"
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""
        entries.append({"date": date_str, "title": title, "body": body})
        i += 2
    return entries

wb = openpyxl.load_workbook(str(EXCEL_PATH), read_only=True, data_only=True)
ws = wb["案件台帳"]

cases_raw = {}  # id -> first_row data
cases_issues = {}  # id -> [issue_texts]

for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i < 3:
        continue  # skip header rows
    vals = list(row)
    def c(n): return vals[n - 1] if len(vals) >= n else None

    case_id = c(2)
    if not case_id:
        continue
    case_id = str(case_id).strip().zfill(3)

    row_id = str(c(3) or "").strip()
    is_first = row_id.endswith("_01") or row_id == case_id

    if is_first or case_id not in cases_raw:
        cases_raw[case_id] = {
            "id": case_id,
            "name": str(c(5) or "").strip(),
            "kubun": str(c(4) or "").strip(),
            "owner": str(c(9) or "").strip(),
            "start": fmt_date(c(11)),
            "target": str(c(19) or "").strip(),
            "jisso": c(20),
            "summary": str(c(12) or "").strip(),
            "history_raw": str(c(6) or "").strip(),
            "updated_raw": fmt_date(c(30)),
        }
        cases_issues[case_id] = []

    req = str(c(26) or "").strip()
    if req:
        cases_issues[case_id].append(req)

wb.close()

# ──────────────────────────────────────────
# cases 配列を構築
# ──────────────────────────────────────────
cases = []
for case_id, raw in sorted(cases_raw.items()):
    status = get_status(raw["jisso"])
    timeline = parse_history(raw["history_raw"])
    # prepend extra entries (newest first)
    if case_id in EXTRA_ENTRIES:
        e = EXTRA_ENTRIES[case_id]
        timeline.insert(0, {"date": e["date"], "title": e["title"], "body": e["body"]})
    # deduplicate issues
    issues = list(dict.fromkeys(cases_issues.get(case_id, [])))
    updated = raw["updated_raw"] or (timeline[0]["date"] if timeline else "")
    cases.append({
        "id": case_id,
        "name": raw["name"],
        "kubun": raw["kubun"],
        "status": status,
        "owner": raw["owner"],
        "start": raw["start"],
        "target": raw["target"],
        "updated": updated,
        "summary": raw["summary"],
        "timeline": timeline,
        "issues": issues,
        "actions": [],
    })

cnt_a = sum(1 for c in cases if c["status"] == "active")
cnt_h = sum(1 for c in cases if c["status"] == "hold")
cnt_d = sum(1 for c in cases if c["status"] == "done")
print(f"案件数: {len(cases)} (対応中:{cnt_a} 検討中:{cnt_h} 取り下げ:{cnt_d})")

# ──────────────────────────────────────────
# JSON → JavaScript に変換
# ──────────────────────────────────────────
cases_js = json.dumps(cases, ensure_ascii=False, indent=2)

# ──────────────────────────────────────────
# HTML テンプレート
# ──────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>電カル共有 案件台帳</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Hiragino Sans','Meiryo',sans-serif;font-size:13px;background:#f0f2f5;color:#222}
/* ── header ── */
.hdr{background:#1a3a5c;color:#fff;padding:12px 20px;display:flex;align-items:center;gap:16px}
.hdr h1{font-size:16px;font-weight:700;letter-spacing:.05em}
.hdr-stats{display:flex;gap:8px;margin-left:auto;font-size:12px}
.hdr-stat{background:rgba(255,255,255,.15);padding:3px 10px;border-radius:12px}
.hdr-stat span{font-weight:700;margin-right:3px}
/* ── filter bar ── */
.filter-bar{background:#fff;padding:10px 20px;display:flex;align-items:center;gap:8px;border-bottom:1px solid #ddd;flex-wrap:wrap}
.filter-bar input{border:1px solid #ccc;border-radius:6px;padding:5px 10px;font-size:12px;width:220px}
.fbtn{border:1px solid #bbb;background:#fff;border-radius:16px;padding:4px 14px;font-size:12px;cursor:pointer;transition:all .15s}
.fbtn.active,.fbtn:hover{background:#1a3a5c;color:#fff;border-color:#1a3a5c}
/* ── table ── */
.tbl-wrap{padding:16px 20px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}
th{background:#1a3a5c;color:#fff;padding:9px 12px;text-align:left;font-size:12px;cursor:pointer;white-space:nowrap;user-select:none}
th:hover{background:#245080}
td{padding:8px 12px;border-bottom:1px solid #eee;font-size:12px;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f5f8ff;cursor:pointer}
/* badges */
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600}
.badge-active{background:#dbeafe;color:#1d4ed8}
.badge-hold{background:#fef9c3;color:#854d0e}
.badge-done{background:#f1f5f9;color:#64748b}
/* ── detail view ── */
#detail{display:none;padding:16px 20px}
.d-header{display:flex;align-items:flex-start;gap:12px;margin-bottom:14px}
.d-back{background:none;border:none;color:#1a3a5c;cursor:pointer;font-size:13px;padding:4px 0;display:flex;align-items:center;gap:4px}
.d-back:hover{text-decoration:underline}
.d-title{font-size:17px;font-weight:700;line-height:1.4}
.d-id{font-size:12px;color:#888;margin-top:2px}
.meta-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin-bottom:14px}
.meta-item{background:#fff;border-radius:6px;padding:8px 12px;border:1px solid #e5e7eb}
.meta-label{font-size:10px;color:#888;margin-bottom:2px}
.meta-value{font-size:12px;font-weight:600}
/* sections */
.sec{background:#fff;border-radius:8px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.sec-hdr{padding:10px 14px;font-weight:700;font-size:13px;border-bottom:1px solid #eee;cursor:pointer;display:flex;align-items:center;gap:6px}
.sec-hdr::before{content:'▾';transition:transform .2s}
.sec-hdr.collapsed::before{transform:rotate(-90deg)}
.sec-body{padding:12px 14px}
.sec-body.hidden{display:none}
/* summary */
.summary-text{line-height:1.7;white-space:pre-wrap;color:#333}
/* timeline */
.tl-item{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f0f0f0}
.tl-item:last-child{border-bottom:none}
.tl-date{width:90px;flex-shrink:0;font-size:11px;color:#888;padding-top:1px}
.tl-content{}
.tl-title{font-size:12px;font-weight:600;color:#1a3a5c;margin-bottom:3px}
.tl-body{font-size:12px;color:#444;white-space:pre-wrap;line-height:1.6}
/* issues */
.issue-item{padding:5px 0;border-bottom:1px solid #f0f0f0;display:flex;gap:8px;align-items:flex-start;font-size:12px}
.issue-item:last-child{border-bottom:none}
.issue-item::before{content:'•';color:#94a3b8;flex-shrink:0;margin-top:1px}
/* actions */
.action-item{display:flex;align-items:flex-start;gap:8px;padding:5px 0;border-bottom:1px solid #f0f0f0;font-size:12px}
.action-item:last-child{border-bottom:none}
.action-item input[type=checkbox]{margin-top:1px;flex-shrink:0}
.action-item.done-item label{text-decoration:line-through;color:#aaa}
.empty-msg{color:#aaa;font-size:12px;font-style:italic}
/* sort arrows */
.sort-asc::after{content:' ↑'}
.sort-desc::after{content:' ↓'}
</style>
</head>
<body>

<div class="hdr">
  <h1>電カル共有 案件台帳</h1>
  <div class="hdr-stats">
    <div class="hdr-stat"><span id="cnt-total">0</span>件</div>
    <div class="hdr-stat" style="background:rgba(219,234,254,.3)"><span id="cnt-active" style="color:#93c5fd">0</span> 対応中</div>
    <div class="hdr-stat" style="background:rgba(254,249,195,.2)"><span id="cnt-hold" style="color:#fde047">0</span> 検討中</div>
    <div class="hdr-stat" style="background:rgba(241,245,249,.2)"><span id="cnt-done" style="color:#cbd5e1">0</span> 取り下げ</div>
  </div>
</div>

<!-- list view -->
<div id="list-view">
  <div class="filter-bar">
    <input id="search" placeholder="案件名・担当者・概要で絞り込み..." oninput="applyFilters()">
    <button class="fbtn active" onclick="setFilter('all',this)">すべて</button>
    <button class="fbtn" onclick="setFilter('active',this)">対応中</button>
    <button class="fbtn" onclick="setFilter('hold',this)">検討中</button>
    <button class="fbtn" onclick="setFilter('done',this)">取り下げ</button>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th onclick="sortBy('id')" data-col="id">案件ID</th>
          <th onclick="sortBy('name')" data-col="name">案件名称</th>
          <th onclick="sortBy('kubun')" data-col="kubun">案件区分</th>
          <th onclick="sortBy('status')" data-col="status">ステータス</th>
          <th onclick="sortBy('owner')" data-col="owner">担当者</th>
          <th onclick="sortBy('target')" data-col="target">リリース希望</th>
          <th onclick="sortBy('updated')" data-col="updated">最終更新</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</div>

<!-- detail view -->
<div id="detail">
  <div class="d-header">
    <button class="d-back" onclick="showList()">← 一覧に戻る</button>
  </div>
  <div id="d-meta"></div>
  <div id="d-sections"></div>
</div>

<script>
const SL = {active:"対応中",done:"取り下げ",hold:"検討中"};
const SC = {active:"badge-active",done:"badge-done",hold:"badge-hold"};
const cases = __CASES_JSON__;

let curFilter = 'all', curSort = {col:'id', dir:'asc'}, curSearch = '';

function initStats(){
  document.getElementById('cnt-total').textContent = cases.length;
  document.getElementById('cnt-active').textContent = cases.filter(c=>c.status==='active').length;
  document.getElementById('cnt-hold').textContent = cases.filter(c=>c.status==='hold').length;
  document.getElementById('cnt-done').textContent = cases.filter(c=>c.status==='done').length;
}

function setFilter(f, btn){
  curFilter = f;
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}

function applyFilters(){
  curSearch = document.getElementById('search').value.toLowerCase();
  renderTable();
}

function sortBy(col){
  if(curSort.col===col) curSort.dir = curSort.dir==='asc'?'desc':'asc';
  else { curSort.col=col; curSort.dir='asc'; }
  document.querySelectorAll('th').forEach(th=>{
    th.classList.remove('sort-asc','sort-desc');
    if(th.dataset.col===col) th.classList.add(curSort.dir==='asc'?'sort-asc':'sort-desc');
  });
  renderTable();
}

function renderTable(){
  let rows = cases.filter(c=>{
    if(curFilter!=='all' && c.status!==curFilter) return false;
    if(curSearch){
      const q = curSearch;
      return (c.name||'').toLowerCase().includes(q) ||
             (c.owner||'').toLowerCase().includes(q) ||
             (c.summary||'').toLowerCase().includes(q) ||
             (c.id||'').toLowerCase().includes(q);
    }
    return true;
  });
  const {col,dir} = curSort;
  rows.sort((a,b)=>{
    const av = (a[col]||'').toLowerCase(), bv = (b[col]||'').toLowerCase();
    return dir==='asc'?(av<bv?-1:av>bv?1:0):(av<bv?1:av>bv?-1:0);
  });
  const tb = document.getElementById('tbody');
  tb.innerHTML = rows.map(c=>`
    <tr onclick="showDetail('${c.id}')">
      <td>${c.id}</td>
      <td>${esc(c.name)}</td>
      <td>${esc(c.kubun)}</td>
      <td><span class="badge ${SC[c.status]}">${SL[c.status]}</span></td>
      <td>${esc(c.owner)}</td>
      <td>${esc(c.target)}</td>
      <td>${esc(c.updated)}</td>
    </tr>`).join('');
}

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

function showDetail(id){
  const c = cases.find(x=>x.id===id);
  if(!c) return;
  document.getElementById('list-view').style.display='none';
  document.getElementById('detail').style.display='block';

  document.getElementById('d-meta').innerHTML = `
    <div class="d-header" style="gap:8px;margin-bottom:10px">
      <div>
        <div class="d-title">${esc(c.name)}</div>
        <div class="d-id">案件ID: ${c.id}　<span class="badge ${SC[c.status]}">${SL[c.status]}</span></div>
      </div>
    </div>
    <div class="meta-grid">
      <div class="meta-item"><div class="meta-label">担当者</div><div class="meta-value">${esc(c.owner)||'―'}</div></div>
      <div class="meta-item"><div class="meta-label">案件区分</div><div class="meta-value">${esc(c.kubun)||'―'}</div></div>
      <div class="meta-item"><div class="meta-label">起票日</div><div class="meta-value">${esc(c.start)||'―'}</div></div>
      <div class="meta-item"><div class="meta-label">リリース希望</div><div class="meta-value">${esc(c.target)||'―'}</div></div>
      <div class="meta-item"><div class="meta-label">最終更新</div><div class="meta-value">${esc(c.updated)||'―'}</div></div>
    </div>`;

  const tl = (c.timeline||[]).map(t=>`
    <div class="tl-item">
      <div class="tl-date">${esc(t.date)}</div>
      <div class="tl-content">
        <div class="tl-title">${esc(t.title)}</div>
        ${t.body?`<div class="tl-body">${esc(t.body)}</div>`:''}
      </div>
    </div>`).join('') || '<p class="empty-msg">履歴なし</p>';

  const issues = (c.issues||[]).map(s=>`<div class="issue-item">${esc(s)}</div>`).join('')
    || '<p class="empty-msg">なし</p>';

  document.getElementById('d-sections').innerHTML = `
    <div class="sec">
      <div class="sec-hdr" onclick="toggleSec('sum-${id}')">案件概要</div>
      <div class="sec-body" id="sum-${id}"><div class="summary-text">${esc(c.summary)||'（記載なし）'}</div></div>
    </div>
    <div class="sec">
      <div class="sec-hdr" onclick="toggleSec('tl-${id}')">更新履歴 (${(c.timeline||[]).length}件)</div>
      <div class="sec-body" id="tl-${id}">${tl}</div>
    </div>
    <div class="sec">
      <div class="sec-hdr" onclick="toggleSec('iss-${id}')">要求事項 (${(c.issues||[]).length}件)</div>
      <div class="sec-body" id="iss-${id}">${issues}</div>
    </div>`;
}

function showList(){
  document.getElementById('list-view').style.display='block';
  document.getElementById('detail').style.display='none';
}

function toggleSec(id){
  const body = document.getElementById(id);
  const hdr = body.previousElementSibling;
  body.classList.toggle('hidden');
  hdr.classList.toggle('collapsed');
}

initStats();
renderTable();
</script>
</body>
</html>"""

# ──────────────────────────────────────────
# 出力
# ──────────────────────────────────────────
html = HTML.replace("__CASES_JSON__", cases_js)
out_path = OUT_DIR / OUT_NAME
out_path.write_text(html, encoding="utf-8")
print(f"出力: {out_path}")
print(f"ファイルサイズ: {out_path.stat().st_size // 1024} KB")
