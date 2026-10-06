"""Claude Codeの会話記録（.jsonl）から、指定した時間帯の「アクティブ時間」と実質の推計値を出す。

使い方:
  python _agent/_ツール/作業時間推計.py <会話記録.jsonl> "2026-10-05 11:38" "2026-10-05 15:44" [係数]

考え方（_agent/_タスク管理/作業時間ログ.md の「推計の方法」と同じ）:
  - アクティブ時間 = 時間帯内のユーザー発言どうしの間隔を合計。ただし1つの間隔は上限15分（それ以上は離席・別作業とみなす）。時間帯の最後の発言から次の発言までの間隔も上限15分で足す（次の発言がなければ5分）
  - 実質の推計値 = アクティブ時間 × 係数（初期値1.3。Claudeの出力を読む・ファイルを開いて確認する・Teams等に貼る等の周辺作業を加味）
  - 係数は、本人申告が入ったタスクで「申告 ÷ アクティブ時間」の中央値に更新していく
"""
import json, sys, datetime

JST = datetime.timezone(datetime.timedelta(hours=9))
CAP = 15  # 分
TAIL = 5  # 分

def user_times(path):
    out = []
    for line in open(path, encoding='utf-8'):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get('type') != 'user' or not o.get('timestamp'):
            continue
        c = o.get('message', {}).get('content')
        txt = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text') if isinstance(c, list) else (c or '')
        if not txt.strip() or '<task-notification>' in txt[:40]:
            continue
        out.append(datetime.datetime.fromisoformat(o['timestamp'].replace('Z', '+00:00')).astimezone(JST))
    return sorted(set(out))

def active_minutes(times, start, end):
    ts = [t for t in times if start <= t <= end]
    if not ts:
        return 0.0
    total = sum(min((b - a).total_seconds() / 60, CAP) for a, b in zip(ts, ts[1:]))
    nxt = [t for t in times if t > ts[-1]]
    tail = min((nxt[0] - ts[-1]).total_seconds() / 60, CAP) if nxt else TAIL
    return total + tail

if __name__ == '__main__':
    path, s, e = sys.argv[1:4]
    k = float(sys.argv[4]) if len(sys.argv) > 4 else 1.3
    p = lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').replace(tzinfo=JST)
    a = active_minutes(user_times(path), p(s), p(e))
    print(f'アクティブ時間 {a:.0f}分 / 推計 {a*k:.0f}分（係数{k}）')
