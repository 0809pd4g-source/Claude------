# -*- coding: utf-8 -*-
"""今日のタスクを数秒で出す（セッション開始・「今日のタスク」と言われたとき用）。

tasks_current.md・会議一覧.md・daily から、次だけを抜き出してMarkdownで表示する。
- 今日の会議（会議一覧 ①の定常＋②の日付つき予定。「参考：出席しない会議」は出さない）
- 締切カレンダーのうち、今日〜N日後（既定7日）と、直近7日以内に過ぎたもの
- 未完了のタスク（- [ ] の行）：見出し・タグ・期限・ステータスだけ（経緯は出さない）
- daily の「マニュアル反映待ち」「WBS向けメモ」の件数

何も書き換えない（読むだけ）。優先順位づけ・上司としての一言はメインが付け足す。

使い方:
    python _agent/_基盤/_ツール/今日のタスク.py               # 今日
    python _agent/_基盤/_ツール/今日のタスク.py --date 2026-10-19 --days 7
"""
import argparse
import datetime as dt
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent / "_タスク管理"
WEEK = "月火水木金土日"


def read(p):
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def section(text, title_re):
    m = re.search(rf"(?m)^##\s+{title_re}.*$", text)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"(?m)^##\s", rest)
    return rest[: n.start()] if n else rest


def table_rows(text):
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", line):
            yield [c.strip() for c in line.strip().strip("|").split("|")]


def md_date(s, year):
    """'10/16（金）' や '10/14（水）〜10/16（金）' を (開始, 終了) に。"""
    ds = re.findall(r"(\d{1,2})/(\d{1,2})", s)
    if not ds:
        return None
    d = [dt.date(year, int(m), int(dd)) for m, dd in ds]
    return d[0], d[-1]


def meetings(today):
    text = read(BASE / "会議一覧.md")
    wd = WEEK[today.weekday()]
    out = []
    for r in table_rows(section(text, "① 定常の会議")):
        if len(r) >= 3 and r[0] in (wd, "毎日"):
            out.append((r[1], r[2], r[4] if len(r) > 4 else "", "定常"))
    dated = []
    for r in table_rows(section(text, "② 週ごとの会議予定")):
        rng = md_date(r[0], today.year) if r else None
        if rng and rng[0] <= today <= rng[1] and "出席しない" not in (r[3] if len(r) > 3 else ""):
            dated.append((r[1], r[2], r[4] if len(r) > 4 else "", r[3] if len(r) > 3 else ""))
    if dated:  # その日の予定が②にあれば、同じ会議名の定常は②を優先
        names = {d[1] for d in dated}
        out = [o for o in out if o[1] not in names]
    rows = out + dated
    rows.sort(key=lambda x: re.sub(r"\D", "", x[0])[:4].zfill(4) if re.search(r"\d", x[0]) else "9999")
    return rows


def calendar(text, today, days):
    rows = []
    for r in table_rows(section(text, "締切カレンダー")):
        if not r or not re.match(r"\d{4}-\d{2}-\d{2}$", r[0]):
            continue
        d = dt.date.fromisoformat(r[0])
        delta = (d - today).days
        if -7 <= delta <= days:
            rows.append((d, r[1], r[2] if len(r) > 2 else "", delta))
    return sorted(rows)


def open_tasks(text):
    tasks, sec = [], ""
    for line in text.splitlines():
        h = re.match(r"^(#{2,3})\s+(.*)", line)
        if h:
            if h.group(1) == "##":
                sec = h.group(2)
            continue
        if not line.startswith("- [ ]") or sec.startswith(("完了", "更新方法")):
            continue
        body = line[5:].strip()
        t = re.search(r"\*\*(.+?)\*\*", body)
        title = t.group(1) if t else body[:60]
        tag = re.search(r"【タグ：([^】]+)】", body)
        due = re.search(r"期限[：:]\s*\**([^。（(]+?)\**(?:[。（(]|$)", body)
        st = re.search(r"ステータス[：:]\s*\**([^。]+?)\**(?:。|$)", body)
        tasks.append({
            "sec": sec, "title": title, "tag": tag.group(1) if tag else "",
            "due": due.group(1).strip() if due else "",
            "status": (st.group(1).strip() if st else "")[:60],
        })
    return tasks


def daily_counts(today):
    text = read(BASE / "daily" / f"{today:%Y%m%d}.md")
    res = {}
    for name in ("マニュアル反映待ち", "WBS向けメモ"):
        s = section(text, name)
        res[name] = len(re.findall(r"(?m)^- ", s))
    return res, bool(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD（省略時は今日）")
    ap.add_argument("--days", type=int, default=7, help="締切を何日先まで出すか")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    tasks_text = read(BASE / "tasks_current.md")

    print(f"## 📋 本日のタスク（{today:%Y-%m-%d}（{WEEK[today.weekday()]}））\n")

    print("### 会議")
    ms = meetings(today)
    if ms:
        print("| 時間 | 会議 | メモ | 区分 |\n|---|---|---|---|")
        for m in ms:
            print(f"| {m[0]} | {m[1]} | {m[2]} | {m[3]} |")
    else:
        print("（会議一覧に今日の予定なし）")

    print(f"\n### 締切（今日〜{a.days}日後、と直近7日以内に過ぎたもの）")
    cal = calendar(tasks_text, today, a.days)
    if cal:
        print("| 締切 | タスク | 優先 | |\n|---|---|---|---|")
        for d, task, pri, delta in cal:
            mark = "⚠️ 今日" if delta == 0 else "⚠️ 明日" if delta == 1 else f"過ぎた（{-delta}日前）・要確認" if delta < 0 else f"{delta}日後"
            print(f"| {d:%m/%d}（{WEEK[d.weekday()]}） | {task} | {pri} | {mark} |")
    else:
        print("（該当なし）")

    ts = open_tasks(tasks_text)
    print(f"\n### 未完了のタスク（{len(ts)}件。経緯は tasks_current.md）")
    print("| 節 | タグ | タスク | 期限 | ステータス |\n|---|---|---|---|---|")
    for t in ts:
        print(f"| {t['sec'][:12]} | {t['tag']} | {t['title'][:70]} | {t['due'][:30]} | {t['status']} |")

    counts, has_daily = daily_counts(today)
    print("\n### 日次メモ")
    if has_daily:
        print(f"- マニュアル反映待ち：{counts['マニュアル反映待ち']}件（終業時に1版にまとめて反映）")
        print(f"- WBS向けメモ：{counts['WBS向けメモ']}件")
    else:
        print(f"- 今日の daily（{today:%Y%m%d}.md）はまだない")
    if today.weekday() == 4:
        print("- 金曜：終業時に tasks_current.md の完了分を外し、締切カレンダーを今週・来週分に整える")


if __name__ == "__main__":
    main()
