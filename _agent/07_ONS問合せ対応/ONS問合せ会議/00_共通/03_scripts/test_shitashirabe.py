# -*- coding: utf-8 -*-
"""ons_shitashirabe.py の試験（過去の回 10/6・10/13 と突き合わせる）

使い方:
  python test_shitashirabe.py --ledger <台帳xlsx>

- 過去の回のフォルダには何も書かない（結果は標準出力だけ）。
- 正解データ（下の GT_PAGES・GT_SIMILAR）は、10/6回の読み合わせ資料v5・10/13回の資料v15・
  台帳L列の確定回答・設計案§6-1 から人が拾ったもの。新しい回で試すときは、ここに足す。
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path

# cp932のコンソールでも絵文字（✅⚠️❌）・機種依存文字で止まらないように
for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ons_shitashirabe as o  # noqa: E402

# 実際の回答・抜粋に使った技術解説書2.1.0版のページ（出典は README の「試験」参照）
GT_PAGES = {
    519: [42, 43, 45],        # L列確定回答 P.42・P.43、10/13資料 P.45
    524: [120],
    525: [41, 50, 132],       # P.132は想定質問用
    530: [154, 155, 156],
    533: [19, 64, 124],       # 保険者向け手引きP.10は対象外
    534: [132, 133],
    535: [95, 98, 126, 155],
    536: [132, 133],
    537: [2, 6, 7, 74],
    538: [132, 133],
}
# 人が参照した過去の#（資料の「経緯」「想定質問」、台帳のメモ・K列の「参照INC」）
GT_SIMILAR = {
    519: [487],               # S列「#487に類似問合せあり」、K列「参照INC0035966」(=#487)
    530: [500],               # K列「INC0036199」(=#500)
    534: [536],               # S列「#536とあわせて」
    536: [534],
    537: [104, 105, 113],     # 10/13資料 #537「過去の同じ論点の回答」
    538: [518, 515, 183],     # 10/13資料 #538
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=str(o.DEFAULT_LEDGER))
    ap.add_argument("--pdf")
    a = ap.parse_args()
    ledger = Path(a.ledger)
    h0 = o.sha256(ledger)
    recs = o.load_ledger(ledger)
    pages, _ = o.load_pages(o.find_pdf(a.pdf))
    eng = o.Engine(recs, pages)
    by = {r.no: r for r in recs}

    print("== 1. 根拠ページの候補（上位8件に実際のページが入るか）==")
    tot = hit = hit_cited = hit_search = 0
    for no, gt in GT_PAGES.items():
        cands, qt = eng.page_candidates(by[no])
        got = [p for p, *_ in cands]
        cited = [p for p, why, *_ in cands if why != "全文検索"]
        # 検索だけの順位（引用の印を除いた順位）
        qv = eng.page_idx.vec(qt)
        sc = sorted(((o.TfIdf.cos(qv, eng.page_idx.vecs[i]), p.printed) for i, p in enumerate(eng.pages)), key=lambda x: -x[0])
        rank = {p: i + 1 for i, (_, p) in enumerate(sc)}
        h = [p for p in gt if p in got]
        tot += len(gt)
        hit += len(h)
        hc = [p for p in h if p in cited]
        hit_cited += len(hc)
        hit_search += len(h) - len(hc)
        miss = [f"P.{p}(検索{rank.get(p, '-')}位)" for p in gt if p not in got]
        print(f"#{no}: {len(h)}/{len(gt)}（台帳の引用から{len(hc)}＋検索から{len(h) - len(hc)}） 候補={got} 引用={cited} 外れ={miss}")
    print(f"合計: {hit}/{tot} = {hit / tot:.0%}（内訳：台帳の引用から{hit_cited}＋検索から{hit_search}）")

    print("\n== 2. 似た過去回答（上位5件に人が参照した#が入るか）==")
    tot = hit = 0
    for no, gt in GT_SIMILAR.items():
        sims = eng.similar(by[no], top=50)
        order = [s[4].no for s in sims]
        top5 = order[:5]
        h = [x for x in gt if x in top5]
        tot += len(gt)
        hit += len(h)
        miss = [f"#{x}({order.index(x) + 1}位)" if x in order else f"#{x}(50位外)" for x in gt if x not in top5]
        print(f"#{no}: {len(h)}/{len(gt)} 上位5={top5} 外れ={miss}")
    print(f"合計（検索だけ）: {hit}/{tot} = {hit / tot:.0%}")
    # 台帳に書かれた参照（K・S・T列の#・INC番号）を先頭に足した場合。
    # 注意：正解の一部（#519・#530・#534）はこの参照そのものから作っているので、この数字は循環している
    tot = hit = 0
    for no, gt in GT_SIMILAR.items():
        refs = [n for n, _ in eng.ledger_refs(by[no])]
        top = refs + [s[4].no for s in eng.similar(by[no], top=5)]
        h = [x for x in gt if x in top]
        tot += len(gt)
        hit += len(h)
        print(f"#{no}: 台帳の参照={refs} → {len(h)}/{len(gt)}")
    print(f"合計（台帳の参照＋検索5件）: {hit}/{tot} = {hit / tot:.0%}（正解の作り方と重なるため参考）")

    print("\n== 3. 抜粋の照合（台帳L列の全行・技術解説書2.1.0版の抜粋）==")
    allres = []
    for r in recs:
        for ex in o.extract_excerpts(r.l, "L列"):
            if "技術解説書" in ex.doc and ex.version == "2.1.0":
                allres.append((r.no, ex, o.check_excerpt(ex, eng.pt)))
    from collections import Counter
    c = Counter(x[2].status for x in allres)
    print(f"対象 {len(allres)}か所（抜粋の見出し単位）: " + " ".join(f"{k}{v}" for k, v in c.items()))
    nk = nh = 0
    for no, ex, res in allres:
        keys = o._excerpt_keys(ex.text)
        win = eng.pt.window(ex.pages)
        nk += len(keys)
        nh += sum(1 for k in keys if k in win)
    print(f"文の単位: {nh}/{nk} 文が書かれたページ（＋次ページ冒頭）で見つかった")
    for no, ex, res in allres:
        if res.status != "✅":
            print(f"  {res.status} #{no} 「{ex.doc}」 → {res.detail} 見つかった={res.found_pages}")
    other = Counter()
    for r in recs:
        for ex in o.extract_excerpts(r.l, "L列"):
            if not ("技術解説書" in ex.doc and ex.version == "2.1.0"):
                other[o.check_excerpt(ex, eng.pt).detail[:20]] += 1
    print(f"対象外（旧版・他資料）: {dict(other)}")
    print("  目視用サンプル（✅の3件）:")
    for no, ex, res in [x for x in allres if x[2].status == "✅"][:3]:
        k = o._excerpt_keys(ex.text)[0]
        p = ex.pages[0]
        t = eng.pt.norm[p]
        i = t.find(k)
        print(f"   #{no} P.{p} 抜粋頭「{k}」 ページ側「{t[max(0, i - 10):i + 40]}」")

    print("\n== 4. 改ざん検出（ページを1つずらす→⚠️、言葉を変える→❌）==")
    ok_items = [x for x in allres if x[2].status == "✅"]
    shift_ok = alter_ok = tail_ok = word_ok = old_tail = old_word = 0
    for no, ex, _ in ok_items:
        e2 = copy.copy(ex)
        e2.pages = [p + 1 for p in ex.pages]
        r2 = o.check_excerpt(e2, eng.pt)
        shift_ok += r2.status in ("⚠️", "❌")
        e3 = copy.copy(ex)
        e3.text = "\n".join(("".join("〇" if 3 <= i % 7 <= 4 else ch for i, ch in enumerate(ln))) for ln in ex.text.splitlines())
        r3 = o.check_excerpt(e3, eng.pt)
        alter_ok += r3.status == "❌"
        # 文末だけ変える：最も長い文の末尾の語を書き換える（「必要があります」→「必要はありません」に相当）
        lines = ex.text.splitlines()
        li = max(range(len(lines)), key=lambda i: len(o.norm(lines[i])))
        ln = lines[li].rstrip().rstrip("。")
        e4 = copy.copy(ex)
        e4.text = "\n".join(lines[:li] + [ln[:-4] + "ではない。"] + lines[li + 1:])
        r4 = o.check_excerpt(e4, eng.pt)
        tail_ok += r4.status != "✅"
        # 1語だけ変える：最も長い文の真ん中の2文字を別の語に置き換える
        mid = len(ln) // 2
        e5 = copy.copy(ex)
        e5.text = "\n".join(lines[:li] + [ln[:mid] + "任意" + ln[mid + 2:]] + lines[li + 1:])
        r5 = o.check_excerpt(e5, eng.pt)
        word_ok += r5.status != "✅"
        # 比較：v1の方式（各文の先頭25字だけを見る）なら検出できたか
        win = eng.pt.window(ex.pages)
        old_tail += any(k[:25] not in win for k in o._excerpt_keys(e4.text))
        old_word += any(k[:25] not in win for k in o._excerpt_keys(e5.text))
        if r2.status == "✅" or r3.status != "❌" or r4.status == "✅" or r5.status == "✅":
            print(f"  検出できず #{no} {ex.doc}: ずらし={r2.status} 変更={r3.status} 文末={r4.status} 1語={r5.status}")
    print(f"ページずらし: {shift_ok}/{len(ok_items)} 検出、言葉の変更（各行の一部を伏せ字）: {alter_ok}/{len(ok_items)} 検出")
    print(f"文末だけ変える: {tail_ok}/{len(ok_items)} 検出（⚠️か❌）、1語だけ変える: {word_ok}/{len(ok_items)} 検出（⚠️か❌）")
    print(f"  比較：v1の方式（文の先頭25字だけ）なら 文末だけ変える {old_tail}/{len(ok_items)}、1語だけ変える {old_word}/{len(ok_items)}")

    print("\n== 5. #534 の再現（「P.132に記載のとおり『患者同意済』」→❌）==")
    rc = o.check_plain_refs(by[534].l, "L列", by[534].date, eng.pt)
    for x in rc:
        print(f"  台帳L列: {x.status} {x.detail} 文=「{x.ref_text[:60]}」")
    syn = "技術解説書2.1.0版 P.132に記載のとおり「患者同意済」として登録可能です。"
    for x in o.check_plain_refs(syn, "試験用", "2026-09-18", eng.pt):
        print(f"  設計案の文: {x.status} {x.detail}")
    syn2 = "技術解説書2.1.0版 P.132に記載のとおり「医師の判断で同意取得を省略し」登録可能です。"
    for x in o.check_plain_refs(syn2, "試験用", "2026-09-18", eng.pt):
        print(f"  対照（P.132-133に実在する言葉）: {x.status} {x.detail}")

    print("\n== 6. 往復の分割（見出しで分けられなかった行）==")
    j_none = [r.no for r in recs if r.j and not any(s.kind == "質問" for s in r.j_segs)]
    j_pre = [r.no for r in recs if any(s.kind == "前置き" and len(o.norm(s.text)) > 30 for s in r.j_segs)]
    k_none = [r.no for r in recs if r.k and not any(s.kind == "基金コメント" for s in r.k_segs)]
    k_pre = [r.no for r in recs if any(s.kind == "前置き" and len(o.norm(s.text)) > 30 for s in r.k_segs)]
    nj = sum(1 for r in recs if r.j)
    nk = sum(1 for r in recs if r.k)
    print(f"J列あり {nj}行: 回の見出しなし {len(j_none)}行 {j_none[:40]}")
    print(f"J列 見出しの前に30字超の文 {len(j_pre)}行 {j_pre[:40]}")
    print(f"K列あり {nk}行: 機構コメントの見出しなし {len(k_none)}行 {k_none[:40]}")
    print(f"K列 見出しの前に30字超の文 {len(k_pre)}行 {k_pre[:40]}")
    recent = [r for r in recs if r.no >= 500]
    print(f"#500以降 {len(recent)}行: J見出しなし {[r.no for r in recent if r.no in j_none]} K見出しなし {[r.no for r in recent if r.no in k_none]}")

    h1 = o.sha256(ledger)
    print(f"\n== 7. 台帳を壊さない: 実行前 {h0[:16]} 実行後 {h1[:16]} → {'一致' if h0 == h1 else '★不一致'} ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
