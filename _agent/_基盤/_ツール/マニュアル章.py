"""定常業務マニュアル（最新版）から、指定した章・節だけを取り出して表示する（読むだけ）。

マニュアルは約8.4万字あり、全体を読むと会話の使用量がかさむ。振り分け表の「読むもの」に
書かれた章だけをこのスクリプトで取り出して読む。

使い方（_agent/ で実行）:
  python _基盤/_ツール/マニュアル章.py --list          # 見出しの一覧（章番号と行番号）
  python _基盤/_ツール/マニュアル章.py 7-2             # 7-2 の節だけ
  python _基盤/_ツール/マニュアル章.py 3 8-2           # 3章全体と 8-2
  python _基盤/_ツール/マニュアル章.py 議事要旨         # 見出しに語を含む節（番号のない節用）
  python _基盤/_ツール/マニュアル章.py --doc JLACマスタチェック手順 8-0   # 同じフォルダの別の手順書

最新版は、マニュアルのフォルダの 更新履歴.md で（最新）が付いた行から決める。
"""
import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AGENT = Path(__file__).resolve().parents[2]
MANUAL_DIR = AGENT / "01_定常業務" / "20260831_電カル調査研究_定常業務マニュアル"
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def latest(doc: str) -> Path:
    """更新履歴.md の（最新）行から、名前に doc を含むファイルを探す。"""
    for line in (MANUAL_DIR / "更新履歴.md").read_text(encoding="utf-8").splitlines():
        if "（最新）" not in line:
            continue
        m = re.search(r"(\d{8}_[^|*（]*?_v\d+\.md)", line)
        if m and doc in m.group(1):
            return MANUAL_DIR / "02_output" / m.group(1)
    sys.exit(f"更新履歴.md に「{doc}」の（最新）が見つかりません")


def sections(lines):
    """(行番号, 見出しレベル, 見出し文) の一覧。コードブロック内は除く。"""
    out, in_code = [], False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_code = not in_code
            continue
        m = None if in_code else HEADING.match(line)
        if m:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def matches(title: str, key: str) -> bool:
    """「7」→「7. …」、「7-2」→「7-2. …」。数字以外は見出しに含まれるかで判定。"""
    if re.fullmatch(r"[\d\-]+", key):
        return re.match(rf"{re.escape(key)}[.．\s]", title + " ") is not None
    return key in title


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keys", nargs="*", help="章番号（7・7-2）または見出しに含まれる語")
    ap.add_argument("--doc", default="定常業務マニュアル", help="対象の文書名（既定：定常業務マニュアル）")
    ap.add_argument("--list", action="store_true", help="見出しの一覧だけを出す")
    a = ap.parse_args()

    path = latest(a.doc)
    lines = path.read_text(encoding="utf-8").splitlines()
    secs = sections(lines)
    print(f"# 出典: {path.relative_to(AGENT)}\n")

    if a.list or not a.keys:
        for i, lv, t in secs:
            if lv <= 3:
                print(f"{i + 1:5d}: {'  ' * (lv - 1)}{t}")
        return

    for key in a.keys:
        hits = [(n, s) for n, s in enumerate(secs) if matches(s[2], key)]
        if not hits:
            print(f"## 「{key}」に当たる見出しがありません（--list で一覧を確認）\n")
            continue
        for n, (start, lv, _) in hits:
            end = next((i for i, l, _ in secs[n + 1:] if l <= lv), len(lines))
            print(f"<!-- {key}: {start + 1}〜{end}行 -->")
            print("\n".join(lines[start:end]).rstrip() + "\n")


if __name__ == "__main__":
    main()
