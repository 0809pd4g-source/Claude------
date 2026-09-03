# -*- coding: utf-8 -*-
"""東ティモールビジネス実務ガイド v1 を、東ティモールKB v39.33 のトリムで生成。
方針：<head>/CSS/全<script> は保持。本文は業務7セクション＋references＋scope-caveatsのみ残す。
ブランド/版はJS定数＋テンプレートを差し替え。埋め込みJSONはパースして撤去id参照を安全処理。"""
import re, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

F = "20260903_東ティモールビジネス実務ガイド/02_output/20260903_東ティモールビジネス実務ガイド_v1.html"
html = open(F, encoding="utf-8").read()
log=[]
BACK = "../../20260729_東ティモールナレッジベース/02_output/20260729_東ティモールナレッジベース_v39.34.html"
KEEP = {"business-practical","business-registration-licensing","business-investment-land-banking",
        "business-tax-calendar","business-employment-payroll","job-seeker-guide","business-customs-procurement",
        "references","scope-caveats"}

# ===== 1) KEEP以外のトップレベルsectionを除去 =====
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
remove=[]
for s,e,a in tops:
    idm=re.search(r'\sid="([^"]*)"',a)
    sid=idm.group(1) if idm else None
    if sid not in KEEP: remove.append((s,e,sid))
# remove right-to-left
for s,e,sid in sorted(remove,reverse=True):
    html=html[:s]+html[e:]
log.append(f"sections removed={len(remove)} kept={len(tops)-len(remove)}")

# ===== 2) ブランド／版の差し替え（静的＋JSテンプレート） =====
reps = [
 ("window.KB_VERSION='v39.33'", "window.KB_VERSION='v1'"),
 ("window.KB_DATE='2026-07-30'", "window.KB_DATE='2026-09-03'"),
 ("<title>Timor-Leste Knowledge Base v39.33 閲覧導線・コンパクトUI版</title>",
  "<title>Timor-Leste Business Practical Guide v1 ビジネス実務・法制度版</title>"),
 ("document.title=`Timor-Leste Knowledge Base ${ver} 閲覧導線・コンパクトUI版`",
  "document.title=`Timor-Leste Business Practical Guide ${ver} ビジネス実務・法制度版`"),
 ("`Timor-Leste Knowledge Base ／ ${ver} 閲覧導線・コンパクトUI版 ｜ 一般",
  "`Timor-Leste Business Practical Guide ／ ${ver} ビジネス実務・法制度版 ｜ 掲載"),
 ("Timor-Leste Knowledge Base ／ v39.33 閲覧導線・コンパクトUI版 ｜ 更新日 2026-07-30",
  "Timor-Leste Business Practical Guide ／ v1 ビジネス実務・法制度版 ｜ 更新日 2026-09-03"),
 ('<span class="brand-title">Timor-Leste <strong>Knowledge Base</strong></span>',
  '<span class="brand-title">Timor-Leste <strong>Business Guide</strong></span>'),
 ("東ティモール総合ナレッジベース", "東ティモール ビジネス実務ガイド"),
 ('<span class="brand-version">v39.33</span>', '<span class="brand-version">v1</span>'),
 ('class="brand-home" href="#start-guide"', 'class="brand-home" href="#business-practical"'),
 ("Timor-Leste Knowledge Baseのスタートガイドへ", "東ティモールビジネス実務ガイドの先頭へ"),
]
for a,b in reps:
    c=html.count(a); html=html.replace(a,b); log.append(f"brand '{a[:26]}' x{c}")

# ===== 3) 生存id集合を作り、埋め込みJSONを安全処理 =====
ALL_IDS = set(re.findall(r'\sid="([^"]*)"', html))
def filt(lst): return [x for x in lst if not(isinstance(x,str)) or x in ALL_IDS]
def clean(obj, drop_empty_sections):
    if isinstance(obj,list):
        out=[]
        for it in obj:
            c=clean(it,drop_empty_sections)
            if c is _DROP: continue
            out.append(c)
        return out
    if isinstance(obj,dict):
        drop=False
        if isinstance(obj.get('sections'),list):
            secs=obj['sections']; titles=obj.get('sectionTitles')
            keep=[i for i,x in enumerate(secs) if not isinstance(x,str) or x in ALL_IDS]
            had=len(keep)!=len(secs)
            obj['sections']=[secs[i] for i in keep]
            if isinstance(titles,list) and len(titles)==len(secs):
                obj['sectionTitles']=[titles[i] for i in keep]
            if drop_empty_sections and had and not obj['sections']: drop=True
        if isinstance(obj.get('targets'),list):
            obj['targets']=filt(obj['targets'])
        for k,v in list(obj.items()):
            if k in ('sections','sectionTitles','targets'): continue
            obj[k]=clean(v,drop_empty_sections)
        return _DROP if drop else obj
    return obj
_DROP=object()

def process_block(m):
    attrs,body=m.group(1),m.group(2)
    s=body.strip()
    if s[:1] not in '{[': return m.group(0)
    try: j=json.loads(s)
    except Exception: return m.group(0)
    # link-audit: 空sectionのソースは落とす／volatile・semantic は records保持（targetsのみ間引き）
    drop = 'tlkb-link-audit-data' in attrs
    j2=clean(j,drop)
    return '<script'+attrs+'>'+json.dumps(j2,ensure_ascii=False,separators=(',',':'))+'</script>'
html=re.sub(r'<script\b([^>]*)>(.*?)</script>', process_block, html, flags=re.S)

# ===== 4) 冒頭に別冊イントロ＋本編への戻りリンクを挿入（business-practical直前） =====
intro=(
'<section class="section-card content-card" id="biz-guide-intro">'
'<div class="callout"><strong>本冊について：</strong>本冊『東ティモール ビジネス実務ガイド』は、'
'会社設立・投資・税務・雇用実務・通関/調達・求職など<strong>実務・法制度</strong>に特化した別冊です。'
'国概要・社会・文化・自然・観光・研究などの情報は本編'
'<a href="'+BACK+'">『東ティモール総合ナレッジベース』</a>を参照してください。'
'対象読者：東ティモールで事業・就労する人／投資検討者。数値・制度は変動が大きいため一次資料での再確認を推奨します。</div>'
'</section>')
html=html.replace('<section class="section-card content-card expanded-section" data-canonical-role="summary"',
                  intro+'<section class="section-card content-card expanded-section" data-canonical-role="summary"',1)
log.append("intro inserted:"+str('biz-guide-intro' in html))

open(F,"w",encoding="utf-8").write(html)
print("\n".join(log))
# diagnostics
secs=re.findall(r'<section\b[^>]*\sid="([^"]*)"',html)
print("remaining sections:",secs)
print("KB_VERSION:",re.search(r"KB_VERSION='([^']*)'",html).group(1))
# json parse check
okj=0
for m in re.finditer(r'<script\b[^>]*>(.*?)</script>',html,re.S):
    b=m.group(1).strip()
    if b[:1] in '{[':
        try: json.loads(b); okj+=1
        except Exception as e: print("JSON FAIL",str(e)[:50])
print("json blocks ok:",okj)
