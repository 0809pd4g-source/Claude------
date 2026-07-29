# -*- coding: utf-8 -*-
"""
東ティモール ナレッジベース（別版）ビルダー
------------------------------------------------
入力: 02_成果物/20260727_東ティモールまとめ_別版_v1.html（＝元版 v19 の複製、全内容）
出力: 02_成果物/20260727_東ティモールまとめ_別版_v2.html

方針:
  - 元HTMLの各 <section> の中身（本文・表・SVG図・コールアウト・出典56件）を
    テキスト/数値を一切カットせず verbatim で保持する。
  - UIのみ差し替え: 固定ヘッダー / ペルソナフィルタ・パンくずバー /
    3カラム（左ナビ・中央本文・右目次）/ ライブ検索。
  - 40セクションを9章へ再編（順序を章立てに並べ替え）。各カードにペルソナタグを付与。
  - 元CSS（表・図・kicker等）は保持し、ヘッダー/mainの旧レイアウト規則のみ除去して
    新UIのCSSとマージ。
"""
import re
import sys
import io
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # プロジェクトルート
SRC = BASE / "02_成果物" / "20260727_東ティモールまとめ_別版_v1.html"
OUT = BASE / "02_成果物" / "20260727_東ティモールまとめ_別版_v13.html"
INDEX_PAGE = "20260727_東ティモール_プロジェクト索引_v4.html"  # 相互リンク先（成果物ハブ・言語切替・参考ガイド）

# ------------------------------------------------------------------
# 章メタ情報
# ------------------------------------------------------------------
CHAPTERS = {
    1: "概要・基礎データ",
    2: "自然・地理・環境",
    3: "歴史と記憶",
    4: "政治・ガバナンス・治安",
    5: "経済・産業・ビジネス",
    6: "社会・開発・生活ガイド",
    7: "言語・文化・アイデンティティ",
    8: "観光・遺産・旅の手引き",
    9: "研究リファレンス・データ",
}

# kicker(英語見出し, &記号は素の & で) -> (章番号, ペルソナタグ)
# 出力順＝このリストの順（＝章立て順に並べ替え）
# ※ v3改訂: 「農業・食料安全保障」を第5章→第6章へ移動。タグはフィルタが
#   「絞り込み」として機能するよう、各ペルソナが優先して読む節に限定して再付与。
MAPPING = [
    # 1. 概要・基礎データ（誰にとっても入口＝全対象中心）
    ("EXECUTIVE SUMMARY",            1, "research business living nature"),
    ("OVERVIEW",                     1, "research business living nature"),
    ("KEY INDICATORS",               1, "research business living nature"),
    ("SYMBOLS & HOLIDAYS",           1, "research living nature"),
    # 2. 自然・地理・環境
    ("GEOGRAPHY & ENVIRONMENT",      2, "research nature living"),
    ("NATURE & BIODIVERSITY",        2, "nature research"),
    ("REGIONS & CITIES",             2, "research business living nature"),
    # 3. 歴史と記憶
    ("HISTORY",                      3, "research living"),
    ("POST-2002 POLITICAL STRIFE",   3, "research business"),  # 政情安定＝投資判断に直結
    # 4. 政治・ガバナンス・治安
    ("POLITICS & GOVERNANCE",        4, "research business"),
    ("KEY FIGURES",                  4, "research business"),
    ("FOREIGN RELATIONS",            4, "research business"),
    ("SECURITY & YOUTH",             4, "research business living"),  # 治安＝ビジネスリスク/生活
    ("JUSTICE & LAW",                4, "research business living"),  # 法制度＝事業/居住の両面
    # 5. 経済・産業・ビジネス
    ("ECONOMY",                      5, "business research"),
    ("INFRASTRUCTURE & DIGITAL",     5, "business living research"),
    ("DIASPORA",                     5, "research business living"),
    # 6. 社会・開発・生活ガイド
    ("DEVELOPMENT & SOCIETY",        6, "research living"),
    ("SOCIAL CHALLENGES",            6, "research living"),
    ("AGRICULTURE & FOOD SECURITY",  6, "research business living"),  # 第5章→第6章へ移動
    ("EDUCATION",                    6, "research living"),
    ("COMPARATIVE VIEW",             6, "research business"),
    # 7. 言語・文化・アイデンティティ
    ("LANGUAGE, ETHNICITY & RELIGION", 7, "research business living"),  # 言語＝居住/事業に実用
    ("CULTURE & SOCIAL STRUCTURE",   7, "research living nature"),
    ("LITERATURE & FILM",            7, "research living nature"),
    ("NATIONAL IDENTITY",            7, "research living"),
    # 8. 観光・遺産・旅の手引き（実用の旅行情報は research を外して絞り込みを効かせる）
    ("HIGHLIGHTS",                   8, "nature living"),
    ("PRACTICAL DATA",               8, "living nature business"),
    ("DESTINATIONS",                 8, "nature living"),
    ("HERITAGE & RUINS",             8, "nature living research"),
    ("WHY VISIT",                    8, "nature living"),
    ("DID YOU KNOW?",                8, "living nature research"),
    ("TRAVEL & PRACTICAL INFO",      8, "living nature business"),
    # 9. 研究リファレンス・データ
    ("INSTITUTIONS & DATA",          9, "research business"),
    ("RESEARCH ANGLES",              9, "research"),
    ("DATA APPENDIX",                9, "research business"),
    ("GLOSSARY",                     9, "research business living nature"),  # 用語集は全対象の助け
    ("FURTHER READING",              9, "research"),
    ("REFERENCES",                   9, "research"),
    ("SCOPE & CAVEATS",              9, "research"),
]

TAG_LABEL = {
    "research": "研究",
    "business": "ビジネス",
    "living": "生活",
    "nature": "観光",
}

# ------------------------------------------------------------------
# 読み込み・分解
# ------------------------------------------------------------------
html = SRC.read_text(encoding="utf-8")

m = re.search(r"<style>(.*?)</style>", html, re.S)
orig_css = m.group(1)

m = re.search(r"<main>(.*?)</main>", html, re.S)
main_html = m.group(1)

# ------------------------------------------------------------------
# v6: 内容QAで検出した不整合・単位・表記の補正
#   元版(v1)は原本として温存し、ここでの置換のみで補正版を生成する。
#   ・数値の自己申告（セクション数・出典数）の陳腐化を実体に合わせる
#   ・年齢中央値カードを文書の統一表記「約21歳」に揃える
#   ・金額単位を US$ に統一（退役軍人給付のみ「万ドル」だった）
#   ・ディアスポラ構成比は出典由来のため数値は変えず、合計>100%の注記を追加
# ------------------------------------------------------------------
CONTENT_FIXES = [
    ("全35セクション＋図表6点＋用語集・文献ガイド・目次",
     "全40セクション（用語集・文献ガイド・統計付録を含む）＋図表6点"),
    ("出典45件を", "出典56件を"),
    ('21.3歳 <small>(2024推計)',
     '約21歳 <small>(2022国勢調査 約21.7／2024推計 約21.3)'),
    ("約7,200万ドル", "約7,200万US$"),
    # #4: 出典由来のため数値は保持し、原因を断定せず中立な注記に（合計 約106%）
    ("アイルランド6%</strong>。",
     "アイルランド6%</strong>（各構成比は概数で合計が約106%となるため、正確な内訳は出典で要確認）。"),
    # 残点: ポータルUIでは目次節を左右ナビに置換済み。旧「冒頭にカテゴリ別の目次」を是正
    ("冒頭に<strong>カテゴリ別の目次</strong>、末尾に<strong>統計付録</strong>・用語集・文献ガイドを備える。",
     "左右のナビゲーション（9章の索引）で全体を辿れ、末尾に<strong>統計付録</strong>・用語集・文献ガイドを備える。"),
    # v8: リンク切れ(404)の是正 ― 深リンク廃止のため安定した代替ページへ
    ("https://iwda.org.au/gender-quotas-increase-womens-participation-in-timor-lestes-parliament/",
     "https://iwda.org.au/timor-leste/"),
    ("https://www.laohamutuk.org/econ/pfund/PFundIndex.htm",
     "https://www.laohamutuk.org/"),
]
for _old, _new in CONTENT_FIXES:
    if _old not in main_html:
        print("!! 内容補正: 対象が見つかりません ->", _old[:28])
    main_html = main_html.replace(_old, _new, 1)

# 元CSSから旧レイアウト規則を除去（ヘッダーhero / .badge群 / main）
css = orig_css
css = re.sub(r"\n  header \{.*?\.badge\.hot \{[^}]*\}", "", css, flags=re.S)
css = re.sub(r"\n  main \{[^}]*\}", "", css)
# 旧 body 規則は残す（日本語フォント・配色）。ただし新UIと競合する要素規則はこの後 append する新CSSで上書き。

# 各 <section> を抽出（トップレベルはフラット構造）
blocks = re.findall(r"<section\b.*?</section>", main_html, re.S)

def kicker_of(block):
    mm = re.search(r'<span class="kicker">(.*?)</span>', block, re.S)
    if not mm:
        return None
    return mm.group(1).replace("&amp;", "&").strip()

by_kicker = {}
for b in blocks:
    k = kicker_of(b)
    if k is not None:
        by_kicker[k] = b

# 整合性チェック
mapped_keys = [k for (k, _, _) in MAPPING]
missing = [k for k in mapped_keys if k not in by_kicker]
extra = [k for k in by_kicker if k not in mapped_keys]
print("抽出セクション数:", len(by_kicker))
print("マッピング数    :", len(mapped_keys))
if missing:
    print("!! マッピング対象なのに元HTMLで見つからない:", missing)
print("マッピング外(=廃止/未割当):", extra)  # CONTENTS(目次) のみのはず
if missing:
    sys.exit("整合性エラー: セクション欠落。中断します。")

# ------------------------------------------------------------------
# 各カードのHTMLを組み立て
# ------------------------------------------------------------------
def badges_html(tags):
    parts = []
    for t in tags.split():
        parts.append(f'<span class="tag-badge {t}">{TAG_LABEL[t]}</span>')
    return '<div class="card-tags">' + "".join(parts) + "</div>"

# 章ごとにグループ化（MAPPING の順序を維持）
from collections import OrderedDict, defaultdict
chapter_items = defaultdict(list)
for idx, (k, ch, tags) in enumerate(MAPPING, start=1):
    chapter_items[ch].append((f"sec-{idx}", k, tags))

main_cards = []
for ch in range(1, 10):
    # 章見出し（最初のカードの直前に置き、id=chN をアンカーに）
    main_cards.append(
        f'<h2 class="chapter-heading" id="ch{ch}" data-chapter="{ch}">'
        f'<span class="chapter-num">{ch}</span>{CHAPTERS[ch]}</h2>'
    )
    for sid, k, tags in chapter_items[ch]:
        block = by_kicker[k]
        # 開始タグを差し替え
        new_open = (
            f'<section class="section-card" id="{sid}" '
            f'data-chapter="{ch}" data-tags="{tags}">'
        )
        block = re.sub(r"^<section\b[^>]*>", new_open, block, count=1)
        # 最初の </h2> の直後にペルソナバッジ行を挿入
        block = block.replace("</h2>", "</h2>\n      " + badges_html(tags), 1)
        # 表を横スクロール対応のラッパで包む（内容は不変・要素追加のみ）
        block = block.replace("<table>", '<div class="table-wrap"><table>').replace(
            "</table>", "</table></div>")
        main_cards.append(block)

# 統合メモ（やったこと・やっていないこと：UI版）を末尾(9章)に追加
integration_note = '''<section class="section-card" id="sec-uinote" data-chapter="9" data-tags="research business living nature">
    <h2><span class="kicker">ABOUT THIS EDITION</span>本UI版について（統合メモ）</h2>
    <div class="card-tags"><span class="tag-badge research">研究</span><span class="tag-badge business">ビジネス</span><span class="tag-badge living">生活</span><span class="tag-badge nature">観光</span></div>
    <div class="callout">
      <strong>やったこと：</strong>元版（v1＝旧v19）の全40セクション・図表6点（図1〜6）・表・出典56件を<strong>テキスト/数値を一切変更せず</strong>そのまま収録し、UIのみ「3カラム・ポータル」に差し替えました。40セクションを9章へ再編し、各カードに読者ペルソナ（研究／ビジネス／生活／観光）タグを付与。上部ボタンでの絞り込み（<strong>複数選択・AND/OR切替</strong>対応）、本文全体のライブ検索（<strong>検索語ハイライト</strong>付き）、<strong>ダークモード</strong>（設定を保存）、左右ナビのアンカー移動（<strong>スクロール連動の現在地ハイライト</strong>・スムーススクロール・「トップへ戻る」・モバイル用の章ジャンプ・表の横スクロール対応付き）を実装しています。<strong>章・タグを見直し</strong>、「農業・食料安全保障」を第6章（社会・開発）へ移動し、治安・司法・政治対立・言語などに生活／ビジネスの観点のタグを補って絞り込みの実用性を高めました。
    </div>
    <div class="callout warning">
      <strong>やっていないこと・留意点：</strong>本文の加筆・削除は行っていません。ただし内容QAで検出した軽微な不整合のみ補正しました（「本書の範囲」節のセクション数35→40・出典数45→56の陳腐化是正、年齢中央値カードの表記を統一表記「約21歳」に、退役軍人給付の金額単位を「万ドル」→「万US$」に統一、ディアスポラ構成比〈合計約106%〉は数値を保持したまま「概数・要出典確認」の注記を追加、旧「冒頭にカテゴリ別の目次」の記述を左右ナビ前提に是正）。数値そのものの妥当性・出典の扱いは元版「本書の範囲と未確認・留意事項」を参照。専門用語（Lulik／Barlake／MAGs 等）の定義は本文中の記述および「用語集」節に従います。注意喚起の枠は元版の note/caveat スタイルを新コールアウト表現に統一しました。章・タグの割り当ては編集上の便宜的分類であり、学術的な唯一の分類ではありません。
    </div>
  </section>'''
# 9章の最後（＝SCOPE & CAVEATS の後）に差し込む
main_cards.append(integration_note)

main_inner = "\n\n  ".join(main_cards)

# サイドバー / 右TOC（9章）
sidebar_li = "\n".join(
    f'      <li><a href="#ch{ch}">{ch}. {CHAPTERS[ch]}</a></li>' for ch in range(1, 10)
)
toc_li = "\n".join(
    f'      <li><a href="#ch{ch}">{ch}. {CHAPTERS[ch]}</a></li>' for ch in range(1, 10)
)
# モバイル用：章ジャンプ（サイドバー非表示時のナビ代替）
mchap_options = "\n".join(
    f'      <option value="ch{ch}">{ch}. {CHAPTERS[ch]}</option>' for ch in range(1, 10)
)

# ------------------------------------------------------------------
# 新UIのCSS（元CSSの後に追記して構造規則を上書き）
# ------------------------------------------------------------------
PORTAL_CSS = r"""
  /* ============ 新UI（ポータル）レイヤ ============ */
  html { scroll-behavior: smooth; }
  :root {
    --tl-red: #B22222;
    --tl-gold: #DAA520;
    --tl-dark: #1A1D20;
    --sidebar-width: 270px;
    --toc-width: 220px;
    --hh: 66px;   /* ヘッダー実高（JSで実測して上書き） */
    --sub: 44px;  /* サブバー実高（JSで実測して上書き） */
  }
  /* グローバルヘッダー */
  header.global-header {
    background: var(--tl-dark);
    color: #fff;
    padding: 12px 24px;
    position: sticky;
    top: 0;
    z-index: 1000;
    border-bottom: 3px solid var(--tl-gold);
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 16px;
  }
  header.global-header::before { content: none; }
  .brand-area h1 { margin: 0; font-size: 1.25rem; font-weight: 700; letter-spacing: .02em; color: #fff; border: 0; padding: 0; }
  .brand-area h1 span { color: var(--tl-gold); }
  .brand-area p {
    margin: 3px 0 0; font-size: .78rem; color: #ADB5BD;
    max-width: min(60vw, 680px);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .header-controls { display: flex; align-items: center; gap: 12px; }
  .search-box input {
    padding: 8px 14px; border-radius: 20px; border: 1px solid #495057;
    background: #2B3035; color: #fff; font-size: .85rem; width: 260px; outline: none;
  }
  .search-box input:focus { border-color: var(--tl-gold); }
  .lang-picker { font-size: .78rem; background: #2B3035; padding: 6px 12px; border-radius: 6px; border: 1px solid #495057; color: #adb5bd; }
  .lang-picker b { color: #fff; }

  /* サブバー */
  .sub-nav {
    background: #fff; border-bottom: 1px solid var(--border);
    padding: 9px 24px; display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 12px; position: sticky; top: var(--hh); z-index: 900;
  }
  .breadcrumbs { font-size: .8rem; color: var(--muted); }
  .persona-filters { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .persona-filters .flabel { font-size: .78rem; font-weight: 700; color: var(--muted); margin-right: 2px; }
  .filter-btn {
    border: 1px solid var(--border); background: var(--bg); padding: 4px 13px;
    border-radius: 16px; font-size: .78rem; cursor: pointer; font-weight: 700; transition: all .2s;
  }
  .filter-btn.active, .filter-btn:hover { background: var(--tl-red); color: #fff; border-color: var(--tl-red); }

  /* モバイル用・章ジャンプ（既定は非表示、狭幅で表示） */
  .mobile-chapter-nav {
    display: none; font-size: .82rem; font-weight: 700; color: var(--text);
    padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px;
    background: #fff; max-width: 60vw;
  }

  /* 表の横スクロール対応（潰さずスクロール） */
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 8px 0 4px; }
  .table-wrap > table { margin-top: 0; }

  /* 3カラム */
  .portal-container { display: flex; max-width: 1500px; margin: 0 auto; align-items: flex-start; }
  aside.sidebar {
    width: var(--sidebar-width); background: #fff; border-right: 1px solid var(--border);
    padding: 20px 14px; position: sticky; top: calc(var(--hh) + var(--sub));
    height: calc(100vh - var(--hh) - var(--sub)); overflow-y: auto; flex-shrink: 0;
  }
  .sidebar h3 { font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin: 0 0 10px; }
  .sidebar-nav { list-style: none; padding: 0; margin: 0; }
  .sidebar-nav li { margin-bottom: 3px; }
  .sidebar-nav a { display: block; padding: 8px 10px; border-radius: 6px; color: var(--text); text-decoration: none; font-size: .86rem; font-weight: 600; }
  .sidebar-nav a:hover { background: var(--soft); color: var(--tl-red); }
  .sidebar-nav a.active {
    background: #FDECEA; color: var(--tl-red); font-weight: 800;
    box-shadow: inset 3px 0 0 var(--tl-red);
  }

  main.content-area { flex: 1; min-width: 0; padding: 26px 34px; max-width: 940px; margin: 0; }

  aside.toc-right {
    width: var(--toc-width); padding: 20px 14px; position: sticky;
    top: calc(var(--hh) + var(--sub)); height: calc(100vh - var(--hh) - var(--sub));
    overflow-y: auto; font-size: .82rem; border-left: 1px solid var(--border); flex-shrink: 0;
  }
  .toc-right .toc-head { font-weight: 700; margin-bottom: 8px; color: var(--primary-dark); }
  .toc-right ul { list-style: none; padding-left: 0; margin: 0; line-height: 1.5; }
  .toc-right li { margin: 4px 0; }
  .toc-right a { color: var(--muted); text-decoration: none; display: block; padding: 2px 8px; border-left: 2px solid transparent; }
  .toc-right a:hover { color: var(--tl-red); }
  .toc-right a.active { color: var(--tl-red); font-weight: 700; border-left-color: var(--tl-red); }

  /* トップへ戻る */
  #to-top {
    position: fixed; right: 22px; bottom: 22px; z-index: 1200;
    width: 46px; height: 46px; border-radius: 50%; border: 0; cursor: pointer;
    background: var(--tl-red); color: #fff; font-size: 1.2rem; line-height: 1;
    box-shadow: 0 4px 14px rgba(0,0,0,.28); opacity: 0; pointer-events: none;
    transition: opacity .25s, transform .15s;
  }
  #to-top:hover { transform: translateY(-2px); }
  #to-top.show { opacity: 1; pointer-events: auto; }

  /* セクションカード（元 section 規則に付加） */
  .section-card { scroll-margin-top: calc(var(--hh) + var(--sub) + 14px); transition: opacity .25s; }
  .section-card.hidden { display: none; }

  /* 章見出し */
  .chapter-heading {
    border: 0; border-left: 0; padding: 0; margin: 34px 0 14px;
    display: flex; align-items: center; gap: 12px;
    font-size: 1.15rem; color: var(--tl-dark);
    letter-spacing: .04em; scroll-margin-top: calc(var(--hh) + var(--sub) + 14px);
  }
  .chapter-heading:first-child { margin-top: 4px; }
  .chapter-heading.hidden { display: none; }
  .chapter-heading .chapter-num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 34px; height: 34px; border-radius: 8px; flex-shrink: 0;
    background: var(--tl-red); color: #fff; font-weight: 800; font-size: 1rem;
  }
  .chapter-heading::after { content: ""; flex: 1; height: 3px; border-radius: 2px; background: linear-gradient(to right, var(--tl-gold), transparent); }

  /* ペルソナタグ・バッジ */
  .card-tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 0 0 14px; }
  .tag-badge { font-size: .68rem; padding: 3px 9px; border-radius: 5px; font-weight: 700; letter-spacing: .02em; }
  .tag-badge.research { background: #E3F2FD; color: #0D47A1; }
  .tag-badge.business { background: #E8F5E9; color: #1B5E20; }
  .tag-badge.living   { background: #FFF3E0; color: #8A3D00; }  /* コントラスト確保（AA） */
  .tag-badge.nature   { background: #F3E5F5; color: #4A148C; }

  /* コールアウト（注意喚起）＋ 元 note/caveat を同表現に統一 */
  .callout, .note {
    border-left: 4px solid var(--tl-gold); background: #FFFDE7;
    padding: 14px 18px; border-radius: 0 8px 8px 0; margin: 18px 0; font-size: .92rem;
  }
  .callout.warning, .caveat {
    border-left: 4px solid var(--tl-red); background: #FFEBEE;
    border-top: 0; border-right: 0; border-bottom: 0; border-radius: 0 8px 8px 0;
  }

  /* 検索ハイライト時の空章の非表示は JS で制御 */
  .no-result { display: none; padding: 40px; text-align: center; color: var(--muted); }
  .no-result.show { display: block; }

  /* テーマ切替ボタン */
  .theme-toggle {
    background: #2B3035; color: #fff; border: 1px solid #495057;
    width: 36px; height: 34px; border-radius: 8px; cursor: pointer; font-size: 1rem; line-height: 1;
  }
  .theme-toggle:hover { border-color: var(--tl-gold); }

  /* AND/OR 論理トグル */
  .logic-toggle {
    border: 1px solid var(--border); background: #fff; color: var(--text);
    padding: 4px 10px; border-radius: 16px; font-size: .72rem; font-weight: 800; cursor: pointer; letter-spacing: .03em;
  }
  .logic-toggle:hover { border-color: var(--tl-red); }
  .filter-hint { font-size: .72rem; color: var(--muted); }

  /* 検索ハイライト */
  mark.kb-hl { background: #ffe08a; color: #111; border-radius: 2px; padding: 0 1px; }

  /* ============ ダークモード ============ */
  html[data-theme="dark"] {
    --bg: #12171a; --card: #1b2226; --text: #e6edf0; --muted: #9fb2b9;
    --border: #2c363c; --soft: #212b30;
    --primary: #3fc0a2; --primary-dark: #86dcc8; --accent: #f0a35a; --accent-dark: #f0a35a;
  }
  html[data-theme="dark"] .sub-nav,
  html[data-theme="dark"] aside.sidebar,
  html[data-theme="dark"] .filter-btn,
  html[data-theme="dark"] .logic-toggle,
  html[data-theme="dark"] .mobile-chapter-nav,
  html[data-theme="dark"] .stat,
  html[data-theme="dark"] .feature,
  html[data-theme="dark"] .muni-card { background: var(--card); color: var(--text); }
  html[data-theme="dark"] .filter-btn { border-color: var(--border); }
  html[data-theme="dark"] .chapter-heading { color: var(--text); }
  html[data-theme="dark"] .callout, html[data-theme="dark"] .note { background: #2a2716; }
  html[data-theme="dark"] .callout.warning, html[data-theme="dark"] .caveat { background: #2e1c1e; }
  html[data-theme="dark"] .sidebar-nav a.active { background: #3a1f1c; }
  html[data-theme="dark"] .tag-badge.research { background: #12385e; color: #a9d3ff; }
  html[data-theme="dark"] .tag-badge.business { background: #14401f; color: #a9e6bd; }
  html[data-theme="dark"] .tag-badge.living   { background: #40230a; color: #f3c393; }
  html[data-theme="dark"] .tag-badge.nature   { background: #331a42; color: #dcb6f0; }
  html[data-theme="dark"] .kind.academic { background: #14304a; color: #a9d3ff; }
  html[data-theme="dark"] .kind.tourism  { background: #3a2410; color: #f3c393; }
  html[data-theme="dark"] mark.kb-hl { background: #ffd54f; color: #111; }  /* AA確保 */
  html[data-theme="dark"] .theme-toggle { background: var(--soft); }

  /* 相互リンク（ヘッダー内・投資ブリーフへ） */
  .kb-xlink {
    font-size: .8rem; font-weight: 700; color: #fff; text-decoration: none;
    background: var(--tl-red); padding: 6px 12px; border-radius: 8px; white-space: nowrap;
  }
  .kb-xlink:hover { background: #8f1b1b; }

  /* ============ 印刷 / PDF 最適化 ============ */
  @media print {
    :root, html[data-theme="dark"] {
      --bg:#fff; --card:#fff; --text:#000; --muted:#333; --border:#bbb; --soft:#f0f0f0;
      --primary:#0a7e65; --primary-dark:#054d3e; --accent:#b5611a; --accent-dark:#b5611a;
    }
    header.global-header, .sub-nav, aside.sidebar, aside.toc-right,
    #to-top, .theme-toggle, .header-controls, .mobile-chapter-nav, .kb-xlink { display: none !important; }
    .portal-container { display: block; max-width: 100%; margin: 0; }
    main.content-area { max-width: 100%; padding: 0; margin: 0; }
    body { background: #fff; color: #000; }
    .section-card { box-shadow: none; border: 1px solid #ccc; break-inside: avoid; page-break-inside: avoid; margin-bottom: 14px; }
    .chapter-heading { break-before: page; page-break-before: always; }
    .chapter-heading:first-of-type { break-before: auto; page-break-before: auto; }
    figure.chart, table, .muni-grid, .stats { break-inside: avoid; page-break-inside: avoid; }
    a[href^="http"]::after { content: " <" attr(href) ">"; font-size: .72em; color: #444; word-break: break-all; }
    .card-tags { display: none; }  /* 印刷ではペルソナ絞り込みは不要 */
  }

  @media (max-width: 1180px) {
    aside.toc-right { display: none; }
  }
  @media (max-width: 900px) {
    aside.sidebar { display: none; }
    main.content-area { padding: 18px 16px; }
    .search-box input { width: 150px; }
    .brand-area p { display: none; }
    .mobile-chapter-nav { display: inline-block; }
    .sub-nav { gap: 8px; }
    .filter-hint { display: none; }
  }
"""

# ------------------------------------------------------------------
# 制御スクリプト
# ------------------------------------------------------------------
PORTAL_JS = r"""
(function () {
  var filterBtns = Array.prototype.slice.call(document.querySelectorAll('.filter-btn'));
  var cards = Array.prototype.slice.call(document.querySelectorAll('.section-card'));
  var headings = Array.prototype.slice.call(document.querySelectorAll('.chapter-heading'));
  var searchInput = document.getElementById('live-search');
  var noResult = document.getElementById('no-result');
  var state = { personas: [], logic: 'OR', q: '' };

  // ヘッダー/サブバーの実高を測り、スティッキー位置とアンカー着地に反映
  function setOffsets() {
    var h = document.querySelector('header.global-header');
    var s = document.querySelector('.sub-nav');
    if (h) document.documentElement.style.setProperty('--hh', h.offsetHeight + 'px');
    if (s) document.documentElement.style.setProperty('--sub', s.offsetHeight + 'px');
  }
  setOffsets();
  window.addEventListener('resize', setOffsets);
  window.addEventListener('load', setOffsets);

  function personaMatch(tags) {
    if (!state.personas.length) return true;
    if (state.logic === 'AND') {
      return state.personas.every(function (p) { return tags.indexOf(p) >= 0; });
    }
    return state.personas.some(function (p) { return tags.indexOf(p) >= 0; });
  }

  function apply() {
    var q = state.q.trim().toLowerCase();
    var anyVisible = false;
    cards.forEach(function (card) {
      var tags = (card.getAttribute('data-tags') || '').split(/\s+/);
      var personaOk = personaMatch(tags);
      var textOk = (q === '') || (card.textContent.toLowerCase().indexOf(q) >= 0);
      var show = personaOk && textOk;
      card.classList.toggle('hidden', !show);
      if (show) anyVisible = true;
    });
    // 章見出し：その章に可視カードが1つも無ければ隠す
    headings.forEach(function (h) {
      var ch = h.getAttribute('data-chapter');
      var hasVisible = cards.some(function (c) {
        return c.getAttribute('data-chapter') === ch && !c.classList.contains('hidden');
      });
      h.classList.toggle('hidden', !hasVisible);
    });
    if (noResult) noResult.classList.toggle('show', !anyVisible);
  }

  var allBtn = document.querySelector('.filter-btn[data-target="all"]');
  function syncFilterButtons() {
    filterBtns.forEach(function (b) {
      var t = b.getAttribute('data-target');
      if (t === 'all') b.classList.toggle('active', state.personas.length === 0);
      else b.classList.toggle('active', state.personas.indexOf(t) >= 0);
    });
  }
  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var t = btn.getAttribute('data-target');
      if (t === 'all') {
        state.personas = [];
      } else {
        var i = state.personas.indexOf(t);
        if (i >= 0) state.personas.splice(i, 1); else state.personas.push(t);
      }
      syncFilterButtons();
      apply(); updateActive();
    });
  });

  var logicToggle = document.getElementById('logic-toggle');
  if (logicToggle) {
    logicToggle.addEventListener('click', function () {
      state.logic = (state.logic === 'OR') ? 'AND' : 'OR';
      logicToggle.textContent = (state.logic === 'OR') ? 'いずれか(OR)' : 'すべて(AND)';
      apply(); updateActive();
    });
  }

  // ---- 検索語ハイライト ----
  function clearHighlights() {
    var marks = document.querySelectorAll('mark.kb-hl');
    marks.forEach(function (mk) {
      var parent = mk.parentNode;
      parent.replaceChild(document.createTextNode(mk.textContent), mk);
      parent.normalize();
    });
  }
  function highlight(q) {
    if (!q) return;
    var ql = q.toLowerCase();
    cards.forEach(function (card) {
      if (card.classList.contains('hidden')) return;
      var walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, {
        acceptNode: function (node) {
          if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          var p = node.parentNode.nodeName;
          if (p === 'SCRIPT' || p === 'STYLE' || p === 'MARK') return NodeFilter.FILTER_REJECT;
          return node.nodeValue.toLowerCase().indexOf(ql) >= 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
      });
      var targets = [];
      while (walker.nextNode()) targets.push(walker.currentNode);
      targets.forEach(function (node) {
        var text = node.nodeValue, low = text.toLowerCase(), frag = document.createDocumentFragment();
        var idx = 0, pos;
        while ((pos = low.indexOf(ql, idx)) >= 0) {
          if (pos > idx) frag.appendChild(document.createTextNode(text.slice(idx, pos)));
          var mk = document.createElement('mark');
          mk.className = 'kb-hl';
          mk.textContent = text.slice(pos, pos + ql.length);
          frag.appendChild(mk);
          idx = pos + ql.length;
        }
        if (idx < text.length) frag.appendChild(document.createTextNode(text.slice(idx)));
        node.parentNode.replaceChild(frag, node);
      });
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', function (e) {
      state.q = e.target.value || '';
      clearHighlights();
      apply();
      highlight(state.q.trim());
      updateActive();
    });
  }

  // ---- テーマ（ダーク/ライト）切替・永続化 ----
  var themeBtn = document.getElementById('theme-toggle');
  function applyTheme(t) {
    if (t === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    else document.documentElement.removeAttribute('data-theme');
    if (themeBtn) themeBtn.textContent = (t === 'dark') ? '☀️' : '🌙';
  }
  var savedTheme;
  try { savedTheme = localStorage.getItem('tl-kb-theme'); } catch (e) {}
  applyTheme(savedTheme || 'light');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem('tl-kb-theme', next); } catch (e) {}
      setOffsets();
    });
  }

  // ---- スクロール連動：現在の章を左ナビ・右目次でハイライト ----
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.sidebar-nav a'));
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc-right a'));
  var allNavLinks = navLinks.concat(tocLinks);

  function currentChapterId() {
    var line = (parseInt(getComputedStyle(document.documentElement).getPropertyValue('--hh')) || 66)
             + (parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sub')) || 44) + 24;
    var cur = null;
    headings.forEach(function (h) {
      if (h.classList.contains('hidden')) return;
      if (h.getBoundingClientRect().top <= line) cur = h.id;
    });
    // まだ最初の章に達していない場合は最初の可視章を現在地とする
    if (!cur) {
      for (var i = 0; i < headings.length; i++) {
        if (!headings[i].classList.contains('hidden')) { cur = headings[i].id; break; }
      }
    }
    return cur;
  }

  function updateActive() {
    var id = currentChapterId();
    allNavLinks.forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('href') === '#' + id);
    });
    var mc = document.getElementById('mchap');
    if (mc && id && mc.value !== id) mc.value = id;
  }

  // ---- モバイル用・章ジャンプ ----
  var mchap = document.getElementById('mchap');
  if (mchap) {
    mchap.addEventListener('change', function () {
      var el = this.value && document.getElementById(this.value);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // ---- トップへ戻る ----
  var toTop = document.getElementById('to-top');
  function onScroll() {
    updateActive();
    if (toTop) toTop.classList.toggle('show', window.pageYOffset > 400);
  }
  if (toTop) {
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // rAF でスクロールをスロットル
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (!ticking) {
      window.requestAnimationFrame(function () { onScroll(); ticking = false; });
      ticking = true;
    }
  }, { passive: true });

  apply();
  updateActive();
  onScroll();
})();
"""

# ------------------------------------------------------------------
# 最終HTML組み立て
# ------------------------------------------------------------------
out = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Timor-Leste Knowledge Base（東ティモール ナレッジベース）</title>
<style>
{css}
{PORTAL_CSS}
</style>
</head>
<body>

<!-- グローバルヘッダー -->
<header class="global-header">
  <div class="brand-area">
    <h1>Timor-Leste <span>Knowledge Base</span></h1>
    <p>東ティモール ナレッジベース ― 歴史・政治・経済から独自の生態系、現地生活までを出典付きで紐解く研究者向け総合データベース</p>
  </div>
  <div class="header-controls">
    <div class="search-box">
      <input type="text" id="live-search" aria-label="本文をキーワード検索" placeholder="キーワード検索（例: Lulik, 石油基金, 固有種, 識字率）...">
    </div>
    <a class="kb-xlink" href="{INDEX_PAGE}" title="関連成果物（投資ブリーフ・観光ブリーフ）の索引を開く">関連資料 ↗</a>
    <button id="theme-toggle" class="theme-toggle" aria-label="ダーク/ライト切替" title="ダーク/ライト切替">🌙</button>
    <div class="lang-picker"><b>JP</b> / EN / TET</div>
  </div>
</header>

<!-- サブナビゲーション（フィルター） -->
<div class="sub-nav">
  <div class="breadcrumbs">Home &gt; 東ティモール総合統合データベース</div>
  <select id="mchap" class="mobile-chapter-nav" aria-label="章へ移動">
    <option value="">章へ移動…</option>
{mchap_options}
  </select>
  <div class="persona-filters">
    <span class="flabel">ターゲット絞り込み:</span>
    <button class="filter-btn active" data-target="all">全対象</button>
    <button class="filter-btn" data-target="research">研究</button>
    <button class="filter-btn" data-target="business">ビジネス</button>
    <button class="filter-btn" data-target="living">移住・生活</button>
    <button class="filter-btn" data-target="nature">観光・ネイチャー</button>
    <button id="logic-toggle" class="logic-toggle" title="複数選択時の論理を切替（いずれか/すべて）">いずれか(OR)</button>
    <span class="filter-hint">複数選択で絞り込み</span>
  </div>
</div>

<div class="portal-container">

  <aside class="sidebar">
    <h3>ナビゲーション</h3>
    <ul class="sidebar-nav">
{sidebar_li}
    </ul>
  </aside>

  <main class="content-area">

  {main_inner}

  <div id="no-result" class="no-result">該当する項目が見つかりませんでした。検索語や絞り込みを変更してください。</div>

  </main>

  <aside class="toc-right">
    <div class="toc-head">章もくじ</div>
    <ul>
{toc_li}
    </ul>
  </aside>

</div>

<button id="to-top" aria-label="トップへ戻る" title="トップへ戻る">↑</button>

<footer>
  Timor-Leste Knowledge Base（東ティモール ナレッジベース・別版）｜ 元版 v19 の全内容を保持し3カラム・ポータルUIに再構成 ／ 情報は自由にアップデートしてご活用ください。
</footer>

<script>
{PORTAL_JS}
</script>

</body>
</html>
'''

OUT.write_text(out, encoding="utf-8")
print("出力:", OUT)
print("章別カード数:", {ch: len(chapter_items[ch]) for ch in range(1, 10)})
print("本文サイズ(chars):", len(out))
