# -*- coding: utf-8 -*-
"""v39.34: 本体KBからビジネス実務セクション＋ビジネスモードを撤去し経済系を残す。
v39.33 から決定論的に再構築する（JSONブロックはパースして安全に処理）。"""
import re, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = "20260729_東ティモールナレッジベース/02_output/20260729_東ティモールナレッジベース_v39.33.html"
DST = "20260729_東ティモールナレッジベース/02_output/20260729_東ティモールナレッジベース_v39.34.html"
html = open(SRC, encoding="utf-8").read()
log = []
BIZ_IDS = {"business-practical","business-registration-licensing","business-investment-land-banking",
           "business-tax-calendar","business-employment-payroll","job-seeker-guide","business-customs-procurement"}
BIZ_LINK = "../../20260903_東ティモールビジネス実務ガイド/02_output/20260903_東ティモールビジネス実務ガイド_v1.html"

# ===== 1) ビジネス7セクション（連続ブロック）をネスト対応で除去 =====
def top_sections(s):
    tok=re.compile(r'<section\b[^>]*>|</section>'); stack=[]; tops=[]
    for m in tok.finditer(s):
        if m.group().startswith('</'):
            if stack:
                st=stack.pop()
                if not stack: tops.append((st[0],m.end(),st[1]))
        else: stack.append((m.start(),m.group()))
    return tops
tops=top_sections(html)
ranges=[(s,e,re.search(r'\sid="([^"]*)"',a).group(1)) for s,e,a in tops if re.search(r'\sid="([^"]*)"',a) and re.search(r'\sid="([^"]*)"',a).group(1) in BIZ_IDS]
assert len(ranges)==7, len(ranges)
bs=min(r[0] for r in ranges); be=max(r[1] for r in ranges)
html=html[:bs]+html[be:]; log.append(f"biz block removed chars={be-bs}")

# ===== 2) ビジネスのフィルタボタン／ペルソナカード除去 =====
html,n=re.subn(r'<button[^>]*data-target="business"[^>]*>.*?</button>','',html,flags=re.S); log.append(f"filter btn:{n}")
html,n=re.subn(r'<a class="audience-card business-card"[^>]*>.*?</a>','',html,flags=re.S); log.append(f"persona card:{n}")

# ===== 3) five-mode-grid 5->4 =====
html=html.replace(".five-mode-grid { grid-template-columns:repeat(5,minmax(0,1fr)); }",
                  ".five-mode-grid { grid-template-columns:repeat(4,minmax(0,1fr)); }")

# ===== 4) data-modes / data-persona の business 除去 =====
def strip_modes(m):
    t=[x for x in m.group(1).split() if x!="business"]; return 'data-modes="'+" ".join(t or["research"])+'"'
html,n=re.subn(r'data-modes="([^"]*)"',strip_modes,html); log.append(f"data-modes:{n}")
html=html.replace('data-persona="research business"','data-persona="research"')

# ===== 5) 実務ロードマップ 💼->📊 経済・産業ルート＋別冊ポインタ =====
new_route=(
'<h3>📊 経済・産業を知るロードマップ</h3>\n'
'<p>マクロ経済の把握から、主要産業・インフラ・統計出典・ドナーまで、東ティモールの経済社会を理解する順に束ねます。'
'<strong>会社設立・投資優遇・税務・雇用実務・通関/調達・求職などの実務手順は、別冊'
'<a href="'+BIZ_LINK+'">『東ティモールビジネス実務ガイド』</a>に分離しました。</strong></p>\n'
'<ol>\n'
'<li><a href="#economy"><strong>経済</strong></a>／<a href="#economy-latest-snapshot"><strong>2026年最新経済スナップショット</strong></a> ― マクロ構造（資源依存・ドル化・貿易赤字）と最新指標。</li>\n'
'<li><a href="#infrastructure-digital"><strong>インフラ・デジタル</strong></a> ― 電力・通信・物流・デジタル環境の制約。</li>\n'
'<li><a href="#coffee-value-chain"><strong>コーヒー生産チェーン</strong></a>／<a href="#agriculture-food-security"><strong>農業・食料安全保障</strong></a>／<a href="#fisheries-sector"><strong>水産業</strong></a> ― 非石油の主要産業と構造課題。</li>\n'
'<li><a href="#statistics-navigator"><strong>統計データナビゲーター</strong></a>／<a href="#data-source-directory"><strong>統計出典ディレクトリ</strong></a> ― 意思決定に使う指標と一次出典。</li>\n'
'<li><a href="#national-development-plans"><strong>国家開発計画</strong></a>／<a href="#sector-policy-documents"><strong>セクター別政策文書</strong></a> ― 政府の優先分野と政策枠組み。</li>\n'
'<li><a href="#donor-landscape"><strong>主要ドナー・国際機関</strong></a> ― 資金の流れとパートナー候補。</li>\n'
'</ol>')
html,n=re.subn(r'<h3>💼 事業・投資家ロードマップ</h3>.*?</ol>',new_route,html,count=1,flags=re.S); log.append(f"roadmap:{n}")

# ===== 6) マトリクス callout の投資リンク／犯罪節プロースリンク／シナリオ article =====
html=html.replace('<a href="#business-investment-land-banking">投資・土地・法人口座</a>',
                  '別冊<a href="'+BIZ_LINK+'">『ビジネス実務ガイド』の投資・土地・法人口座</a>')
html=html.replace('<a href="#business-investment-land-banking">投資・土地・法人銀行口座</a>',
                  '別冊<a href="'+BIZ_LINK+'">『ビジネス実務ガイド』の投資・土地・法人銀行口座</a>')
html,n=re.subn(r'<article class="release-scenario-card" data-acceptance-scenario="business"[^>]*>.*?</article>','',html,flags=re.S); log.append(f"scenario article:{n}")

# ===== 7) ビジネス専用クイック回答サジェスト2件除去 =====
for tgt in ["#business-practical","#job-seeker-guide"]:
    html,n=re.subn(r"\{keys:\[[^\]]*\][^{}]*?href:'"+re.escape(tgt)+r"'[^{}]*?\},","",html); log.append(f"qa {tgt}:{n}")

# ===== 8) 文言調整（5->4 / 投資->経済） / 版番号 =====
for a,b in [('実務ロードマップ ― 移住・医療・投資','実務ロードマップ ― 移住・医療・経済'),
            ('5つの入口への','4つの入口への'),
            ('移住・駐在／医療・健康／事業・投資','移住・駐在／医療・健康／経済・産業'),
            ('5入口への高速ジャンプ','4入口への高速ジャンプ')]:
    html=html.replace(a,b)
html=html.replace("v39.33","v39.34"); log.append("version->v39.34")

# ===== 9) 埋め込みJSONブロックから biz 参照を安全に除去 =====
def clean_json(obj):
    if isinstance(obj,list):
        out=[]
        for it in obj:
            c=clean_json(it)
            if c is _DROP: continue
            out.append(c)
        return out
    if isinstance(obj,dict):
        drop=False
        # sections / sectionTitles を index 並行でフィルタ
        if isinstance(obj.get('sections'),list):
            secs=obj['sections']; titles=obj.get('sectionTitles')
            keep_idx=[i for i,x in enumerate(secs) if not(isinstance(x,str) and x in BIZ_IDS)]
            had=len(keep_idx)!=len(secs)
            obj['sections']=[secs[i] for i in keep_idx]
            if isinstance(titles,list) and len(titles)==len(secs):
                obj['sectionTitles']=[titles[i] for i in keep_idx]
            if had and not obj['sections']: drop=True
        for k in ('targets',):
            if isinstance(obj.get(k),list):
                orig=obj[k]; had=any(isinstance(x,str) and x in BIZ_IDS for x in orig)
                obj[k]=[x for x in orig if not(isinstance(x,str) and x in BIZ_IDS)]
                if had and not obj[k]: drop=True
        # その他の list 値からも biz id 文字列を除去
        for k,v in list(obj.items()):
            if k in ('sections','sectionTitles','targets'): continue
            obj[k]=clean_json(v)
        return _DROP if drop else obj
    return obj
_DROP=object()

def clean_block(m):
    attrs,body=m.group(1),m.group(2)
    s=body.strip()
    if s[:1] not in '{[': return m.group(0)
    try: j=json.loads(s)
    except Exception: return m.group(0)
    j2=clean_json(j)
    new=json.dumps(j2,ensure_ascii=False,separators=(',',':'))
    return '<script'+attrs+'>'+new+'</script>'
before_ct=len(re.findall(r'business-(?:practical|registration-licensing|investment-land-banking|tax-calendar|employment-payroll|customs-procurement)|job-seeker-guide',html))
html=re.sub(r'<script\b([^>]*)>(.*?)</script>',clean_block,html,flags=re.S)
after_ct=len(re.findall(r'business-(?:practical|registration-licensing|investment-land-banking|tax-calendar|employment-payroll|customs-procurement)|job-seeker-guide',html))
log.append(f"json clean biz-id refs {before_ct}->{after_ct}")

open(DST,"w",encoding="utf-8").write(html)
print("\n".join(log))
print("clickable biz hrefs:",re.findall(r"href[=:]['\"]#(business-[^'\"]*|job-seeker-guide)['\"]",html))
print("#undefined:",html.count('#undefined'))
