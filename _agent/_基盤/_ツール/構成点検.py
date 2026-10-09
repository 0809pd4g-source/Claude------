# -*- coding: utf-8 -*-
"""
構成点検：フォルダ・ファイルの乱れを検出して報告する（何も移動・削除しない）。

検出するもの
  1. 名前の似たプロジェクト（定例会議の回ごとの分裂、シリーズがあるのに単独プロジェクト 等）
  2. 同じ目的の別ファイル（同名ファイル、名前に共通の固有語を持つ参照文書）
  3. 置き場所の違反（_agent 直下・業務分類直下・02_output 外の成果物・管理文書の欠け 等）
  4. ルール文書のコピー（テンプレと同一の CLAUDE.md / README_プロジェクト管理規約.md）

使い方
  python _agent/_基盤/_ツール/構成点検.py              # 全体を点検
  python _agent/_基盤/_ツール/構成点検.py --name 名称   # 新規作成前：似た名前・既存シリーズを探す
  python _agent/_基盤/_ツール/構成点検.py --root <dir>  # 別のツリーを点検（テスト用）

指摘はすべて「提案の候補」。移動・統合・削除はユーザーに1件ずつ相談し、承認後に
チェックポイントのコミットを作ってから行う（_agent/CLAUDE.md・/review-rules）。
"""
import os, re, sys, hashlib, difflib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _find_container(start):
    d = start
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "00_プロジェクトテンプレート")):
            return d
        d = os.path.dirname(d)
    return start


args = sys.argv[1:]
ROOT = args[args.index("--root") + 1] if "--root" in args else _find_container(os.path.dirname(os.path.abspath(__file__)))
NAME = args[args.index("--name") + 1] if "--name" in args else None

SKIP_DIRS = {".git", "_archive", "node_modules", "__pycache__", ".claude", ".agents"}
WORK_DIRS = ("01_input", "02_output", "03_scripts", "04_reference", "00_共通")
MGMT_DOCS = {"プロジェクト状況.md", "更新履歴.md", "CLAUDE.md", "README_プロジェクト管理規約.md", "_フォルダ説明.md"}
DATE_ONLY = re.compile(r"^\d{8}$")
DATE_PREFIX = re.compile(r"^\d{8}_")
DELIVERABLE = re.compile(r"^\d{8}_.+_v\d[\d.]*\.[A-Za-z0-9]+$")
CATEGORY = re.compile(r"^(0[1-9]|99)_")
# 名前に共通していても同じ目的とは言えない一般語（誤検出を減らす）
STOPWORDS = {"プロジェクト", "テンプレート", "マニュアル", "議事録", "逐語録", "ガイド", "資料", "確認", "一覧",
             "手順", "作成", "管理", "チェック", "ルール", "共通", "プロンプト", "移行", "立ち上げ", "指示", "メモ",
             "プロファイル", "フォーマット", "打合せ", "打ち合わせ", "電カル", "電カル共有", "サービス", "用語", "README"}

findings = {k: [] for k in ("名前の似たプロジェクト", "同じ目的の別ファイル", "置き場所", "ルール文書のコピー", "その他フォルダの見直し")}


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def walk():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        yield dp, dns, fns


# ---------- プロジェクトの収集 ----------
projects = []  # (path, 論理名, 親フォルダ)
for dp, dns, fns in walk():
    if "00_プロジェクトテンプレート" in rel(dp).split("/"):
        dns[:] = []
        continue
    if "プロジェクト状況.md" in fns or "更新履歴.md" in fns:
        base = os.path.basename(dp)
        parent = os.path.dirname(dp)
        logical = os.path.basename(parent) if DATE_ONLY.match(base) else DATE_PREFIX.sub("", base)
        projects.append((dp, logical, parent))
        # 管理文書の片方だけ
        if ("プロジェクト状況.md" in fns) != ("更新履歴.md" in fns):
            lack = "更新履歴.md" if "プロジェクト状況.md" in fns else "プロジェクト状況.md"
            findings["置き場所"].append(f"管理文書の片方がない（{lack}）：{rel(dp)}")
        dns[:] = [d for d in dns if d in WORK_DIRS]  # プロジェクトの中は作業フォルダだけ見る


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


# ---------- 1. 名前の似たプロジェクト ----------
series_dirs = {}  # シリーズ名 -> フォルダ（YYYYMMDD の回を含むフォルダ）
for p, logical, parent in projects:
    if DATE_ONLY.match(os.path.basename(p)):
        series_dirs[logical] = parent

if NAME:
    core = DATE_PREFIX.sub("", NAME)
    print(f"== 新規作成前の確認：「{core}」==")
    hit = False
    if core in series_dirs:
        print(f"  ★ 同名の定例シリーズがあります：{rel(series_dirs[core])}/ → 新しいプロジェクトではなく回のフォルダ（YYYYMMDD/）を追加してください")
        hit = True
    for p, logical, parent in projects:
        r = similar(core, logical)
        if r >= 0.6 and not (logical == core and p.startswith(series_dirs.get(core, "\0"))):
            print(f"  似た名前（{r:.2f}）：{rel(p)}")
            hit = True
    if not hit:
        print("  似た名前のプロジェクト・シリーズはありません")
    sys.exit(0)

for i in range(len(projects)):
    for j in range(i + 1, len(projects)):
        (p1, n1, par1), (p2, n2, par2) = projects[i], projects[j]
        same_series = par1 == par2 and DATE_ONLY.match(os.path.basename(p1)) and DATE_ONLY.match(os.path.basename(p2))
        if same_series:
            continue
        r = similar(n1, n2)
        single = lambda p, n, par: not DATE_ONLY.match(os.path.basename(p)) and n in series_dirs and par != series_dirs[n]
        if n1 == n2 and (single(p1, n1, par1) or single(p2, n2, par2)):
            continue
        if n1 == n2 or r >= 0.85:
            tag = "同名" if n1 == n2 else f"類似{r:.2f}"
            hint = "（定例ならシリーズ化：<会議名>/YYYYMMDD/）" if n1 == n2 else ""
            findings["名前の似たプロジェクト"].append(f"{tag}：{rel(p1)} ／ {rel(p2)}{hint}")
for p, logical, parent in projects:
    if not DATE_ONLY.match(os.path.basename(p)) and logical in series_dirs and parent != series_dirs[logical]:
        findings["名前の似たプロジェクト"].append(
            f"シリーズがあるのに単独プロジェクト：{rel(p)} → {rel(series_dirs[logical])}/{os.path.basename(p)[:8]}/ へ移す候補")

# ---------- 2. 同じ目的の別ファイル ----------
refs = []  # 参照文書（成果物・管理文書・作業フォルダ内を除く .md）
for dp, dns, fns in walk():
    r = rel(dp)
    parts = r.split("/")
    if "00_プロジェクトテンプレート" in parts or any(w in parts for w in WORK_DIRS):
        continue
    for f in fns:
        if parts[-1] in ("daily", "_log"):
            continue
        if f.endswith(".md") and f not in MGMT_DOCS and not f.startswith("README") and not DELIVERABLE.match(f) and r != ".":
            refs.append((os.path.join(dp, f), re.sub(r"(_v\d[\d.]*)?\.md$", "", DATE_PREFIX.sub("", f))))


def distinctive(a, b):
    m = difflib.SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    s = a[m.a:m.a + m.size]
    if m.size < 3 or s.strip("_ ・-") != s or re.fullmatch(r"[0-9._-]+", s):
        return None
    return None if any(w in s or s in w for w in STOPWORDS) else s


for i in range(len(refs)):
    for j in range(i + 1, len(refs)):
        (f1, s1), (f2, s2) = refs[i], refs[j]
        if os.path.dirname(f1) == os.path.dirname(f2) and s1 != s2:
            continue
        if s1 == s2:
            findings["同じ目的の別ファイル"].append(f"同名：{rel(f1)} ／ {rel(f2)}")
        else:
            w = distinctive(s1, s2)
            if w:
                findings["同じ目的の別ファイル"].append(f"共通語「{w}」：{rel(f1)} ／ {rel(f2)}（内容が重なっていないか確認）")

# ---------- 3. 置き場所 ----------
agent = os.path.join(ROOT, "_agent")
if os.path.isdir(agent):
    for x in sorted(os.listdir(agent)):
        if x not in ("CLAUDE.md", ".claude", "_基盤") and not CATEGORY.match(x):
            findings["置き場所"].append(f"_agent 直下に管理系・業務分類以外：_agent/{x} → 管理系なら _基盤/ へ")
    for cat in sorted(os.listdir(agent)):
        cp = os.path.join(agent, cat)
        if not (CATEGORY.match(cat) and os.path.isdir(cp)):
            continue
        for x in sorted(os.listdir(cp)):
            xp = os.path.join(cp, x)
            if os.path.isfile(xp) and not x.startswith("."):
                findings["置き場所"].append(f"業務分類の直下にファイルの直置き：{rel(xp)}")
            # 99_その他 は分類できないものの一時置き場。定期的（月1回の /review-rules）に中身を見て、他の分類へ移せないか確認する
            if cat.startswith("99_") and not x.startswith("."):
                findings["その他フォルダの見直し"].append(f"{rel(xp)} → 06_会議／07_ONS問合せ対応／02_仕様・技術 など、ほかの分類に移せないか確認")
proj_set = {p for p, _, _ in projects}
for dp, dns, fns in walk():
    r = rel(dp)
    parts = r.split("/")
    if any(w in parts for w in WORK_DIRS) or "00_プロジェクトテンプレート" in parts or "_基盤" in parts:
        continue
    for f in fns:
        if DELIVERABLE.match(f) and dp in proj_set:
            findings["置き場所"].append(f"成果物らしいファイルが 02_output の外：{rel(os.path.join(dp, f))}")
inp = os.path.join(agent, "_基盤", "_input")
if os.path.isdir(inp):
    for f in sorted(os.listdir(inp)):
        if re.search(r"_v\d[\d.]*\.[A-Za-z0-9]+$", f):
            findings["置き場所"].append(f"_input に版付きファイル（Claude生成物なら 02_output へ）：{rel(os.path.join(inp, f))}")


# ---------- 4. ルール文書のコピー ----------
def md5(p):
    with open(p, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


# 過去のテンプレ（2026-10-07 以前。コピー対策で雛形化する前）のハッシュ。旧テンプレの複製も検出するため
OLD_TPL = {"CLAUDE.md": {"1ef4a2cfd825ad48c37441930d636d83"}, "README_プロジェクト管理規約.md": {"f88978c086adda3583a556e939d8a5da"}}
tpl = os.path.join(ROOT, "00_プロジェクトテンプレート")
tpl_hash = {n: md5(os.path.join(tpl, n)) for n in ("CLAUDE.md", "README_プロジェクト管理規約.md") if os.path.exists(os.path.join(tpl, n))}
for dp, dns, fns in walk():
    if "00_プロジェクトテンプレート" in rel(dp).split("/"):
        continue
    for n, h in tpl_hash.items():
        if n in fns:
            fp = os.path.join(dp, n)
            hv = md5(fp)
            if hv == h or hv in OLD_TPL.get(n, ()):
                findings["ルール文書のコピー"].append(f"テンプレの複製：{rel(fp)} → 削除候補（固有の内容なし）")
            elif n == "README_プロジェクト管理規約.md":
                findings["ルール文書のコピー"].append(f"README の複製（内容が変わっている）：{rel(fp)} → 差分を確認して削除候補")
            elif open(fp, encoding="utf-8-sig", errors="ignore").read(200).lstrip().startswith("# 作業前提：プロジェクト管理規約"):
                findings["ルール文書のコピー"].append(f"旧テンプレの共通部分＋固有の追記：{rel(fp)} → 共通部分を削って固有のルールだけ残す候補")

# ---------- 報告 ----------
total = sum(len(v) for v in findings.values())
print(f"構成点検  ROOT: {ROOT}")
print(f"プロジェクト数: {len(projects)} ／ 参照文書: {len(refs)} ／ 指摘: {total} 件\n")
for k, v in findings.items():
    print(f"== {k}（{len(v)}件）==")
    for x in v:
        print(f"  - {x}")
    if not v:
        print("  （なし）")
    print()
if total:
    print("※ 指摘は提案の候補です。移動・統合・削除は1件ずつ相談し、承認後にチェックポイントのコミットを作ってから行ってください。")
