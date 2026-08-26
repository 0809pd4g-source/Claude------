#!/usr/bin/env python3
"""gen_html.py — 課題解決支援チーム 定常業務マニュアル HTML を生成する"""
import subprocess, sys, json, os
from pathlib import Path
from datetime import date

BASE = Path(__file__).parent
OUT_NAME = f"20260728_課題解決支援チーム_定常業務マニュアル_v27.html"
OUT  = BASE.parent / "02_output" / OUT_NAME

TITLE      = "課題解決支援チーム 定常業務マニュアル"
TEAM_LABEL = "課題解決支援チーム"

# ── セクション定義 ────────────────────────────────────────────────────────────
# (sid, type, title, target_meeting, search_key, cadence, cat_id)
SECTIONS = [
    # ─ 共通
    ("s0",  "参考", "全マニュアル共通ルール",
     "全セクション共通",
     "共通", "-", "m_cat0", "t_cat0"),
    # ─ 進捗連絡会議・課題検討会
    ("s1",  "手順", "会議参加・ロジ対応",
     "進捗連絡会議（月 13:30）／課題検討会（月 14:00）",
     "会議参加・ロジ対応", "週次", "m_cat1", "t_cat1"),
    ("s3",  "手順", "週次運営：課題検討会・進捗連絡会議（火〜月）",
     "進捗連絡会議（月 13:30）／課題検討会（月 14:00）",
     "週次運営", "週次", "m_cat1", "t_cat2"),
    ("s7",  "手順", "議事要旨：作成フロー（木〜火）",
     "進捗連絡会議（月 13:30）／課題検討会（月 14:00）",
     "作成フロー（木〜火）", "週次", "m_cat1", "t_cat3"),
    ("s8",  "手順", "議事要旨：承認フロー（火〜金）",
     "進捗連絡会議（月 13:30）／課題検討会（月 14:00）",
     "承認フロー（火〜金）", "週次", "m_cat1", "t_cat3"),
    ("s10", "手順", "議事要旨：事業者送付（火）",
     "進捗連絡会議（月 13:30）",
     "事業者送付（火）", "週次", "m_cat1", "t_cat3"),
    # ─ 個別検討会
    ("s11", "手順", "会議参加・議事メモ・報告",
     "個別検討会（火 15:30／水 10:00）",
     "議事メモ・報告", "週次", "m_cat2", "t_cat1"),
    # ─ 基金定例
    ("s12", "手順", "議事メモ・ToDo起票",
     "基金定例（水 16:00）",
     "ToDo起票", "週次", "m_cat3", "t_cat1"),
    ("s14", "手順", "アジェンダ・会議体更新（火〜木）",
     "基金定例（水 16:00）→三者定例（金 13:00）",
     "アジェンダ・会議体更新", "週次", "m_cat3", "t_cat4"),
    # ─ 三者定例
    ("s13", "手順", "会議運営・議事要旨確定",
     "三者定例（金 13:00）",
     "会議運営・議事要旨確定", "週次", "m_cat4", "t_cat4"),
    ("s15", "手順", "議事要旨・資料更新（木〜金）",
     "三者定例（金 13:00）",
     "議事要旨・資料更新", "週次", "m_cat4", "t_cat4"),
    # ─ 月次
    ("s16", "手順", "ステコミ：議事録作成",
     "ステアリングコミッティ",
     "ステコミ：議事録作成", "月次", "m_cat5", "t_cat5"),
    ("s17", "手順", "納品（月次）",
     "月次納品",
     "納品（月次）", "月次", "m_cat5", "t_cat5"),
    # ─ 台帳・参考
    ("s6",  "メモ",  "議事要旨：作成メモ",
     "進捗連絡会議 ／ 課題検討会",
     "作成メモ", "-", "m_cat6", "t_cat3"),
    ("s9",  "手順", "課題・ToDo台帳 更新・整理",
     "〔原本〕課題・ToDo管理台帳.xlsx",
     "課題・ToDo台帳", "-", "m_cat6", "t_cat6"),
    ("s18", "手順", "参加者名簿更新",
     "進捗連絡会議",
     "参加者名簿更新", "随時", "m_cat6", "t_cat6"),
    ("s19", "参考", "会議調整・Inv更新",
     "",
     "会議調整・Inv更新", "随時", "m_cat6", "t_cat6"),
    ("s20", "参考", "用語集",
     "",
     "用語集", "-", "m_cat6", "t_cat6"),
]

# ── カテゴリ定義（会議別） ────────────────────────────────────────────────────
CATS_MEETING = [
    {"id": "m_cat0", "label": "共通ルール",               "cadence": "-",
     "color": "#1a2e4a"},
    {"id": "m_cat1", "label": "進捗連絡会議・課題検討会", "cadence": "週次",
     "color": "#3b82f6"},
    {"id": "m_cat2", "label": "個別検討会",               "cadence": "週次",
     "color": "#8b5cf6"},
    {"id": "m_cat3", "label": "基金定例（水）",            "cadence": "週次",
     "color": "#059669"},
    {"id": "m_cat4", "label": "三者定例（金）",            "cadence": "週次",
     "color": "#0d9488"},
    {"id": "m_cat5", "label": "ステコミ・納品",            "cadence": "月次",
     "color": "#d97706"},
    {"id": "m_cat6", "label": "台帳・随時対応",            "cadence": "-",
     "color": "#6b7280"},
]

# ── カテゴリ定義（作業別） ────────────────────────────────────────────────────
CATS_TASK = [
    {"id": "t_cat0", "label": "共通ルール",               "cadence": "-",
     "color": "#1a2e4a"},
    {"id": "t_cat1", "label": "会議参加・議事メモ作成",   "cadence": "週次",
     "color": "#3b82f6"},
    {"id": "t_cat2", "label": "資料作成・連携",            "cadence": "週次",
     "color": "#8b5cf6"},
    {"id": "t_cat3", "label": "議事要旨",                  "cadence": "週次",
     "color": "#059669"},
    {"id": "t_cat4", "label": "定例準備・会議体管理",      "cadence": "週次",
     "color": "#0d9488"},
    {"id": "t_cat5", "label": "月次業務",                  "cadence": "月次",
     "color": "#d97706"},
    {"id": "t_cat6", "label": "台帳・随時対応",            "cadence": "-",
     "color": "#6b7280"},
]

# ── コンテンツ取得 ────────────────────────────────────────────────────────────
def get_content(search_key):
    e = os.environ.copy()
    e["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, str(BASE / "manual_editor.py"), "show", search_key],
        capture_output=True, encoding="utf-8", errors="replace", env=e, cwd=str(BASE)
    )
    text = r.stdout
    blocks = []
    lines = text.split("\n")
    current_block = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("=== ") and stripped.endswith(" ==="):
            if current_block:
                blocks.append(current_block)
            current_block = []
            in_block = True
            continue
        if in_block:
            current_block.append(stripped)
    if current_block:
        blocks.append(current_block)
    if not blocks:
        return ""
    block_lines = blocks[0]
    content_lines = []
    started = False
    for line in block_lines:
        if not started:
            if (line.startswith("対象") or line.startswith("最終更新") or
                    line.startswith("【") or line == ""):
                continue
            if line.startswith("## "):
                started = True
        if started:
            content_lines.append(line)
    return "\n".join(content_lines).strip()

# ── データ取得 ────────────────────────────────────────────────────────────────
print("セクションデータ取得中...")
section_data = []
for sid, stype, stitle, starget, skey, cadence, m_cat, t_cat in SECTIONS:
    print(f"  [{cadence}] {stitle[:28]}...", end="", flush=True)
    content = get_content(skey)
    section_data.append({
        "id": sid, "type": stype, "title": stitle,
        "target": starget, "cadence": cadence,
        "m_cat": m_cat, "t_cat": t_cat,
        "content": content,
        "updated": str(date.today()), "author": "中澤"
    })
    print(f" ({len(content)}文字)")

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
:root{--sb:272px;--pri:#1a2e4a;--acc:#2563eb;--txt:#1f2937;--mu:#6b7280;--bd:#e5e7eb;--bg:#f9fafb}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Hiragino Sans','Yu Gothic',Meiryo,sans-serif;font-size:14px;color:var(--txt);background:var(--bg);display:flex;height:100vh;overflow:hidden}
/* ─ Sidebar */
#sb{width:var(--sb);min-width:var(--sb);background:var(--pri);color:#fff;display:flex;flex-direction:column;height:100vh;overflow:hidden}
#sb-hd{padding:14px 12px 10px;border-bottom:1px solid rgba(255,255,255,.12)}
#sb-tag{font-size:9.5px;font-weight:700;letter-spacing:.1em;color:rgba(255,255,255,.45);text-transform:uppercase}
#sb-ttl{font-size:12.5px;font-weight:700;color:#fff;margin-top:4px;line-height:1.5}
#sb-srch{padding:8px 10px;border-bottom:1px solid rgba(255,255,255,.1)}
#srch-in{width:100%;padding:5px 8px;border-radius:5px;border:none;background:rgba(255,255,255,.15);color:#fff;font-size:12px;outline:none}
#srch-in::placeholder{color:rgba(255,255,255,.4)}
#srch-in:focus{background:rgba(255,255,255,.22)}
#nav{flex:1;overflow-y:auto;padding:4px 0 12px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.15) transparent}
/* ─ Category headers */
.cat-hd{padding:10px 10px 4px;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none}
.cat-hd:hover{background:rgba(255,255,255,.05)}
.cat-cadence{font-size:9px;padding:1px 5px;border-radius:10px;font-weight:700;white-space:nowrap;background:rgba(255,255,255,.18);color:rgba(255,255,255,.8)}
.cat-cadence.月次{background:rgba(217,119,6,.4);color:#fde68a}
.cat-cadence.随時{background:rgba(107,114,128,.4);color:#d1d5db}
.cat-name{font-size:10.5px;font-weight:700;color:rgba(255,255,255,.7);flex:1;line-height:1.3}
.cat-arrow{font-size:9px;color:rgba(255,255,255,.3);transition:transform .15s}
.cat-hd.collapsed .cat-arrow{transform:rotate(-90deg)}
.cat-body{overflow:hidden}
.cat-body.collapsed{display:none}
/* ─ Nav items */
.ni{display:flex;align-items:flex-start;gap:5px;padding:5px 10px 5px 20px;cursor:pointer;font-size:11px;line-height:1.4;color:rgba(255,255,255,.65);border-left:3px solid transparent;transition:background .1s}
.ni:hover{background:rgba(255,255,255,.08);color:#fff}
.ni.active{background:rgba(255,255,255,.12);color:#fff;border-left-color:#60a5fa}
.ni-bd{font-size:8.5px;padding:1px 4px;border-radius:3px;font-weight:700;white-space:nowrap;flex-shrink:0;margin-top:2px}
.bd-手順{background:rgba(96,165,250,.3);color:#bfdbfe}
.bd-メモ{background:rgba(52,211,153,.3);color:#a7f3d0}
.bd-台帳{background:rgba(251,191,36,.3);color:#fde68a}
.bd-参考{background:rgba(156,163,175,.3);color:#d1d5db}
.ni-tx{flex:1}
/* ─ Main */
#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
#topbar{background:#fff;border-bottom:1px solid var(--bd);padding:8px 20px;display:flex;align-items:center;gap:8px;min-height:42px}
#cur-ttl{font-size:13px;font-weight:600;color:var(--pri);flex:1}
.tb-btn{padding:3px 10px;font-size:11px;border-radius:4px;border:1px solid var(--bd);background:#fff;cursor:pointer;color:var(--txt)}
.tb-btn:hover{background:var(--bg)}
#ca{flex:1;overflow-y:auto;scrollbar-width:thin;scrollbar-color:#d1d5db transparent}
/* ─ Section */
.sec{display:none;padding:22px 28px 48px;max-width:840px}
.sec.active{display:block}
.sec-meta{display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.sec-cat-tag{font-size:10px;padding:2px 7px;border-radius:3px;font-weight:700;color:#fff}
.sec-cadence{font-size:10px;padding:2px 7px;border-radius:3px;font-weight:700;border:1px solid var(--bd);color:var(--mu)}
.sec-cadence.週次{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
.sec-cadence.月次{background:#fffbeb;color:#92400e;border-color:#fde68a}
.sec-cadence.随時{background:#f3f4f6;color:#374151;border-color:#d1d5db}
.sec-type{font-size:10px;padding:2px 7px;border-radius:3px;font-weight:700}
.sec-type.手順{background:#dbeafe;color:#1e40af}
.sec-type.メモ{background:#d1fae5;color:#065f46}
.sec-type.台帳{background:#fef3c7;color:#92400e}
.sec-type.参考{background:#f3f4f6;color:#374151}
.tgt{font-size:11px;color:var(--mu);background:var(--bg);padding:2px 7px;border-radius:4px;border:1px solid var(--bd)}
.upd{font-size:11px;color:var(--mu);margin-left:auto}
.sec-h1{font-size:18px;font-weight:700;color:var(--pri);margin-bottom:18px;line-height:1.35}
/* ─ Content body */
.cb h2{font-size:14px;font-weight:700;color:var(--pri);margin:22px 0 8px;padding-bottom:5px;border-bottom:2px solid #dbeafe}
.cb h2:first-child{margin-top:0}
.cb h3{font-size:12.5px;font-weight:700;color:#1e40af;margin:12px 0 5px;padding:5px 9px;background:#eff6ff;border-radius:4px;border-left:3px solid #3b82f6}
.cb p{margin:3px 0;line-height:1.75;color:#374151}
.cb ul.lns{list-style:none;margin:3px 0 8px;padding:0}
.cb ul.lns li{padding:2px 0 2px 12px;line-height:1.65;color:#374151;position:relative}
.cb ul.lns li::before{content:'·';position:absolute;left:3px;color:var(--mu)}
.chk{display:flex;align-items:flex-start;gap:7px;padding:3px 0}
.chk input{margin-top:2px;width:14px;height:14px;flex-shrink:0;accent-color:#3b82f6;cursor:pointer}
.chk label{cursor:pointer;color:#374151;line-height:1.6;flex:1}
.chk input:checked+label{color:#9ca3af;text-decoration:line-through}
.wrn{background:#fef2f2;border:1px solid #fecaca;border-radius:5px;padding:6px 10px;margin:4px 0;color:#991b1b;font-size:13px;line-height:1.65}
.nt{color:var(--mu);font-size:12px;padding:2px 0 2px 10px;border-left:2px solid var(--bd);margin:3px 0;line-height:1.6}
.fr{font-size:12px;background:#eff6ff;color:#1e40af;padding:1px 4px;border-radius:3px;font-family:monospace}
.bun{background:#f8fafc;border:1px solid var(--bd);border-left:3px solid #94a3b8;border-radius:5px;padding:10px 12px;margin:8px 0;font-size:12.5px;line-height:1.85;white-space:pre-wrap}
.bl{color:var(--acc);text-decoration:underline;text-underline-offset:2px;cursor:pointer;font-weight:600}
.bl:hover{color:#1e40af}
.bun-h{scroll-margin-top:10px}
.bun-h.bun-hl{background:#fde68a!important;border-left-color:#d97706!important;transition:background .3s}
.empty-sec{color:var(--mu);font-size:13px;padding:12px;border:1px dashed var(--bd);border-radius:5px;text-align:center}
/* ─ Welcome / Search */
#welcome{padding:40px 32px;color:var(--mu)}
#welcome h2{font-size:18px;color:var(--pri);margin-bottom:12px}
#srch-res{display:none;padding:20px 28px}
.sr-item{padding:12px;margin-bottom:8px;background:#fff;border:1px solid var(--bd);border-radius:6px;cursor:pointer}
.sr-item:hover{border-color:#93c5fd}
.sr-sec{font-size:11px;color:var(--mu);margin-bottom:4px}
.sr-txt{font-size:13px;color:var(--txt);line-height:1.5}
#view-toggle{display:flex;padding:6px 8px;gap:4px;border-bottom:1px solid rgba(255,255,255,.1)}
.vt-btn{flex:1;padding:4px 6px;font-size:11px;font-weight:600;border-radius:4px;border:1px solid rgba(255,255,255,.2);background:transparent;color:rgba(255,255,255,.55);cursor:pointer;transition:all .15s}
.vt-btn:hover{background:rgba(255,255,255,.1);color:#fff}
.vt-btn.active-view{background:rgba(255,255,255,.2);color:#fff;border-color:rgba(255,255,255,.35)}
@media print{body{overflow:visible;display:block}#sb{display:none}#main{overflow:visible}#topbar{display:none}#ca{overflow:visible}.sec{display:block!important;page-break-before:always}.sec:first-child{page-break-before:auto}}
"""

# ── JavaScript ────────────────────────────────────────────────────────────────
JS_TMPL = """
const SECS = %s;
const CATS_MEETING = %s;
const CATS_TASK = %s;

let curId = null;
let viewMode = 'meeting';
let chkState = JSON.parse(localStorage.getItem('chkState')||'{}');

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}

const BUN_NUM={'①':'1','②':'2','③':'3','④':'4','⑤':'5'};
function inlineProcess(t){
  let r = esc(t);
  r = r.replace(/(📁)([^\\s,。、<\\n（）]+)/g,'$1<span class="fr">$2</span>');
  r = r.replace(/(📄)([^\\s,。、<\\n（）]+)/g,'$1<span class="fr">$2</span>');
  r = r.replace(/文案([A-C])([①②③④⑤])(・([A-C])([①②③④⑤]))?/g,function(m,l1,d1,rest,l2,d2){
    let o='<a class="bl" href="#" onclick="jumpBun(event,\\''+l1+BUN_NUM[d1]+'\\')">文案'+l1+d1+'</a>';
    if(rest){ o+='・<a class="bl" href="#" onclick="jumpBun(event,\\''+l2+BUN_NUM[d2]+'\\')">'+l2+d2+'</a>'; }
    return o;
  });
  return r;
}
function jumpBun(ev, code){
  ev.preventDefault();
  const t=document.getElementById('bun-'+code);
  if(t){ t.scrollIntoView({behavior:'smooth',block:'start'}); t.classList.add('bun-hl'); setTimeout(()=>t.classList.remove('bun-hl'),1600); }
}

function renderContent(raw, secId){
  const lines = raw.split('\\n');
  let html = '';
  let buf = [];
  let inBun = false;
  let bunBuf = [];

  function flushBuf(){
    if(!buf.length) return;
    if(buf.length===1) html += '<p>'+inlineProcess(buf[0])+'</p>';
    else{ html+='<ul class="lns">'; buf.forEach(l=>{ html+='<li>'+inlineProcess(l)+'</li>'; }); html+='</ul>'; }
    buf=[];
  }
  function flushBun(){
    if(!bunBuf.length) return;
    html += '<div class="bun">'+esc(bunBuf.join('\\n'))+'</div>';
    bunBuf=[];
  }

  for(const rawL of lines){
    const l = rawL.trim();
    if(!l){ flushBuf(); flushBun(); continue; }
    if(l.startsWith('## ')){
      flushBuf(); flushBun();
      const h = l.slice(3);
      inBun = (h==='文案'||h.startsWith('文案'));
      html += '<h2>'+esc(h)+'</h2>';
    } else if(l.startsWith('### ')){
      const h = l.slice(4);
      if(inBun){ flushBun();
        const mm=h.match(/文案([A-C])([①②③④⑤])/);
        const idA = mm? ' id="bun-'+mm[1]+BUN_NUM[mm[2]]+'"':'';
        html+='<h3'+idA+' class="bun-h">'+esc(h)+'</h3>'; }
      else { flushBuf(); html+='<h3>'+esc(h)+'</h3>'; }
    } else if(l.startsWith('☐ ')){
      flushBuf(); flushBun();
      const id='c'+Math.random().toString(36).slice(2,8);
      const txt = l.slice(2);
      const key = secId+'|'+txt;
      const ckd = chkState[key]?'checked':'';
      html+=`<div class="chk"><input type="checkbox" id="${id}" ${ckd} onchange="saveChk('${key}',this.checked)"><label for="${id}">${inlineProcess(txt)}</label></div>`;
    } else if(l.startsWith('⚠️')){
      flushBuf(); flushBun();
      html+='<div class="wrn">'+inlineProcess(l)+'</div>';
    } else if(l.startsWith('※')){
      if(inBun) bunBuf.push(l);
      else { flushBuf(); html+='<div class="nt">'+inlineProcess(l)+'</div>'; }
    } else if(l.startsWith('▼') || (inBun && l.startsWith('# '))){
      bunBuf.push(l);
    } else {
      if(inBun) bunBuf.push(l);
      else buf.push(l);
    }
  }
  flushBuf(); flushBun();
  return html||'<div class="empty-sec">（このセクションの詳細は原本docxを参照してください）</div>';
}

function saveChk(key,val){
  chkState[key]=val;
  localStorage.setItem('chkState',JSON.stringify(chkState));
}

function switchView(mode){
  viewMode = mode;
  document.getElementById('btn-meeting').classList.toggle('active-view', mode==='meeting');
  document.getElementById('btn-task').classList.toggle('active-view', mode==='task');
  buildNav(mode);
}

function buildNav(mode){
  const nav = document.getElementById('nav');
  nav.innerHTML = '';
  const cats = mode === 'task' ? CATS_TASK : CATS_MEETING;
  const catKey = mode === 'task' ? 't_cat' : 'm_cat';
  cats.forEach(cat=>{
    const hd = document.createElement('div');
    hd.className='cat-hd';
    hd.innerHTML=`<span class="cat-cadence ${cat.cadence}">${cat.cadence}</span><span class="cat-name">${esc(cat.label)}</span><span class="cat-arrow">▼</span>`;
    hd.onclick=()=>toggleCat(cat.id);
    nav.appendChild(hd);
    const body = document.createElement('div');
    body.className='cat-body'; body.id='cat_'+cat.id;
    const catSecs = SECS.filter(s=>s[catKey]===cat.id);
    catSecs.forEach(s=>{
      const el = document.createElement('div');
      el.className='ni'; el.id='ni_'+s.id;
      el.innerHTML=`<span class="ni-bd bd-${s.type}">${s.type}</span><span class="ni-tx">${esc(s.title)}</span>`;
      el.onclick=()=>showSec(s.id);
      body.appendChild(el);
    });
    nav.appendChild(body);
  });
  if(curId){
    const ni = document.getElementById('ni_'+curId);
    if(ni){ ni.classList.add('active'); }
  }
}

function toggleCat(catId){
  const body = document.getElementById('cat_'+catId);
  const hd = body.previousElementSibling;
  const collapsed = body.classList.toggle('collapsed');
  hd.classList.toggle('collapsed', collapsed);
}

function buildSections(){
  const cont = document.getElementById('sc');
  SECS.forEach(s=>{
    const cat = CATS_MEETING.find(c=>c.id===s.m_cat)||{label:'',color:'#6b7280'};
    const div = document.createElement('div');
    div.className='sec'; div.id='sec_'+s.id;
    const tgt = s.target ? `<span class="tgt">${esc(s.target)}</span>` : '';
    div.innerHTML=`
      <div class="sec-meta">
        <span class="sec-cadence ${s.cadence}">${esc(s.cadence)}</span>
        <span class="sec-cat-tag" style="background:${cat.color}">${esc(cat.label)}</span>
        <span class="sec-type ${s.type}">${s.type}</span>
        ${tgt}
        <span class="upd">最終更新：${s.updated}　担当：${s.author}</span>
      </div>
      <div class="sec-h1">【${esc(s.type)}】${esc(s.title)}</div>
      <div class="cb">${renderContent(s.content, s.id)}</div>`;
    cont.appendChild(div);
  });
}

function showSec(id){
  curId=id;
  document.querySelectorAll('.sec').forEach(e=>e.classList.remove('active'));
  document.querySelectorAll('.ni').forEach(e=>e.classList.remove('active'));
  document.getElementById('srch-res').style.display='none';
  document.getElementById('welcome').style.display='none';
  const secEl = document.getElementById('sec_'+id);
  if(secEl) secEl.classList.add('active');
  const ni = document.getElementById('ni_'+id);
  if(ni){ ni.classList.add('active'); ni.scrollIntoView({block:'nearest'}); }
  const s = SECS.find(x=>x.id===id);
  document.getElementById('cur-ttl').textContent = s? '【'+s.type+'】'+s.title : '';
  document.getElementById('ca').scrollTop=0;
}

function doSearch(q){
  const sr = document.getElementById('srch-res');
  document.querySelectorAll('.sec').forEach(e=>e.classList.remove('active'));
  document.getElementById('welcome').style.display='none';
  if(!q.trim()){ sr.style.display='none'; if(curId) showSec(curId); return; }
  const kw = q.trim().toLowerCase();
  const hits=[];
  SECS.forEach(s=>{
    const txt=(s.title+' '+s.target+' '+s.content).toLowerCase();
    if(txt.includes(kw)){
      const idx=txt.indexOf(kw);
      const start=Math.max(0,idx-40);
      const snip=(s.title+' '+s.target+' '+s.content).slice(start,start+120).replace(/\\n/g,' ');
      hits.push({s,snip});
    }
  });
  sr.style.display='block';
  if(!hits.length){ sr.innerHTML='<p style="color:#6b7280">「'+esc(q)+'」は見つかりませんでした</p>'; return; }
  sr.innerHTML='<p style="font-size:12px;color:#6b7280;margin-bottom:12px">'+hits.length+'件ヒット</p>'+
    hits.map(({s,snip})=>`<div class="sr-item" onclick="showSec('${s.id}')">
      <div class="sr-sec">【${esc(s.type)}】${esc(s.title)}</div>
      <div class="sr-txt">...${esc(snip)}...</div>
    </div>`).join('');
  document.getElementById('cur-ttl').textContent=hits.length+'件ヒット';
}

function resetAll(){
  if(!confirm('すべてのチェックをリセットしますか？')) return;
  chkState={};
  localStorage.setItem('chkState','{}');
  document.querySelectorAll('.chk input[type=checkbox]').forEach(el=>{el.checked=false;});
}

window.onload=()=>{
  buildNav('meeting');
  buildSections();
};
"""

# ── HTML生成 ──────────────────────────────────────────────────────────────────
def make_html(secs, cats_meeting, cats_task):
    js_secs   = json.dumps(secs, ensure_ascii=False)
    js_cats_m = json.dumps(cats_meeting, ensure_ascii=False)
    js_cats_t = json.dumps(cats_task, ensure_ascii=False)
    js_code   = JS_TMPL % (js_secs, js_cats_m, js_cats_t)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{TITLE}</title>
<style>{CSS}</style>
</head>
<body>
<nav id="sb">
  <div id="sb-hd">
    <div id="sb-tag">{TEAM_LABEL}</div>
    <div id="sb-ttl">定常業務<br>マニュアル</div>
  </div>
  <div id="view-toggle">
    <button id="btn-meeting" class="vt-btn active-view" onclick="switchView('meeting')">会議別</button>
    <button id="btn-task" class="vt-btn" onclick="switchView('task')">作業別</button>
  </div>
  <div id="sb-srch">
    <input type="text" id="srch-in" placeholder="🔍 検索..." oninput="doSearch(this.value)">
  </div>
  <div id="nav"></div>
</nav>
<main id="main">
  <div id="topbar">
    <span id="cur-ttl">セクションを選択してください</span>
    <button class="tb-btn" onclick="window.print()">🖨 印刷</button>
    <button class="tb-btn" onclick="resetAll()">☑ リセット</button>
  </div>
  <div id="ca">
    <div id="welcome">
      <h2>{TITLE}</h2>
      <p>左のメニューからカテゴリ・セクションを選択するか、検索をご利用ください。<br>チェックリストの状態はブラウザに保存されます。</p>
    </div>
    <div id="sc"></div>
    <div id="srch-res"></div>
  </div>
</main>
<script>{js_code}</script>
</body>
</html>"""
    return html

print("\nHTML生成中...")
def to_js_cats(cats):
    return [{"id": c["id"], "label": c["label"],
             "cadence": c["cadence"], "color": c["color"]} for c in cats]

html = make_html(section_data, to_js_cats(CATS_MEETING), to_js_cats(CATS_TASK))
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"✅ 保存完了: {OUT}")
print(f"   サイズ: {len(html)//1024} KB")
