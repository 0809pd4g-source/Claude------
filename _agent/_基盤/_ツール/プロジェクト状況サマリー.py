# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
"""
_agent/ 配下の全プロジェクトを走査し、プロジェクト状況.md から
「次にやること」「未確認事項」を抽出してダッシュボードを表示する。

使い方:
    python _agent/_基盤/_ツール/プロジェクト状況サマリー.py
    python _agent/_基盤/_ツール/プロジェクト状況サマリー.py --stale  # 90日以上更新なしを絞り込み
"""
import os, io, re, sys
from datetime import date, datetime

ROOT = r"C:\Users\masato.nakazawa\Downloads\Claudeプロジェクト\_agent"
TODAY = date.today()
STALE_DAYS = 90  # これ以上更新がなければ「停滞」とみなす

CATEGORY_DIRS = {
    "01_定常業務": "01_定常業務",
    "02_仕様・技術": "02_仕様・技術",
    "03_案件管理": "03_案件管理",
    "04_マスタ・プロファイル管理": "04_マスタ・プロファイル管理",
    "05_周知広報": "05_周知広報",
    "06_その他": "06_その他",
}

STALE_ONLY = "--stale" in sys.argv


def read(path):
    try:
        return io.open(path, encoding="utf-8").read()
    except Exception:
        return ""


def extract_section(text, heading):
    """## heading 以下の次の ## までのテキストを返す"""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_last_date(text):
    """変更履歴の最新日付（YYYY-MM-DD 形式）を返す"""
    dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if not dates:
        return None
    try:
        return max(datetime.strptime(d, "%Y-%m-%d").date() for d in dates)
    except Exception:
        return None


def scan_projects():
    results = []
    for cat_name, cat_dir in CATEGORY_DIRS.items():
        cat_path = os.path.join(ROOT, cat_dir)
        if not os.path.isdir(cat_path):
            continue
        # JLAC等のサブディレクトリも含めて再帰的に探す（深さ2まで）
        for sub in [cat_path] + [os.path.join(cat_path, d) for d in os.listdir(cat_path)
                                   if os.path.isdir(os.path.join(cat_path, d))]:
            for proj in os.listdir(sub):
                proj_path = os.path.join(sub, proj)
                if not os.path.isdir(proj_path):
                    continue
                status_path = os.path.join(proj_path, "プロジェクト状況.md")
                if not os.path.exists(status_path):
                    continue
                text = read(status_path)
                last_date = extract_last_date(extract_section(text, "変更履歴"))
                next_action = extract_section(text, "未確認・要確認事項")
                # 変更履歴末尾の「次にやること」を抽出
                rekishi = extract_section(text, "変更履歴")
                lines = [l.strip() for l in rekishi.splitlines() if l.strip()]
                last_entry = lines[-1] if lines else ""

                if STALE_ONLY:
                    if last_date and (TODAY - last_date).days < STALE_DAYS:
                        continue

                results.append({
                    "category": cat_name,
                    "name": proj,
                    "last_date": last_date,
                    "last_entry": last_entry,
                    "pending": next_action,
                })
    return results


def print_dashboard(results):
    print(f"\n{'='*60}")
    print(f"  プロジェクト状況ダッシュボード  {TODAY}")
    if STALE_ONLY:
        print(f"  ※ {STALE_DAYS}日以上更新なしのみ表示")
    print(f"{'='*60}\n")

    current_cat = None
    for r in sorted(results, key=lambda x: (x["category"], x["name"])):
        if r["category"] != current_cat:
            current_cat = r["category"]
            print(f"\n【{current_cat}】")

        age = f"{(TODAY - r['last_date']).days}日前" if r["last_date"] else "日付不明"
        stale_mark = " ⚠️ 停滞" if r["last_date"] and (TODAY - r["last_date"]).days >= STALE_DAYS else ""

        print(f"\n  [proj] {r['name']}")
        print(f"     最終更新: {r['last_date'] or '不明'} ({age}){stale_mark}")
        if r["last_entry"]:
            print(f"     直近: {r['last_entry'][:80]}")
        if r["pending"]:
            pending_lines = [l for l in r["pending"].splitlines() if l.strip() and not l.startswith("<!--")]
            for line in pending_lines[:3]:
                print(f"     [ ] {line.strip()[:70]}")

    print(f"\n{'='*60}")
    print(f"  合計: {len(results)} プロジェクト")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    results = scan_projects()
    if not results:
        print("プロジェクトが見つかりませんでした。")
    else:
        print_dashboard(results)
