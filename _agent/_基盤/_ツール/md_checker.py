#!/usr/bin/env python3
"""
md_checker.py — Claudeプロジェクト Markdown品質チェッカー

使い方:
    # 成果物（02_output/*.md）のチェック
    python _agent/_基盤/_ツール/md_checker.py 02_output/YYYYMMDD_名称_vN.md

    # 管理文書のチェック（ファイル名で自動判定）
    python _agent/_基盤/_ツール/md_checker.py プロジェクト名/更新履歴.md
    python _agent/_基盤/_ツール/md_checker.py プロジェクト名/プロジェクト状況.md

    # strict モード: WARN も失敗扱い
    python _agent/_基盤/_ツール/md_checker.py <path> --strict

終了コード:
    0 = FAIL 0件
    1 = FAIL 1件以上（またはstrictモードでWARN1件以上）

チェック内容（成果物モード — 02_output/*.md 等）:
    [ブロッカー] ファイル名が YYYYMMDD_名称_vN.md 規約に準拠
    [警告]       見出しレベルが飛んでいない (h2->h4 等)
                 内部リンク ([text](path)) がすべて解決できる
                 相対日付表現がない（今週/先週/来週/翌月 等）

チェック内容（更新履歴.md）:
    [ブロッカー] （最新）が成果物の系統ごとに1行（全体で0行・同じ系統に2行以上は異常）
    [警告]       最新日付が1年以内

チェック内容（プロジェクト状況.md）:
    [警告]       変更履歴セクションに当年または前年の日付がある

チェック内容（CLAUDE.md / README* / GEMINI.md / AGENTS.md — 管理・設定文書）:
    命名規約(YYYYMMDD_名称_vN)は対象外。見出し飛び・内部リンク・相対日付のみ警告で確認。
"""

import sys
import re
import os
from datetime import date

# Windows cp932 コンソール対応
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp932", "cp936", "mbcs"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _c(text, code):
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


GREEN, YELLOW, RED, BOLD, DIM = "32", "33", "31", "1", "2"
SYM_OK   = "[OK]"
SYM_WARN = "[△]"
SYM_FAIL = "[NG]"
SYM_INFO = "[i]"


class Results:
    def __init__(self):
        self.items = []

    def add(self, name, passed, level="FAIL", detail=""):
        self.items.append({"name": name, "passed": passed, "level": level, "detail": detail})
        sym, col = (SYM_OK, GREEN) if passed else ((SYM_WARN, YELLOW) if level == "WARN" else (SYM_FAIL, RED))
        line = f"  {_c(sym, col)} {name}"
        if not passed and detail:
            line += f"\n      {_c(detail, DIM)}"
        print(line)
        return passed

    def fails(self):
        return sum(1 for r in self.items if not r["passed"] and r["level"] == "FAIL")

    def warns(self):
        return sum(1 for r in self.items if not r["passed"] and r["level"] == "WARN")


# ─────────────────────────────────────────
# 共通ヘルパー
# ─────────────────────────────────────────

def _mask_code_blocks(text):
    """コードブロック・インラインコードをマスク（チェックから除外）"""
    masked = re.sub(r'```.*?```', lambda m: '\n' * m.group().count('\n'), text, flags=re.DOTALL)
    masked = re.sub(r'`[^`\n]+`', lambda m: ' ' * len(m.group()), masked)
    return masked


def _extract_headings(text):
    """見出し行を (level, text) のリストで返す。コードブロック内は除外"""
    masked = _mask_code_blocks(text)
    headings = []
    for line in masked.splitlines():
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            headings.append((len(m.group(1)), m.group(2).strip()))
    return headings


def _check_heading_jumps(headings):
    """見出しレベルが2段以上飛んでいる箇所を (prev_level, new_level, heading_text) で返す"""
    jumps = []
    prev = 0
    for level, text in headings:
        if prev > 0 and level > prev + 1:
            jumps.append((prev, level, text[:30]))
        prev = level
    return jumps


def _extract_internal_links(text):
    """[text](path) 形式の内部リンク（http/https/mailto でないもの）のリストを返す"""
    masked = _mask_code_blocks(text)
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', masked)
    internal = []
    for label, href in links:
        anchor_stripped = href.split('#')[0].strip()
        if anchor_stripped and not anchor_stripped.startswith(('http://', 'https://', 'mailto:')):
            internal.append((label, anchor_stripped))
    return internal


def _check_relative_dates(text):
    """相対日付表現（今週/先週/来週/翌月等）の一覧を返す"""
    masked = _mask_code_blocks(text)
    hits = re.findall(r'(?:今週|先週|来週|今月|先月|来月|翌月|翌週|明日|昨日|明後日|一昨日)', masked)
    return hits


# ─────────────────────────────────────────
# ファイル名規約チェック
# ─────────────────────────────────────────

DELIVERABLE_NAME_RE = re.compile(r'^\d{8}_[^_].+_v\d+(?:\.\d+)*\.md$')


# ─────────────────────────────────────────
# 管理文書チェック
# ─────────────────────────────────────────

def _check_update_history(text):
    """
    更新履歴.md:
    - （最新）の総数と、同じ系統に（最新）が複数ある系統の一覧を返す
    - 日付の最大値 → latest_date を返す
    """
    # ★表の行（`|` で始まる行）だけを数える。
    #   2026-08-31：規約そのものを説明する地の文
    #   「最新版は **太字＋（最新）** で示す」を1件と数えてしまい、
    #   正しく1行だけ印を付けても必ずFAILになっていた。
    #   **検査が、正しい状態を不合格にしていた。**
    # 2026-10-03：成果物が複数系統（月次成果物＋常設ツール等）ある案件に対応し、
    #   系統（先頭列のファイル名から日付接頭辞・_vN・拡張子を除いた名前）ごとに数える。
    marked = [ln for ln in text.split('\n')
              if ln.lstrip().startswith('|') and '（最新）' in ln]
    series = {}
    for ln in marked:
        first = ln.strip().strip('|').split('|')[0]
        name = re.sub(r'[*\s]|（最新）', '', first)
        key = re.sub(r'^\d{8}_', '', re.sub(r'(_v\d+)?(\.[A-Za-z0-9]+)?$', '', name))
        series[key] = series.get(key, 0) + 1
    count = len(marked)
    dup = [k for k, n in series.items() if n > 1]
    return count, dup, _latest_date(text)


def _latest_date(text):

    # YYYY-MM-DD 形式の日付を全抽出
    raw_dates = re.findall(r'(\d{4}-\d{2}-\d{2})', text)
    latest_date = None
    if raw_dates:
        try:
            latest_date = max(date.fromisoformat(d) for d in raw_dates)
        except ValueError:
            pass

    return latest_date


def _check_project_status(text):
    """
    プロジェクト状況.md の変更履歴セクションに当年または前年の日付があるか。
    Returns: (bool, max_year_found | None)
    """
    # 見出し行だけに当てる（[^\n]*）。DOTALLで .* を使うと改行をまたいで本文中の「変更履歴」まで伸び、誤WARNになる
    m = re.search(r'##[^#][^\n]*変更履歴(.*?)(?=^##|\Z)', text, re.DOTALL | re.MULTILINE)
    section = m.group(1) if m else text  # セクションが見つからなければ全体を対象

    years = [int(y) for y in re.findall(r'(\d{4})-\d{2}-\d{2}', section)]
    if not years:
        return False, None
    max_year = max(years)
    return max_year >= date.today().year - 1, max_year


# ─────────────────────────────────────────
# モード判定
# ─────────────────────────────────────────

def _detect_mode(filename, path=None):
    if filename == "更新履歴.md":
        return "update_history"
    elif filename == "プロジェクト状況.md":
        return "project_status"
    elif filename in ("CLAUDE.md", "GEMINI.md", "AGENTS.md") or filename.startswith("README"):
        # 管理・設定文書は版番号が付かない。命名規約(YYYYMMDD_名称_vN)の対象外。
        return "config"
    # 命名規約(YYYYMMDD_名称_vN)は「02_output/ 配下の成果物」だけに適用する。
    # _agent/_基盤/_ツール/ 等に置く参照・ツール文書（ガイド・プロンプト類）は対象外（config扱い）。
    norm = (path or filename).replace("\\", "/")
    if "/02_output/" in norm or norm.startswith("02_output/"):
        return "deliverable"
    else:
        return "config"


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────

def run(path, strict=False):
    filename = os.path.basename(path)
    mode = _detect_mode(filename, path)

    with open(path, encoding="utf-8") as f:
        text = f.read()

    size_kb = os.path.getsize(path) / 1024
    mode_label = {"deliverable": "成果物", "update_history": "更新履歴", "project_status": "プロジェクト状況", "config": "管理・設定文書"}[mode]
    print(f"\n{_c('Markdown品質チェック', BOLD)} [{mode_label}]: {filename}")
    print(f"  {_c(f'ファイルサイズ: {size_kb:,.1f} KB  ({len(text):,} 文字)', DIM)}\n")

    r = Results()

    # ────────────────────────
    # 成果物モード
    # ────────────────────────
    if mode in ("deliverable", "config"):
        if mode == "deliverable":
            print(_c("【ブロッカー】", BOLD))

            r.add("ファイル名が YYYYMMDD_名称_vN.md 規約に準拠", bool(DELIVERABLE_NAME_RE.match(filename)), "FAIL",
                  f'"{filename}"  →  例: 20260801_調査レポート_v1.md')
        else:
            print(_c("【管理・設定文書：命名規約は対象外】", DIM))

        print(f"\n{_c('【警告】', BOLD)}")

        headings = _extract_headings(text)
        jumps = _check_heading_jumps(headings)
        r.add("見出しレベルが連続している（飛びなし）", len(jumps) == 0, "WARN",
              f"{len(jumps)}箇所で飛びあり: " +
              ", ".join(f"h{a}→h{b}「{t}」" for a, b, t in jumps[:3]) if jumps else "")

        base_dir = os.path.dirname(os.path.abspath(path))
        internal_links = _extract_internal_links(text)
        broken = [f"[{lbl}]({href})" for lbl, href in internal_links
                  if not os.path.exists(os.path.join(base_dir, href))]
        r.add("内部リンクがすべて解決できる", len(broken) == 0, "WARN",
              f"{len(broken)}件の未解決: {', '.join(broken[:3])}" if broken else "")

        # 設定・ルール文書（CLAUDE.md等）は「今日/明日/前日」をルール文言として使うため相対日付チェックの対象外。
        if mode != "config":
            rel_dates = _check_relative_dates(text)
            r.add("相対日付表現がない（絶対日付で記載）", len(rel_dates) == 0, "WARN",
                  f"{len(rel_dates)}件検出: {', '.join(list(dict.fromkeys(rel_dates))[:5])}"
                  "  →  YYYY-MM-DD 形式で記載してください" if rel_dates else "")

        print(f"\n{_c('【情報】', DIM)}")
        h_by_level = {lv: sum(1 for l, _ in headings if l == lv) for lv in range(1, 5)}
        print(f"  {SYM_INFO} 見出し数: {len(headings)}"
              f"  (h1:{h_by_level[1]} h2:{h_by_level[2]} h3:{h_by_level[3]} h4:{h_by_level[4]})")
        h1s = [t for l, t in headings if l == 1]
        if h1s:
            print(f"  {SYM_INFO} h1: {h1s[0][:60]}")
        print(f"  {SYM_INFO} 内部リンク数: {len(internal_links)}")

    # ────────────────────────
    # 更新履歴.md モード
    # ────────────────────────
    elif mode == "update_history":
        print(_c("【更新履歴.md チェック】", BOLD))

        count, dup, latest_date = _check_update_history(text)

        r.add("（最新）が成果物の系統ごとに1行", count >= 1 and not dup, "FAIL",
              f"（最新）が {count} 行"
              + (f"・同じ系統に複数: {', '.join(dup)}" if dup else "")
              + "  →  系統ごとに1行だけ **（最新）** を付け、旧版の（最新）は外してください")

        if latest_date:
            days_ago = (date.today() - latest_date).days
            r.add("最新日付が1年以内", days_ago <= 365, "WARN",
                  f"最新日付 {latest_date}（{days_ago}日前）  →  更新が必要かもしれません")
            print(f"\n{_c('【情報】', DIM)}")
            print(f"  {SYM_INFO} 最終更新日: {latest_date}  ({days_ago}日前)")
        else:
            r.add("YYYY-MM-DD 形式の日付が含まれている", False, "WARN",
                  "日付が見つかりません。絶対日付で記載してください")

    # ────────────────────────
    # プロジェクト状況.md モード
    # ────────────────────────
    elif mode == "project_status":
        print(_c("【プロジェクト状況.md チェック】", BOLD))

        has_recent, max_year = _check_project_status(text)
        if max_year is None:
            r.add("変更履歴に日付がある", False, "WARN",
                  "変更履歴セクションに YYYY-MM-DD 形式の日付が見つかりません")
        else:
            r.add("変更履歴が当年または前年に更新済み", has_recent, "WARN",
                  f"変更履歴の最新年が {max_year} です  →  セッション終了時に更新が必要です")

    # ────────────────────────
    # サマリー
    # ────────────────────────
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

    return (fails + warns) if strict else fails


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
