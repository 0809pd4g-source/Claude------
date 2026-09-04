#!/usr/bin/env python3
"""
make_offline.py
Gemini版しおりHTMLの外部CDN依存をインライン化し、オフライン対応版を生成する。

処理内容:
  1. Tailwind CDN JS       → <script> インライン
  2. Font Awesome CSS+WOFF2 → base64 データURIでインライン
  3. Google Fonts CDN      → 削除 (Noto Sans JP は日本デバイスに標準搭載)
  4. placehold.co アイコン → apple-touch-icon タグごと除去 (PWAアイコン用途のみ)

入力: 02_output/20260901_新婚旅行しおり_v1.html
出力: 02_output/20260901_新婚旅行しおり_v2.html
"""

import re
import base64
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
INPUT  = BASE_DIR / "02_output" / "20260901_新婚旅行しおり_v1.html"
OUTPUT = BASE_DIR / "02_output" / "20260901_新婚旅行しおり_v2.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def fetch_text(url: str) -> str:
    return fetch(url).decode("utf-8")

def to_data_uri(content: bytes, mime: str) -> str:
    b64 = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{b64}"

# ──────────────────────────────────────────────
print("=== オフライン化スクリプト開始 ===\n")
html = INPUT.read_text(encoding="utf-8")

# ── 1. Tailwind CDN JS をインライン化 ─────────────────────────
print("1. Tailwind CDN JS をダウンロード中...")
tw_js = fetch_text("https://cdn.tailwindcss.com")
html = html.replace(
    '<script src="https://cdn.tailwindcss.com"></script>',
    f"<script>\n{tw_js}\n</script>",
)
print(f"   完了 ({len(tw_js):,} chars)\n")

# ── 2. Font Awesome CSS + フォントをインライン化 ───────────────
print("2. Font Awesome CSS をダウンロード中...")
FA_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
FA_WEBFONTS_BASE = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/"
fa_css = fetch_text(FA_CSS_URL)

# CSS内のフォントURLを抽出（woff2のみ対象）
font_files = list(dict.fromkeys(
    re.findall(r"\.\./webfonts/([^\s)]+\.woff2)", fa_css)
))
print(f"   フォントファイル ({len(font_files)}件): {font_files}\n")

for font_file in font_files:
    font_url = FA_WEBFONTS_BASE + font_file
    print(f"   ダウンロード: {font_file}")
    font_bytes = fetch(font_url)
    data_uri = to_data_uri(font_bytes, "font/woff2")
    fa_css = fa_css.replace(
        f"url(../webfonts/{font_file})",
        f"url({data_uri})",
    )
    print(f"   → {len(font_bytes):,} bytes → base64 {len(data_uri):,} chars")

# ttf の行は残っていると外部URLになるため行ごと削除
fa_css = re.sub(r",?\s*url\(\.\./webfonts/[^)]+\.ttf\)\s*format\(['\"]truetype['\"]\)", "", fa_css)

# CDN <link> タグをインライン <style> に置換
fa_link_tag = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com'
               '/ajax/libs/font-awesome/6.4.0/css/all.min.css">')
html = html.replace(fa_link_tag, f"<style>\n{fa_css}\n</style>")
print("\n   Font Awesome インライン化 完了\n")

# ── 3. Google Fonts CDN を除去しシステムフォントへ差し替え ──────
print("3. Google Fonts CDN タグを除去してシステムフォント化...")
# preconnect / stylesheet タグをすべて除去
html = re.sub(
    r'[ \t]*<link[^>]*(fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>\n?',
    "",
    html,
)
# システムフォント定義を <head> 末尾に追加
system_font_css = """\
<style>
  /* Google Fonts CDN 除去 — システムフォントで代替 */
  /* Noto Sans JP: iOS/Android/Windows 日本語環境に標準搭載 */
  /* Amiri: アラビア文字はデバイス標準アラビアフォントで代替 */
  body {
    font-family: 'Noto Sans JP', 'ヒラギノ角ゴ ProN', 'Hiragino Kaku Gothic ProN',
                 'Meiryo', 'メイリオ', sans-serif;
  }
  .font-arabic {
    font-family: 'Amiri', 'Traditional Arabic', 'Arial Unicode MS', serif;
  }
</style>"""
html = html.replace("</head>", system_font_css + "\n</head>")
print("   完了\n")

# ── 4. placehold.co の apple-touch-icon を除去 ─────────────────
print("4. 外部画像 (placehold.co) apple-touch-icon タグを除去...")
html = re.sub(
    r'[ \t]*<link[^>]*apple-touch-icon[^>]*placehold\.co[^>]*>\n?',
    "",
    html,
)
print("   完了\n")

# ── 出力 ────────────────────────────────────────────────────────
OUTPUT.write_text(html, encoding="utf-8")
size_bytes = OUTPUT.stat().st_size
print(f"=== 完了 ===")
print(f"出力: {OUTPUT.name}")
print(f"ファイルサイズ: {size_bytes:,} bytes ({size_bytes / 1024 / 1024:.2f} MB)")

# 残存する外部URL確認
remaining = re.findall(r'(https?://[^\s\'"<>]+)', html)
external = [u for u in remaining if not u.startswith("data:")]
if external:
    print(f"\n⚠️ 残存外部URL ({len(external)}件):")
    for u in sorted(set(external)):
        print(f"  {u}")
else:
    print("\n✅ 外部URL: なし（完全オフライン対応）")
