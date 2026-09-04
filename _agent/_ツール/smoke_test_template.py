#!/usr/bin/env python3
"""
smoke_test_template.py — プロジェクト固有スモークテスト テンプレート

使い方:
    1. このファイルを 03_scripts/smoke_test.py としてコピーする
    2. HTML_PATH・REQUIRED_IDS・assertions を書き換える
    3. python 03_scripts/smoke_test.py

このテンプレートの目的:
    - HTMLのJSロジック（計算エンジン・状態管理）をブラウザなしでユニットテストする
    - ClaudeCodeのブラウザペインはfile://が使えないため、
      計算が正しいかの確認は dukpy（JSエンジン）で行う
    - ブラウザが必要な見た目テストは Layer 2（ブラウザ統合テスト）で行う

依存:
    pip install dukpy   （JSエンジン。なければ構造テストのみ実行）

テスト層の位置づけ:
    Layer 1: 静的チェック   → _ツール/html_checker.py     （常に実行）
    Layer 2: ブラウザテスト → CLAUDE.md の検証プロトコル  （UI変更時）
    Layer 3: スモークテスト → 本ファイル（プロジェクト固有）（計算系HTMLのみ）
"""

import sys
import re
import os

# ──────────────────────────────────────────────────────────────
# 設定: プロジェクトごとに書き換える
# ──────────────────────────────────────────────────────────────

# テスト対象のHTMLファイルパス（このスクリプトからの相対パス）
HTML_PATH = "../02_output/YYYYMMDD_プロジェクト名_最新版.html"

# 必ず存在すべきセクションID（構造テスト）
REQUIRED_IDS = [
    # 例: "summary", "table-main", "graph-1"
]

# JSで検証すべき計算の入力→期待値ペア（計算エンジンテスト）
# ライフプランシミュレーター例:
# CALC_ASSERTIONS = [
#     {
#         "desc": "年収800万・配偶者600万の定年時資産がプラスであること",
#         "setup": "CONFIG.income = 800; CONFIG.spouseIncome = 600;",
#         "expr": "calcAssetAt(65)",
#         "check": lambda v: v > 0,
#         "label": "> 0万円"
#     }
# ]
CALC_ASSERTIONS = []

# ──────────────────────────────────────────────────────────────
# テスト実装（通常は変更不要）
# ──────────────────────────────────────────────────────────────

GREEN  = "\033[32m" if sys.stdout.isatty() else ""
YELLOW = "\033[33m" if sys.stdout.isatty() else ""
RED    = "\033[31m" if sys.stdout.isatty() else ""
BOLD   = "\033[1m"  if sys.stdout.isatty() else ""
RESET  = "\033[0m"  if sys.stdout.isatty() else ""


class SmokeTest:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def ok(self, desc):
        print(f"  {GREEN}✓{RESET} {desc}")
        self.passed += 1

    def fail(self, desc, detail=""):
        print(f"  {RED}✗{RESET} {desc}" + (f"\n      {RED}{detail}{RESET}" if detail else ""))
        self.failed += 1

    def skip(self, desc, reason):
        print(f"  {YELLOW}−{RESET} {desc}  ({reason})")
        self.skipped += 1

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'─' * 50}")
        if self.failed == 0:
            print(f"{GREEN}{BOLD}  結果: 異常なし{RESET}  "
                  f"({self.passed}/{total} PASS, {self.skipped} SKIP)")
        else:
            print(f"{RED}{BOLD}  結果: 異常あり{RESET}  "
                  f"({self.failed} FAIL, {self.passed} PASS, {self.skipped} SKIP)")
        print(f"{'─' * 50}\n")
        return self.failed


def _load_html(path):
    abs_path = os.path.join(os.path.dirname(__file__), path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"HTMLが見つかりません: {abs_path}")
    with open(abs_path, encoding="utf-8") as f:
        return f.read()


def _extract_script(html):
    """HTML中の最初の非CDN <script> ブロックを返す（JSエンジン投入用）"""
    scripts = re.findall(r'<script(?:[^>]*)>(.*?)</script>', html, re.DOTALL)
    inline = [s for s in scripts if s.strip()]
    return "\n".join(inline) if inline else ""


def test_structure(t: SmokeTest, html: str):
    """構造テスト: 必須IDの存在確認（dukpy不要）"""
    print(f"\n{BOLD}【構造テスト】{RESET}")
    if not REQUIRED_IDS:
        t.skip("必須IDチェック", "REQUIRED_IDS が未設定")
        return

    existing_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))
    for id_ in REQUIRED_IDS:
        if id_ in existing_ids:
            t.ok(f"#{id_} が存在")
        else:
            t.fail(f"#{id_} が存在しない", f"id=\"{id_}\" が見つかりません")


def test_calculations(t: SmokeTest, html: str):
    """計算テスト: JSエンジン（dukpy）で計算ロジックを直接実行"""
    print(f"\n{BOLD}【計算テスト】{RESET}")
    if not CALC_ASSERTIONS:
        t.skip("計算ロジックテスト", "CALC_ASSERTIONS が未設定")
        return

    try:
        import dukpy
    except ImportError:
        t.skip("計算ロジックテスト", "dukpy が未インストール（pip install dukpy）")
        return

    # DOMスタブ（最低限のwindow/document模倣）
    dom_stub = """
    var window = { localStorage: { getItem: function(){return null;}, setItem: function(){} } };
    var document = {
        getElementById: function(){ return { value: '', innerHTML: '', style: {}, addEventListener: function(){} }; },
        querySelector: function(){ return null; },
        querySelectorAll: function(){ return []; },
        addEventListener: function(){},
        body: { style: {} }
    };
    var console = { log: function(){}, warn: function(){}, error: function(){} };
    """

    js_source = _extract_script(html)
    if not js_source:
        t.fail("JSソース抽出", "HTMLにインラインscriptが見つかりません")
        return

    for assertion in CALC_ASSERTIONS:
        desc = assertion.get("desc", "テスト")
        setup = assertion.get("setup", "")
        expr  = assertion.get("expr", "true")
        check = assertion.get("check", lambda v: bool(v))
        label = assertion.get("label", "")
        try:
            full_js = dom_stub + js_source + "\n" + setup + "\nresult = " + expr + ";"
            ctx = dukpy.evaljs(full_js)
            val = dukpy.evaljs(dom_stub + js_source + "\n" + setup + "\n" + expr)
            if check(val):
                t.ok(f"{desc}  → {val} {label}")
            else:
                t.fail(f"{desc}", f"期待: {label}  実際: {val}")
        except Exception as e:
            t.fail(f"{desc}", f"JS実行エラー: {e}")


def test_no_js_errors(t: SmokeTest, html: str):
    """JSサイレントエラーの検出（dukpy）"""
    print(f"\n{BOLD}【JSエラー検出】{RESET}")
    try:
        import dukpy
    except ImportError:
        t.skip("JSエラー検出", "dukpy が未インストール")
        return

    dom_stub = """
    var window = { localStorage: { getItem: function(){return null;}, setItem: function(){} } };
    var document = {
        getElementById: function(){ return { value: '', innerHTML: '', style: {}, addEventListener: function(){} }; },
        querySelector: function(){ return null; },
        querySelectorAll: function(){ return []; },
        addEventListener: function(){},
        body: { style: {} }
    };
    var console = { log: function(){}, warn: function(){}, error: function(){} };
    """

    js_source = _extract_script(html)
    if not js_source:
        t.skip("JSエラー検出", "インラインscriptなし")
        return
    try:
        dukpy.evaljs(dom_stub + js_source)
        t.ok("JSソースがエラーなしで実行可能")
    except Exception as e:
        t.fail("JSソースにエラーあり", str(e)[:200])


# ──────────────────────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"{BOLD}スモークテスト: {os.path.basename(HTML_PATH)}{RESET}")

    try:
        html = _load_html(HTML_PATH)
    except FileNotFoundError as e:
        print(f"{RED}エラー: {e}{RESET}")
        sys.exit(1)

    t = SmokeTest()
    test_structure(t, html)
    test_no_js_errors(t, html)
    test_calculations(t, html)
    t.summary()

    sys.exit(1 if t.failed > 0 else 0)
