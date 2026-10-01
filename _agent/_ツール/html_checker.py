#!/usr/bin/env python3
"""
html_checker.py — Claudeプロジェクト HTML品質チェッカー（汎用・静的）

使い方:
    python _ツール/html_checker.py <htmlファイルのパス>
    python _ツール/html_checker.py <htmlファイルのパス> --strict   # WARN も失敗扱い

終了コード:
    0 = FAIL 0件 (WARNは問わない)
    1 = FAIL 1件以上（またはstrictモードでWARN1件以上）

チェック内容:
    [ブロッカー] パース可能・外部CDN/fetch依存なし・charset宣言・ID重複なし・内部リンク解決・base64 PNG デコード健全性
    [警告]       CSS色ハードコード・版番号一元管理・<title>・viewport・lang属性・title/h1乖離・console.log残留・未接続data-*セレクタ・版付き_vN.html直リンク
    [情報]       ファイルサイズ・ID数・リンク数・style件数

背景:
    ClaudeCodeでHTMLを作成する際、以下の経験則からルールを抽出してチェックする。
    - v39.23: 図版を追加したが既存の図2と重複 → ID重複・内容重複を事前検知
    - v39.3:  フッターの版番号が"v34"のままハードコード → 版番号の一元管理チェック
    - v39:    ダークモード追加時にハードコード明色130箇所超を修正 → CSS色チェック
    - 東ティモールKB等: file://でブラウザ確認不可 → 静的チェックで補完
"""

import sys
import re
import os
from html.parser import HTMLParser
from collections import Counter

# Windowsのcp932コンソールでも動くようにUTF-8で出力する
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp932", "cp936", "mbcs"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def _c(text, code):
    """ANSI カラーコード（TTYのときだけ適用）"""
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

GREEN, YELLOW, RED, BOLD, DIM = "32", "33", "31", "1", "2"

# コンソールで確実に出せる記号
SYM_OK   = "[OK]"
SYM_WARN = "[△]"
SYM_FAIL = "[NG]"
SYM_INFO = "[i]"


class Results:
    def __init__(self):
        self.items = []

    def add(self, name, passed, level="FAIL", detail=""):
        self.items.append({"name": name, "passed": passed, "level": level, "detail": detail})
        if passed:
            sym, col = SYM_OK, GREEN
        elif level == "WARN":
            sym, col = SYM_WARN, YELLOW
        else:
            sym, col = SYM_FAIL, RED
        line = f"  {_c(sym, col)} {name}"
        if not passed and detail:
            line += f"\n      {_c(detail, DIM)}"
        print(line)
        return passed

    def fails(self):
        return sum(1 for r in self.items if not r["passed"] and r["level"] == "FAIL")

    def warns(self):
        return sum(1 for r in self.items if not r["passed"] and r["level"] == "WARN")


class HTMLAnalyzer(HTMLParser):
    """HTMLを1パスで解析してIDとリンクとスタイルを収集する"""

    def __init__(self):
        super().__init__()
        self.ids = []
        self.internal_hrefs = []    # href="#xxx" の xxx 部分
        self.ext_scripts = []       # <script src="https://...">
        self.ext_links = []         # <link href="https://...">
        self.style_blocks = []      # <style>...</style> の中身
        self.inline_styles = []     # style="..." の中身
        self.title = ""
        self.h1s = []
        self._cur_tag = None
        self._style_buf = ""
        self.error = None
        self.has_charset = False
        self.has_viewport = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self._cur_tag = tag

        if "id" in d:
            self.ids.append(d["id"])
        if tag == "meta":
            if d.get("charset"):
                self.has_charset = True
            elif d.get("http-equiv", "").lower() == "content-type" and "charset=" in d.get("content", "").lower():
                self.has_charset = True
            elif d.get("name", "").lower() == "viewport":
                self.has_viewport = True
        if tag == "a" and "href" in d:
            h = d["href"]
            if h.startswith("#") and len(h) > 1:
                self.internal_hrefs.append(h[1:])
        if tag == "script" and "src" in d and d["src"].startswith("http"):
            self.ext_scripts.append(d["src"])
        if tag == "link" and "href" in d:
            href = d["href"]
            if href.startswith("http"):
                self.ext_links.append(href)
        if "style" in d:
            self.inline_styles.append(d["style"])
        if tag == "style":
            self._style_buf = ""

    def handle_endtag(self, tag):
        if tag == "style":
            self.style_blocks.append(self._style_buf)
            self._style_buf = ""
        self._cur_tag = None

    def handle_data(self, data):
        if self._cur_tag == "title":
            self.title += data
        elif self._cur_tag == "h1":
            self.h1s.append(data.strip())
        elif self._cur_tag == "style":
            self._style_buf += data


def _parse(html):
    a = HTMLAnalyzer()
    try:
        a.feed(html)
    except Exception as e:
        a.error = str(e)
    return a


def _check_hardcoded_colors(css_blocks, inline_styles):
    """
    CSSの色ハードコードを検出する。
    CSS変数定義 (--name: #hex) と コメントは除外してから判定する。
    """
    all_css = "\n".join(css_blocks) + "\n" + "\n".join(inline_styles)
    # CSS変数定義を除去（--変数名: 値; の形式）
    no_vars = re.sub(r"--[\w-]+\s*:[^;{}]+", "", all_css)
    # コメントを除去
    no_vars = re.sub(r"/\*.*?\*/", "", no_vars, flags=re.DOTALL)
    # color系プロパティにリテラルの色値が使われていないかチェック
    hits = re.findall(
        r"(?:^|[\s;{,])(?:color|background(?:-color)?|border(?:-color)?|"
        r"fill|stroke|outline-color)\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\s*\([^)]+\))",
        no_vars,
        re.IGNORECASE | re.MULTILINE,
    )
    return hits


def _check_version_management(html):
    """
    版番号の一元管理チェック。
    JS定数(VERSION/KB_VERSION等)で管理されているかを確認する。
    """
    has_const = bool(
        re.search(r"(?:window\.|const\s+|let\s+|var\s+)(?:KB_)?VERSION\s*=\s*[\"']v?\d", html)
    )
    # 版番号らしきパターンを検出（"v39.25" "v5" など）
    raw_versions = re.findall(r'["\']v\d+(?:\.\d+)*["\']', html)
    unique_versions = list(dict.fromkeys(raw_versions))
    return has_const, len(raw_versions), unique_versions


def _count_console_logs(html):
    """インラインスクリプト内の console.log 件数を数える（コメント行は除外）"""
    scripts = re.findall(r'<script(?:[^>]*)>(.*?)</script>', html, re.DOTALL)
    count = 0
    for script in scripts:
        cleaned = re.sub(r'//[^\n]*', '', script)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        count += len(re.findall(r'console\.log\s*\(', cleaned))
    return count


def _check_dangling_data_selectors(html):
    """
    JS内の querySelector(All)('[data-xxx]') のうち、その属性が本文マークアップに
    1件も存在しないものを返す（「書いたが繋がっていない」空回りセレクタの検出）。
    ※ JSで動的に付与する属性は本文に無いため偽陽性になりうる（WARN止まり）。
    """
    scripts = "\n".join(re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL))
    markup = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    sels = re.findall(
        r'querySelector(?:All)?\s*\(\s*[\'"]([^\'"]*\[data-[\w-]+\][^\'"]*)[\'"]', scripts)
    dangling = []
    for sel in sels:
        for attr in re.findall(r'\[(data-[\w-]+)', sel):
            # マークアップ側に data-xxx 属性が使われているか（= や > や空白が続く）
            if not re.search(re.escape(attr) + r'(?:[\s=\]>])', markup):
                dangling.append(attr)
    return list(dict.fromkeys(dangling))


def _check_base64_images(html):
    """
    data:image/...;base64 の埋め込み画像をデコードし、
    PNGはIDATのzlibデータが完全に復号できるかを検証する（FAIL）。
    全体書き直し時のバイナリ破損検出。v34〜v39.35の1.5ヶ月潜伏事例に基づく。
    """
    import base64, zlib
    broken = []
    for m in re.finditer(r'data:(image/[\w+]+);base64,([A-Za-z0-9+/=\s]{20,})', html):
        mime = m.group(1)
        try:
            raw = base64.b64decode(m.group(2).replace('\n', '').replace(' ', ''))
        except Exception as e:
            broken.append(f"{mime}: base64デコード失敗 ({e})")
            continue
        if mime == "image/png":
            if len(raw) < 8 or raw[:8] != b'\x89PNG\r\n\x1a\n':
                broken.append("image/png: PNGシグネチャ不正（バイナリ破損）")
                continue
            idat = b''
            pos = 8
            while pos + 12 <= len(raw):
                length = int.from_bytes(raw[pos:pos+4], 'big')
                ctype = raw[pos+4:pos+8]
                if ctype == b'IDAT':
                    idat += raw[pos+8:pos+8+length]
                elif ctype == b'IEND':
                    break
                pos += 12 + length
            if idat:
                try:
                    zlib.decompress(idat)
                except zlib.error as e:
                    broken.append(f"image/png: IDATのzlibデータ破損 ({e})")
    return broken


def _check_versioned_cross_links(html):
    """
    href="xxx_vN.html" のような版付きHTMLへの直リンクを検出する（WARN）。
    改訂時にリンクが腐る原因になるため、_latestスタブ経由を推奨。
    """
    hits = re.findall(
        r'href\s*=\s*["\']([^"\'#?]*_v\d+(?:\.\d+)*\.html)["\']',
        html,
        re.IGNORECASE,
    )
    return list(dict.fromkeys(hits))


def _title_h1_match(title, h1s):
    """
    <title> と <h1> の内容が大幅に乖離していないかを確認する。
    共通の単語（3文字以上）が1つもなければ不一致とみなす（Rule H 対応）。
    """
    if not title.strip() or not h1s:
        return True  # どちらかが空なら比較不能 → 他チェックに委ねる
    h1 = h1s[0]
    title_words = set(w.lower() for w in re.findall(r'\w{3,}', title))
    h1_words = set(w.lower() for w in re.findall(r'\w{3,}', h1))
    if not title_words or not h1_words:
        return True
    return bool(title_words & h1_words)


def run(path, strict=False):
    with open(path, encoding="utf-8") as f:
        html = f.read()

    print(f"\n{_c('HTML品質チェック', BOLD)}: {os.path.basename(path)}")
    size_kb = os.path.getsize(path) / 1024
    print(f"  {_c(f'ファイルサイズ: {size_kb:,.1f} KB  ({len(html):,} 文字)', DIM)}\n")

    a = _parse(html)
    r = Results()

    # ──────────────────────────────────────────
    # ブロッカー: 必ずクリアすること
    # ──────────────────────────────────────────
    print(_c("【ブロッカー】", BOLD))

    # 1. HTMLパース可能
    r.add("HTMLパース可能", a.error is None, "FAIL",
          a.error[:100] if a.error else "")

    # 2. 外部CDN・fetch依存なし
    fetch_matches = re.findall(r'fetch\s*\(\s*["\']https?://', html)
    # フォントのみのlink（Googleフォント等）はWARNに落とすため分離
    font_only_links = [l for l in a.ext_links if "font" in l.lower()]
    real_ext = a.ext_scripts + [l for l in a.ext_links if l not in font_only_links] + fetch_matches
    r.add("外部CDN・fetch依存なし", len(real_ext) == 0, "FAIL",
          f"{len(real_ext)}件検出: " + ", ".join(str(e)[:50] for e in real_ext[:2]) if real_ext else "")

    # 3. charset 宣言（日本語コンテンツで文字化け防止）
    r.add('<meta charset="UTF-8"> が宣言済み', a.has_charset, "FAIL",
          '<meta charset="UTF-8"> を <head> 内の先頭付近に追加してください')

    # 4. IDの重複なし
    dup = [id_ for id_, n in Counter(a.ids).items() if n > 1]
    r.add("IDの重複なし", len(dup) == 0, "FAIL",
          f"重複ID {len(dup)}件: {', '.join(dup[:5])}" if dup else "")

    # 4. 内部リンク（#id）がすべて解決できる
    id_set = set(a.ids)
    broken = list(dict.fromkeys(h for h in a.internal_hrefs if h and h not in id_set))
    r.add("内部リンク（#id）がすべて解決", len(broken) == 0, "FAIL",
          f"{len(broken)}件の未解決: {', '.join(broken[:4])}" if broken else "")

    # 5. 埋め込みPNGのzlibデータが完全に復号できる（全体書き直し時のIDAT破損検出）
    img_broken = _check_base64_images(html)
    r.add("埋め込み画像（base64 PNG）のデコードが健全", len(img_broken) == 0, "FAIL",
          f"{len(img_broken)}件の破損: {'; '.join(img_broken[:2])}"
          "  →  全体書き直しによるバイナリ破損の疑い。差分編集（Rule E）で修正してください" if img_broken else "")

    # ──────────────────────────────────────────
    # 警告: 品質向上のために対処を推奨
    # ──────────────────────────────────────────
    print(f"\n{_c('【警告】', BOLD)}")

    # 5. CSS色のハードコードなし
    hc = _check_hardcoded_colors(a.style_blocks, a.inline_styles)
    r.add("CSS色はCSS変数で定義（ハードコードなし）", len(hc) == 0, "WARN",
          f"{len(hc)}件検出（例: {hc[0]}）  →  CSS変数 (--name) に移行してください" if hc else "")

    # 6. 版番号の一元管理
    has_const, ver_count, sample_vers = _check_version_management(html)
    if ver_count >= 3 and not has_const:
        r.add("版番号がJS定数で一元管理", False, "WARN",
              f"VERSION定数未検出（版番号パターンが{ver_count}か所: {', '.join(sample_vers[:3])}）"
              f"  →  window.VERSIONなどで一元管理してください")
    else:
        r.add("版番号がJS定数で一元管理", True, "WARN")

    # 7. <title>が存在し空でない
    r.add("<title>が存在し空でない", bool(a.title.strip()), "WARN",
          "<title>が未設定または空です")

    # 8. viewport meta（モバイル対応の前提）
    r.add('<meta name="viewport"> が設定済み', a.has_viewport, "WARN",
          '<meta name="viewport" content="width=device-width, initial-scale=1"> を追加してください')

    # 9. html[lang]の設定
    has_lang = bool(re.search(r'<html[^>]+lang\s*=\s*["\']', html, re.IGNORECASE))
    r.add('html要素に lang="" が設定済み', has_lang, "WARN",
          '<html lang="ja"> などを設定してください')

    # 10. <title> と <h1> の内容が大幅に乖離していない（Rule H）
    if not _title_h1_match(a.title, a.h1s):
        h1_sample = a.h1s[0][:40] if a.h1s else ""
        r.add("<title>と<h1>の内容が一致", False, "WARN",
              f'title="{a.title.strip()[:40]}" / h1="{h1_sample}"  →  Rule H: 表記を合わせてください')
    else:
        r.add("<title>と<h1>の内容が一致", True, "WARN")

    # 11. console.log の残留（デバッグコードの流出防止）
    clog_count = _count_console_logs(html)
    r.add("console.log が残留していない", clog_count == 0, "WARN",
          f"{clog_count}件検出  →  本番前に削除または console.debug に置換してください" if clog_count else "")

    # 12. 未接続の [data-*] セレクタ（書いたが繋がっていない空回りの検出）
    dangling = _check_dangling_data_selectors(html)
    r.add("querySelector('[data-*]') が本文に接続されている", len(dangling) == 0, "WARN",
          f"未接続の属性 {len(dangling)}件: {', '.join(dangling[:4])}"
          "  →  マークアップに無い＝空回りの可能性（JSで動的付与しているなら無視可）" if dangling else "")

    # 13. 版付きHTMLへの直リンク（改訂でリンクが腐る恐れ）
    ver_links = _check_versioned_cross_links(html)
    r.add("版付き _vN.html への直リンクがない", len(ver_links) == 0, "WARN",
          f"{len(ver_links)}件検出: {', '.join(ver_links[:3])}"
          "  →  Rule G: 改訂時にリンクが切れます。_latestスタブ経由に変更してください" if ver_links else "")

    # ──────────────────────────────────────────
    # 情報
    # ──────────────────────────────────────────
    print(f"\n{_c('【情報】', DIM)}")
    title_str = a.title.strip()[:70] or "(未設定)"
    h1_str = ", ".join(h[:30] for h in a.h1s[:2]) or "(なし)"
    print(f"  {SYM_INFO} <title>       : {title_str}")
    print(f"  {SYM_INFO} <h1>          : {h1_str}")
    print(f"  {SYM_INFO} ID 総数       : {len(a.ids)}")
    print(f"  {SYM_INFO} 内部リンク数  : {len(a.internal_hrefs)}")
    print(f"  {SYM_INFO} <style>ブロック: {len(a.style_blocks)}  インラインstyle: {len(a.inline_styles)}")

    if a.ext_scripts or font_only_links:
        print(f"  {SYM_WARN} 外部リソース（確認推奨）: {', '.join((a.ext_scripts + font_only_links)[:3])}")

    # ──────────────────────────────────────────
    # サマリー
    # ──────────────────────────────────────────
    fails, warns = r.fails(), r.warns()
    print(f"\n{'─' * 55}")
    if fails == 0 and warns == 0:
        print(_c(f"  {SYM_OK} 全チェック PASS", GREEN))
    elif fails == 0 and not strict:
        print(_c(f"  {SYM_WARN} WARN {warns}件（FAIL なし） — /ship 可", YELLOW))
    elif fails == 0 and strict:
        print(_c(f"  {SYM_WARN} WARN {warns}件（strict モードで失敗扱い）", RED))
    else:
        print(_c(f"  {SYM_FAIL} FAIL {fails}件 / WARN {warns}件 — 修正してから /ship してください", RED))
    print(f"{'─' * 55}\n")

    if strict:
        return fails + warns
    return fails


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    path = args[0]
    strict = "--strict" in args

    if not os.path.exists(path):
        print(f"エラー: ファイルが見つかりません: {path}")
        sys.exit(1)

    sys.exit(1 if run(path, strict=strict) > 0 else 0)
