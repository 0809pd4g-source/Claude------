# -*- coding: utf-8 -*-
"""
容量整理スクリプト（作業ツリーを軽く保つ）

やること:
  1. 各プロジェクトの 02_output で「最新版＋確定/最新明記版」だけ残し、中間 _vN を間引く
  2. _wip/ の一時ファイルを削除
  3. （報告のみ）複数プロジェクトに重複する大きな入力バイナリを一覧
  4. git gc で .git を圧縮
削除物はすべて git 履歴に残るため復元可（例: git checkout <commit> -- <path>）。

使い方:
  py "_ツール/容量整理.py"           ← ドライラン（何も削除せず計画を表示）
  py "_ツール/容量整理.py" --apply    ← 実行（チェックポイントcommit→間引き→commit→gc）

ROOT はこのスクリプトの2つ上（コンテナ直下）を自動採用するのでフォルダ名変更に強い。
"""
import os, re, io, sys, subprocess

def _find_container(start):
    """コンテナ（00_プロジェクトテンプレート を持つ階層）まで親を遡る。配置場所に依存しない。"""
    d = start
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, '00_プロジェクトテンプレート')):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(start))  # フォールバック

ROOT = _find_container(os.path.dirname(os.path.abspath(__file__)))
# プロジェクト（02_outputを持つフォルダ）を探す際に踏み込まないインフラ・特殊フォルダ。
# _agent 自体は除外しない（配下の業務プロジェクトの 02_output は整理対象）が、
# _agent 内のインフラ（_ツール/_input/_log/_評価/_タスク管理）とテンプレ・.git・_wip は除外する。
EXCLUDE_SEG = {'00_プロジェクトテンプレート', '_ツール', '_input', '_log', '_評価',
               '_タスク管理', '.git', '_wip'}
TRAILER = 'Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>'
APPLY = '--apply' in sys.argv


def git(*args):
    return subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True, encoding='utf-8')


def human(n):
    return f'{n/1048576:.1f} MB'


def dir_size(path, exclude_git=True):
    tot = 0
    for dp, dns, fns in os.walk(path):
        if exclude_git and '.git' in dp.split(os.sep):
            continue
        for f in fns:
            try:
                tot += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return tot


def vtok(name):
    m = re.search(r'_v([0-9][0-9.]*)(\.[^.]+)$', name)
    return m.group(1) if m else None


def series(name):
    return re.sub(r'_v[0-9][0-9.]*(\.[^.]+)$', r'\1', name)


def output_dirs():
    """ツリー全体から『02_output を持つプロジェクトフォルダ』を探す。
    インフラ・テンプレ（EXCLUDE_SEG）には踏み込まない。_agent 配下の業務プロジェクトも対象。"""
    dirs = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in EXCLUDE_SEG]  # 除外フォルダへ踏み込まない
        if '02_output' in dns:
            dirs.append((dp, os.path.join(dp, '02_output')))
            dns.remove('02_output')  # 02_output の中は掘らない
    return sorted(dirs)


def vkey(f):
    """版トークン '39.35' → (39,35) の数値タプル。版番号での大小比較に使う。"""
    t = vtok(f) or '0'
    return tuple(int(x) for x in t.split('.') if x.isdigit())


def marked_versions(proj):
    """更新履歴.md / プロジェクト状況.md で『確定』『（最新）』を含む行の、
    **その行の先頭の版トークン（＝その行が指す成果物の版）だけ** を保持対象にする。
    以前は行内の全vNを拾っていたため、変更説明に他版のvNが並ぶと全版が保持扱いになり
    間引きが常に0件になっていた（本バグの修正）。"""
    keep = set()
    for d in ('更新履歴.md', 'プロジェクト状況.md'):
        p = os.path.join(proj, d)
        if os.path.exists(p):
            for ln in io.open(p, encoding='utf-8', errors='replace').read().splitlines():
                if '確定' in ln or '最新' in ln:
                    m = re.search(r'v([0-9][0-9.]*)', ln)  # 行の先頭版のみ
                    if m:
                        keep.add(m.group(1))
    return keep


def plan_prune():
    """間引き対象（削除候補）を [(path,size), ...] で返す＋プロジェクト別サマリ。"""
    to_del = []
    summary = []
    for proj, od in output_dirs():
        marked = marked_versions(proj)
        files = [f for f in os.listdir(od)
                 if os.path.isfile(os.path.join(od, f)) and vtok(f)]
        groups = {}
        for f in files:
            groups.setdefault(series(f), []).append(f)
        kept = deleted = 0
        for sk, fs in groups.items():
            # 最新は「版番号最大」と「更新時刻最新」の両方を保持（どちらで見ても最新を誤削除しない）
            keep_latest = {max(fs, key=vkey), max(fs, key=lambda f: os.path.getmtime(os.path.join(od, f)))}
            for f in fs:
                if f in keep_latest or vtok(f) in marked:
                    kept += 1
                else:
                    fp = os.path.join(od, f)
                    to_del.append((fp, os.path.getsize(fp)))
                    deleted += 1
        if deleted:
            summary.append((os.path.relpath(proj, ROOT), kept, deleted))
    return to_del, summary


def wip_files():
    out = []
    for dp, dns, fns in os.walk(ROOT):
        if '.git' in dp.split(os.sep):
            continue
        if os.path.basename(dp) == '_wip':
            for f in fns:
                fp = os.path.join(dp, f)
                out.append((fp, os.path.getsize(fp)))
    return out


def dup_big_binaries(min_mb=1.0):
    """複数プロジェクトに同名・同サイズで存在する大きめファイルを検出（報告のみ）。"""
    seen = {}
    for dp, dns, fns in os.walk(ROOT):
        if '.git' in dp.split(os.sep):
            continue
        for f in fns:
            fp = os.path.join(dp, f)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            if sz >= min_mb * 1048576:
                seen.setdefault((f, sz), []).append(os.path.relpath(fp, ROOT))
    return {k: v for k, v in seen.items() if len(v) > 1}


def main():
    print(f'ROOT: {ROOT}')
    print(f'モード: {"APPLY（実行）" if APPLY else "DRY-RUN（計画表示のみ／削除しません）"}')
    before = dir_size(ROOT)
    to_del, summary = plan_prune()
    wips = wip_files()
    dups = dup_big_binaries()

    print('\n== 間引き候補（最新＋確定/最新版は保持）==')
    for name, kept, deleted in sorted(summary, key=lambda x: -x[2]):
        print(f'  {name[:46]:<46} 残={kept} 削={deleted}')
    print(f'  → 削除 {len(to_del)} ファイル / {human(sum(s for _, s in to_del))}')

    print('\n== _wip 一時ファイル ==')
    for fp, sz in wips:
        print(f'  {os.path.relpath(fp, ROOT)} ({human(sz)})')
    if not wips:
        print('  （なし）')

    print('\n== 重複の大きい入力バイナリ（報告のみ・自動削除しない）==')
    if dups:
        for (f, sz), locs in dups.items():
            print(f'  {f} ({human(sz)}) x{len(locs)}:')
            for l in locs:
                print(f'      {l}')
        print('  → 1つに集約し、他は所在メモへ（手動判断）')
    else:
        print('  （なし）')

    if not APPLY:
        print('\n削除は行っていません。実行するには --apply を付けて再実行してください。')
        return

    # ---- APPLY ----
    if git('status', '--porcelain').stdout.strip():
        git('add', '-A')
        git('commit', '-q', '-m', 'チェックポイント: 容量整理の前に全状態を保全（復元用）', '-m', TRAILER)
        print(f'\nチェックポイント: {git("rev-parse","--short","HEAD").stdout.strip()}')

    n = 0
    for fp, _ in to_del + wips:
        try:
            os.remove(fp); n += 1
        except OSError as e:
            print('  削除失敗:', fp, e)
    print(f'削除: {n} ファイル')

    if git('status', '--porcelain').stdout.strip():
        git('add', '-A')
        git('commit', '-q', '-m', '整理: 中間版の間引き・_wip削除（履歴はgitに保全）', '-m', TRAILER)
    git('gc', '--aggressive', '--prune=now')

    after = dir_size(ROOT)
    print(f'\n完了: {human(before)} → {human(after)}（-{human(before-after)}）')
    print('復元例: git checkout <commit> -- <path>')


if __name__ == '__main__':
    main()
