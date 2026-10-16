"""
layout_select.py — 「どの型（family）をいつ・何のために選ぶか」を、人の資料の注釈から作った規則で決める。

人が作ったアクセンチュアの資料（本文約 1,400 枚）に「目的・時機・話の段・内容の形・前とのつながり・デッキの種類」と
選ばれた型を注釈し、その集計（grammar/selection_rules.json）で、スライドごとに型の上位案と理由を出す。
grammar_select.py はこの結果で構成パターン（P-xxx）と骨格（K-xxx）の採点を補正する。

outline の content スライドに書く欄（無い欄は「不明」として扱う）:
  purpose     掴ませる / 理解させる / 納得させる / 選ばせる / 決めさせる / 覚えさせる / 参照させる / 行動させる
  story_step  背景 / 目的・ゴール / 要旨 / 課題 / 原因 / 打ち手 / 全体像 / 詳細 / 根拠 / 比較・評価 / 計画 / 体制 /
              費用 / 前提 / 事例 / 効果 / 示唆 / 手順 / 定義 / まとめ / 依頼・次の一手
  shape       {"n_items": 4, "attrs": 3, "relation": "parallel", "data": "none", "focus": true, "text_load": "mid"}
  from_prev   zoom_in / evidence / contrast / next_step / parallel_next / shift / summary / new_topic
timing（deck_open / chapter_open / chapter_body / chapter_close / deck_close / appendix）は章の構造から自動で決める。
デッキの種類は outline の deck_type（proposal / report / training / lt / offering / internal / techvision）。

CLI:
  python layout_select.py outline.json        スライドごとの型の上位 3 案と理由
"""
import json
import math
import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

_RULES = None
_CACHE = {}
FEAT_LABEL = {"intent": "意図", "density": "密度", "deck_type": "デッキの種類", "timing": "時機", "story_step": "話の段", "purpose": "目的",
              "from_prev": "前とのつながり", "relation": "関係", "data": "データ", "focus": "強調する要素",
              "text_load": "文字量", "n_items": "要素数", "attrs": "属性数", "prev_family": "直前の型"}
MATS = ["chart", "diagram", "external_figure", "icons", "logos", "numbers", "people_org", "photo", "screenshot",
        "table_data", "text"]
# compose の部品 → 型（スライドの主図の部品から、使っている型を引く。ペインが複数なら最初の部品）
MODULE_FAMILY = {
    "M-TABLE": "table", "M-MATRIX-SYM": "roles", "M-SCORE": "eval_matrix", "M-MATURITY": "eval_matrix",
    "M-ROWHEAD": "row_header", "M-CARDSTACK": "row_header", "M-COMPARE": "contrast_lr", "M-2AXIS": "quadrant",
    "M-CARD": "cards", "M-HEADCOL": "cards", "M-BADGECOL": "cards", "M-NUMCOL": "cards", "M-ICONGRID": "cards",
    "M-CHEVRON": "process", "M-PIPELINE": "process", "M-PHASE": "process", "M-DIAGRAM-FLOW": "process",
    "M-SWIMLANE": "swimlane", "M-GANTT": "schedule", "M-TIMELINE": "schedule", "M-ROADMAP": "schedule",
    "M-PHASEGRID": "process", "M-LAYER": "layer", "M-ARCH": "layer", "M-TREE": "tree", "M-HUB": "hub", "M-HUBSPOKE": "hub",
    "M-CYCLE": "cycle", "M-HOUSE": "framework", "M-KPI-TILE": "big_number", "M-KPI-STACK": "big_number",
    "M-CHART": "chart", "M-CODE": "screen", "M-SCREEN": "screen", "M-SCREEN-MOCK": "screen", "M-FILETREE": "screen",
    "M-PROMPTBOX": "screen", "M-CHAT-MOCK": "screen", "M-PHOTO": "visual", "M-ILLUST": "visual", "M-CASE": "case",
    "M-ORG": "org", "M-ORG-PYRAMID": "meeting", "M-CHECKLIST": "assumptions", "M-NUMLIST": "summary_points",
    "M-BULLETS": "text_blocks", "M-CALLOUT": "statement", "M-QUOTE": "statement", "M-PROFILE": "profile",
    "M-EQUATION": "framework", "M-ICONROW": "cards", "M-ACTORS": "hub", "M-ORG-ACTORS": "org", "M-VENN": "framework",
    "M-PYRAMID": "framework", "M-CASE": "case",
    "M-ZONE": "text_blocks", "M-RHMATRIX": "row_header", "M-STEPS": "process", "M-FIGNOTE": "hub", "M-RING": "cycle",
    "M-WHY": "row_header", "M-STATGRID": "cards", "M-STRENGTH": "cards",
    "M-CASELIST": "case", "M-COLCARDS": "cards", "M-PROGRAM": "framework", "M-OUTPUTS": "visual", "M-MELON": "schedule",
}


def load_standard():
    """提案書・報告書の定型ページ（grammar/standard_pages.json）。"""
    if "std" not in _CACHE:
        p = os.path.join(_paths.GRAMMAR_DIR, "standard_pages.json")
        _CACHE["std"] = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}
    return _CACHE["std"]


def standard_page(slide, dtype):
    """定型ページなら (ページ名, 定義) を返す。提案書・報告書の 要旨・選ばれる理由・体制・会議体・計画（スケジュール）・費用・前提。"""
    std = load_standard()
    if not std or dtype not in std.get("deck_types", []):
        return None
    t = slide.get("title", "")
    st = slide.get("story_step", "")
    data = (slide.get("shape") or {}).get("data")
    key = None
    if any(k in t for k in ("エグゼクティブサマリ", "サマリー", "サマリ", "骨子", "要旨")) or st == "要旨":
        key = "要旨"
    elif "Why" in t or "選ばれる理由" in t or st == "選ばれる理由":
        key = "選ばれる理由"
    elif "会議" in t:
        key = "会議体"
    elif st == "体制" and not any(k in t for k in ("役割", "分担", "メンバー", "プロフィール")):
        key = "体制"
    elif st == "計画" and (any(k in t for k in ("スケジュール", "日程", "ロードマップ")) or data == "timeseries"):
        key = "計画"
    elif st == "費用" or any(k in t for k in ("見積", "費用", "お見積")) and "前提" not in t:
        key = "費用"
    elif st == "前提" or "前提" in t:
        key = "前提"
    if key and key in std.get("pages", {}):
        return key, std["pages"][key]
    return None
DECK_TYPE_JA = {"提案": "proposal", "報告": "report", "構想": "report", "研修": "training", "勉強": "training",
                "LT": "lt", "講演": "lt", "ウェビナー": "lt", "紹介": "offering", "社内": "internal",
                "タウンホール": "internal", "洞察": "techvision"}


def _label(f, v):
    if f.startswith("mat_"):
        return f"素材に {f[4:]}"
    return f"{FEAT_LABEL.get(f, f)}={v}"


def drawable_families(slide, rules=None):
    """スライドの主な部品で描ける型の集合（M-TABLE なら table・estimate・roles など）。"""
    fams = (rules or load_rules()).get("families", {})
    main = next((p.get("module") for p in slide.get("panes", []) if p.get("module")), None)
    out = set()
    if slide.get("family"):
        out.add(slide["family"])
    if main:
        if main in MODULE_FAMILY:
            out.add(MODULE_FAMILY[main])
        out |= {f for f, v in fams.items() if main in v.get("modules", [])}
    for key, field in (("skeleton", "skeletons"), ("composition", "patterns")):
        if slide.get(key):
            out |= {f for f, v in fams.items() if slide[key] in v.get(field, [])}
    return out


def load_rules():
    global _RULES
    if _RULES is None:
        path = os.path.join(_paths.GRAMMAR_DIR, "selection_rules.json")
        if not os.path.exists(path):
            _RULES = {}
        else:
            with open(path, encoding="utf-8") as f:
                _RULES = json.load(f)
    return _RULES


def bucket_n(n):
    try:
        n = int(n)
    except Exception:
        return "?"
    return "1-2" if n <= 2 else "3-4" if n <= 4 else "5-6" if n <= 6 else "7+"


def bucket_a(n):
    try:
        n = int(n)
    except Exception:
        return "?"
    return "1" if n <= 1 else "2" if n == 2 else "3+"


def deck_type(outline):
    dt = outline.get("deck_type") or (outline.get("settings") or {}).get("deck_type") or ""
    if dt in ("proposal", "report", "training", "lt", "offering", "internal", "techvision", "other"):
        return dt
    for k, v in DECK_TYPE_JA.items():
        if k in str(dt):
            return v
    return "lt" if outline.get("mode") == "present" else "?"


def timings(outline):
    """content スライド番号 → timing。中扉（section）と本文の chapter で章を区切る。"""
    slides = outline.get("slides", [])
    chap, cur, appendix, last = {}, 0, False, None
    out = {}
    for no, s in enumerate(slides, 1):
        t = s.get("type", "content")
        if t == "section":
            cur += 1
            last = s.get("title")
            appendix = "appendix" in (s.get("title") or "").lower() or s.get("role") == "Appendix"
            continue
        if t != "content":
            continue
        if s.get("chapter") and s["chapter"] != last:
            cur += 1
            last = s["chapter"]
            appendix = appendix or "appendix" in s["chapter"].lower()
        if appendix or s.get("role") == "Appendix":
            out[no] = "appendix"
        chap[no] = cur
    # 人の資料の注釈と同じ基準: 末尾・章末は「まとめる・次へ渡す」役のときだけ close にする（詳細・事例・手順で
    # 終わるなら chapter_body）。冒頭は導入の段（背景・目的・要旨・課題）なら 3 枚目まで deck_open にする
    body = [no for no in chap if no not in out]
    step = {no: slides[no - 1].get("story_step") for no in body}
    detail = {"詳細", "事例", "手順"}
    for i, no in enumerate(body):
        c = chap[no]
        same = [n for n in body if chap[n] == c]
        if (i < 2 or (i == 2 and step[no] in ("背景", "目的・ゴール", "要旨", "課題"))) and c == chap[body[0]]:
            out[no] = "deck_open"
        elif i >= len(body) - 2 and step[no] not in detail:
            out[no] = "deck_close"
        elif no == same[0]:
            out[no] = "chapter_open"
        elif no == same[-1] and len(same) >= 3 and (step[no] in ("まとめ", "示唆", "要旨")
                                                     or slides[no - 1].get("from_prev") == "summary"):
            out[no] = "chapter_close"
        else:
            out[no] = "chapter_body"
    return out


def features(slide, timing, dtype, prev_family):
    sh = slide.get("shape") or {}
    rel = sh.get("relation") or slide.get("relation") or (slide.get("relations") or ["?"])[0]
    n = sh.get("n_items")
    mats = slide.get("materials")
    matf = {f"mat_{m}": (("1" if m in mats else "0") if mats else "?") for m in MATS}
    return {
        **matf, "density": slide.get("density") or "?",
        "intent": slide.get("intent") or "?", "deck_type": dtype, "timing": timing or "?", "story_step": slide.get("story_step", "?"),
        "purpose": slide.get("purpose", "?"), "from_prev": slide.get("from_prev", "?"),
        "relation": rel if isinstance(rel, str) else "?", "data": sh.get("data", "?"),
        "focus": str(bool(sh.get("focus"))) if "focus" in sh else "?",
        "text_load": sh.get("text_load") or {"low": "low", "mid": "mid", "high": "high", "max": "high"}.get(slide.get("density"), "?"),
        "n_items": bucket_n(n), "attrs": bucket_a(sh.get("attrs")), "prev_family": prev_family or "START",
    }


def score_families(feat, rules=None, top=3):
    """単純ベイズで型を採点する。理由: 事前確率より強く効いた手がかり（尤度比）と、一致した規則。"""
    rules = rules or load_rules()
    if not rules.get("prior"):
        return []
    prior, counts, a = rules["prior"], rules["counts"], rules.get("alpha", 1.0)
    N = sum(prior.values())
    nvals = {f: len({v for fam in counts[f] for v in counts[f][fam]}) + 1 for f in counts}
    out = []
    for fam, pc in prior.items():
        s = math.log(pc / N)
        why = []
        for f, v in feat.items():
            if v == "?" or f not in counts:
                continue
            c = counts[f].get(fam, {}).get(v, 0)
            p = (c + a) / (pc + a * nvals[f])
            tot_v = sum(counts[f][x].get(v, 0) for x in counts[f])
            pv = (tot_v + a) / (N + a * nvals[f])
            s += math.log(p)
            lr = p / pv
            if lr >= 1.6 and c >= 2 and v not in ("0", "START") and f != "prev_family":
                why.append((lr, _label(f, v)))
        why.sort(reverse=True)
        out.append({"family": fam, "score": s, "why": [w for _, w in why[:3]]})
    out.sort(key=lambda x: -x["score"])
    # 採点を確率に直す（上位の相対的な強さ）
    mx = out[0]["score"]
    z = sum(math.exp(o["score"] - mx) for o in out)
    for o in out:
        o["p"] = round(math.exp(o["score"] - mx) / z, 3)
    # 一致した規則（「こういうとき → この型」）を理由に添える
    for o in out[:top]:
        for r in rules.get("rules", []):
            if r["then"] == o["family"] and all(feat.get(k) == v for k, v in r["if"].items()):
                cond = "・".join(_label(k, v) for k, v in r["if"].items())
                o.setdefault("rules", []).append(f"{cond} → {r['then']}（人の資料で {r['precision']:.0%}）")
                if len(o["rules"]) >= 2:
                    break
    return out


def avoid_hits(feat, family, rules=None):
    rules = rules or load_rules()
    hits = []
    for r in rules.get("avoid", []):
        if r["avoid"] == family and all(feat.get(k) == v for k, v in r["if"].items()):
            cond = "・".join(_label(k, v) for k, v in r["if"].items())
            hits.append(f"{cond} の場面で {family} は人の資料でほぼ使われない（{r['observed']} / 期待 {r['expected']}）")
    return hits


def select(outline, top=3):
    """スライドごとの型の上位案。同じ型の連続は from_prev=parallel_next のときだけ許す。"""
    rules = load_rules()
    if not rules.get("prior"):
        return []
    tm = timings(outline)
    dt = deck_type(outline)
    fams_info = rules.get("families", {})
    res, prev, used = [], None, {}
    for no, s in enumerate(outline.get("slides", []), 1):
        if s.get("type", "content") != "content":
            continue
        feat = features(s, tm.get(no), dt, s.get("prev_family") or prev)
        ranked = score_families(feat, rules)
        for o in ranked:
            adj = math.log(max(o["p"], 1e-6))
            if o["family"] == prev and feat["from_prev"] != "parallel_next":
                adj -= 1.2           # 同じ型を続けるのは同格の項目を並べるときだけ
            adj -= 0.35 * used.get(o["family"], 0)
            if avoid_hits(feat, o["family"], rules):
                adj -= 2.0
            o["adjusted"] = adj
        ranked.sort(key=lambda o: -o["adjusted"])
        sp = standard_page(s, dt)
        if sp:       # 定型ページは人の提案書の多数派の型に固定する（中身のページだけを選び分ける）
            name, info_ = sp
            fam0 = info_["family"][0]
            ev = info_.get("evidence", {})
            head_ = next((o for o in ranked if o["family"] == fam0), {"family": fam0, "p": 0})
            head_ = {**head_, "why": [f"定型ページ「{name}」: {info_.get('how', '')}（人の提案書の {ev.get('share', 0):.0%}）"],
                   "rules": []}
            ranked = [head_] + [o for o in ranked if o["family"] != fam0]
        chosen = s.get("family") or (ranked[0]["family"] if ranked else None)
        used[chosen] = used.get(chosen, 0) + 1
        info = fams_info.get(chosen, {})
        res.append({"no": no, "title": s.get("title", ""), "timing": feat["timing"], "family": chosen,
                    "standard": sp[0] if sp else None,
                    "label": info.get("label_ja", ""),
                    "top3": [{k: o.get(k) for k in ("family", "p", "why", "rules")} for o in ranked[:top]],
                    "avoid": avoid_hits(feat, chosen, rules),
                    "draw": {k: info.get(k, []) for k in ("modules", "skeletons", "patterns")},
                    "why_typical": info.get("why", [])[:2]})
        prev = chosen
    return res


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("outline")
    ap.add_argument("--out")
    a = ap.parse_args()
    a.out = a.out and _paths.check_path(a.out, write=True)
    with open(_paths.check_path(a.outline), encoding="utf-8") as f:
        ol = json.load(f)
    res = select(ol)
    if not res:
        print("grammar/selection_rules.json が無い")
        return
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    for r in res:
        alts = " / ".join(f"{o['family']}({o['p']:.0%})" for o in r["top3"])
        print(f"{r['no']:>2} [{r['timing']}] {r['title'][:22]:<22} → {r['family']} {r['label']}　候補: {alts}")
        why = r["top3"][0].get("rules") or r["top3"][0].get("why")
        if why:
            print("     理由: " + " / ".join(why[:2]))
        if r["draw"].get("modules"):
            print("     描き方: 部品 " + ", ".join(r["draw"]["modules"][:3]) +
                  ("　骨格 " + ", ".join(r["draw"]["skeletons"][:3]) if r["draw"].get("skeletons") else ""))
        for w in r["avoid"]:
            print("     注意: " + w)


if __name__ == "__main__":
    main()
