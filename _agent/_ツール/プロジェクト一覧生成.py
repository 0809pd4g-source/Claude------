# -*- coding: utf-8 -*-
"""
Downloads 配下の全プロジェクト（更新履歴.md と プロジェクト状況.md を持つフォルダ）を走査し、
最新版・更新日・目的を一覧化した Downloads/プロジェクト一覧.md を生成する。

使い方:  py "Claudeプロジェクト/_ツール/プロジェクト一覧生成.py"
"""
import os, io, datetime

ROOT = r"C:\Users\masato.nakazawa\Downloads\Claudeプロジェクト"
OUT = os.path.join(ROOT, "プロジェクト一覧.md")
MAX_DEPTH = 2  # ROOT からの深さ
EXCLUDE = ("00_プロジェクトテンプレート", "_ツール", "_agent", "_archive")  # プロジェクトとして扱わない


def read(path):
    try:
        return io.open(path, encoding="utf-8").read()
    except Exception:
        return ""


def latest_version(rireki_md):
    """更新履歴.md のテーブルから (成果物, 版, 日付) を返す。（最新）優先、無ければ最終行。"""
    rows = []
    for line in rireki_md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0] in ("成果物",) or set(cells[0]) <= set("-: "):
            continue  # ヘッダ / 区切り行
        rows.append(cells)
    if not rows:
        return ("—", "—", "—")
    # 「（最新）」マーカーは変更内容セルに入る運用なので行内の全セルを対象に探す。
    # 見つからない場合は、最新版を先頭行に置く運用に合わせて rows[0] を採用する。
    pick = next((r for r in rows if any("最新" in c for c in r)), rows[0])
    ver = pick[1].replace("**", "").replace("（最新）", "").strip()
    return (pick[0], ver, pick[2])


def purpose(joukyou_md):
    lines = joukyou_md.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("## 目的"):
            for nxt in lines[i + 1:]:
                t = nxt.strip()
                if t and not t.startswith("<!--") and not t.startswith("#"):
                    return t
            break
    return "—"


def find_projects():
    projects = []
    root_depth = ROOT.rstrip("\\").count("\\")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        depth = dirpath.rstrip("\\").count("\\") - root_depth
        if depth > MAX_DEPTH:
            dirnames[:] = []
            continue
        if any(x in dirpath for x in EXCLUDE):
            continue
        if "更新履歴.md" in filenames and "プロジェクト状況.md" in filenames:
            projects.append(dirpath)
            dirnames[:] = []  # プロジェクト内は掘らない
    return sorted(projects, key=lambda p: os.path.basename(p), reverse=True)


def main():
    projs = find_projects()
    today = datetime.date.today().isoformat()
    out = []
    out.append("# プロジェクト一覧（自動生成）\n")
    out.append(f"> 生成日: {today}　/　`_ツール/プロジェクト一覧生成.py` で再生成\n")
    out.append(f"> 対象: `{ROOT}` 配下で 更新履歴.md・プロジェクト状況.md を持つフォルダ（テンプレート除く）\n")
    out.append("| プロジェクト | 最新版 | 更新日 | 目的 | 場所 |")
    out.append("|---|---|---|---|---|")
    for p in projs:
        name = os.path.basename(p)
        art, ver, date = latest_version(read(os.path.join(p, "更新履歴.md")))
        pur = purpose(read(os.path.join(p, "プロジェクト状況.md")))
        if len(pur) > 40:
            pur = pur[:39] + "…"
        rel = os.path.relpath(p, ROOT)
        out.append(f"| {name} | {ver} | {date} | {pur} | `{rel}` |")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("generated:", OUT)
    print("projects:", len(projs))


if __name__ == "__main__":
    main()
