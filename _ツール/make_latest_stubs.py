# -*- coding: utf-8 -*-
"""版依存リンクの恒久対策：固定名リダイレクトスタブ(_latest.html)を生成し、
成果物間の相互リンクをスタブ経由に張り替える。改訂時はスタブのTARGETを1行直すだけ。
スタブは location.replace(target + location.hash) でアンカーを保持（メタリフレッシュはnoscript代替）。"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "C:/Users/masato.nakazawa/Downloads/Claudeプロジェクト/"

def stub(name, target):
    return (
'<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8"/>\n'
'<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
'<title>最新版へ移動 — '+name+'</title>\n'
'<script>location.replace('+repr_js(target)+'+location.hash);</script>\n'
'<noscript><meta http-equiv="refresh" content="0; url='+target+'"/></noscript>\n'
'<style>body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#191d21;color:#e7ebef;'
'margin:0;padding:40px;line-height:1.6}a{color:#e0b451}</style>\n'
'</head>\n<body>\n'
'<p>「'+name+'」の最新版へ移動します。自動で移動しない場合は '
'<a id="lnk" href="'+target+'">こちら</a> を開いてください。</p>\n'
'<script>var a=document.getElementById("lnk");if(a)a.href='+repr_js(target)+'+location.hash;</script>\n'
'</body>\n</html>\n')

def repr_js(s):
    return '"'+s.replace('\\','\\\\').replace('"','\\"')+'"'

# (スタブのパス, 表示名, リダイレクト先の現行版ファイル名)
STUBS = [
 (BASE+"20260729_東ティモールナレッジベース/02_output/20260729_東ティモールナレッジベース_latest.html",
  "東ティモール総合ナレッジベース", "20260729_東ティモールナレッジベース_v39.35.html"),
 (BASE+"20260729_東ティモールナレッジベース/02_output/20260729_東ティモールKB英語概要_latest.html",
  "Timor-Leste — Essentials（英語概要）", "20260729_東ティモールKB英語概要_v1.html"),
 (BASE+"20260903_東ティモールビジネス実務ガイド/02_output/20260903_東ティモールビジネス実務ガイド_latest.html",
  "東ティモール ビジネス実務ガイド", "20260903_東ティモールビジネス実務ガイド_v1.html"),
]
for path, name, target in STUBS:
    open(path, "w", encoding="utf-8").write(stub(name, target))
    print("stub:", path.split("/")[-1], "->", target)

# 相互リンクを _latest スタブへ張り替え（ファイル名の部分置換＝#anchor 付きも保持）
EDITS = [
 # 本編 v39.35：英語概要／別冊 への外向きリンク
 (BASE+"20260729_東ティモールナレッジベース/02_output/20260729_東ティモールナレッジベース_v39.35.html",
  [("20260729_東ティモールKB英語概要_v1.html", "20260729_東ティモールKB英語概要_latest.html"),
   ("20260903_東ティモールビジネス実務ガイド_v1.html", "20260903_東ティモールビジネス実務ガイド_latest.html")]),
 # 英語概要 v1：本編へのリンク
 (BASE+"20260729_東ティモールナレッジベース/02_output/20260729_東ティモールKB英語概要_v1.html",
  [("20260729_東ティモールナレッジベース_v39.35.html", "20260729_東ティモールナレッジベース_latest.html")]),
 # 別冊 v1：本編へのリンク（intro＋章間相互参照の#anchor付き）
 (BASE+"20260903_東ティモールビジネス実務ガイド/02_output/20260903_東ティモールビジネス実務ガイド_v1.html",
  [("20260729_東ティモールナレッジベース_v39.35.html", "20260729_東ティモールナレッジベース_latest.html")]),
]
for path, reps in EDITS:
    h = open(path, encoding="utf-8").read()
    for a, b in reps:
        c = h.count(a); h = h.replace(a, b)
        print("  ", path.split("/")[-1], f"'{a[-30:]}' x{c}")
    open(path, "w", encoding="utf-8").write(h)
print("done")
