"""
grammar_select.py — アウトライン下書きの各スライドに、構成パターン（P-xxx）の候補を出し、デッキ全体で選ぶ。

入力（outline.json v2 の下書き）: 各 content スライドに少なくとも
    role（Why/What/How/Ask/Plan/Proof/Learn/Appendix）, intent（grammar/intent_map.json のキー）,
    relations（add/cause/contrast/converge/equation/flow/hierarchy/multiply/mutual/parallel/sequence/solve）,
    materials（chart/diagram/external_figure/icons/logos/numbers/people_org/photo/screenshot/table_data/text）,
    density（low/mid/high）
  outline.settings.variation: "統一感" / "バランス" / "多彩"（既定バランス）
  outline.settings.images: "おまかせ" / "アイコン中心" / "イラスト・写真も使う" / "図形のみ"

処理:
  1. intent_map の既定順位 + 条件（relation / materials / density）一致で候補を採点
  2. パターンの when.roles・素材の有無・compose 対応状況で補正
  3. デッキ順に貪欲選択（同一パターンの再使用・隣接スライドの同一配置にペナルティ。重みは variation で変える）
  4. 候補上位 3 件と選択結果、使えそうなデッキ横断の型（S-xx）を出力 → Claude が最終決定する

CLI:
  python grammar_select.py outline.json [--out candidates.json] [--apply]
    --apply: 選んだパターンの grid / panes(module) / connectors / closing / devices を
             まだ埋まっていないスライドに雛形として書き込み、outline.json を上書きする
"""

import argparse
import json
import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

EQUAL_ARRAY = {"M-CARD", "M-HEADCOL", "M-BADGECOL", "M-KPI-TILE", "M-ICONGRID"}
NON_PARALLEL = {"sequence", "hierarchy", "cause", "flow", "converge", "solve", "mutual"}
IMAGE_MODULES = {"M-PHOTO", "M-SCREEN", "M-FIGREF", "M-LOGOROW", "M-DELIVTHUMB", "M-PROFILE"}
VARIATION = {   # 再使用ペナルティ, 隣接同一配置ペナルティ, 提案パターン（観測なし）の加点
    "統一感": (1.0, 0.5, 0.0), "バランス": (3.0, 1.2, 0.3), "多彩": (4.5, 2.0, 0.8),
}


def load_grammar():
    g = {}
    for name in ("compositions", "intent_map", "modules"):
        with open(os.path.join(_paths.GRAMMAR_DIR, f"{name}.json"), encoding="utf-8") as f:
            g[name] = json.load(f)
    g["patterns"] = {p["id"]: p for p in g["compositions"]["patterns"]}
    return g


def _supported():
    try:
        from compose import SUPPORTED_MODULES
        return set(SUPPORTED_MODULES)
    except Exception:
        return set()


def signature(slide_or_struct):
    st = slide_or_struct.get("structure", slide_or_struct)
    mods = sorted({p.get("module") for p in st.get("panes", []) if p.get("module")})
    return f"{st.get('grid', '')}|{'+'.join(mods)}"


def candidates(slide, g, settings, supported):
    im = g["intent_map"].get(slide.get("intent", ""), {})
    scores = {}

    def add(pid, v, why):
        if pid not in g["patterns"]:
            return
        s, w = scores.get(pid, (0.0, []))
        scores[pid] = (s + v, w + [why])

    for x in im.get("default", []):
        add(x["pattern"], 6 - x["rank"], f"意図の既定 {x['rank']} 位")
    rel = set(slide.get("relations") or [])
    mat = set(slide.get("materials") or [])
    for c in im.get("conditions", []):
        cond = c.get("if", {})
        hit = (("relation" in cond and cond["relation"] in rel) or
               ("materials" in cond and cond["materials"] in mat) or
               ("density" in cond and cond["density"] == slide.get("density")))
        if hit:
            for k, pid in enumerate(c.get("ranking", [])[:5]):
                add(pid, 3 - k * 0.5, f"条件一致 {cond}")
    for pid in im.get("editorial_picks", []):
        add(pid, 1.5, "編集推奨")
    var = VARIATION.get(settings.get("variation", "バランス"), VARIATION["バランス"])
    for pid in im.get("proposed_alternatives", []):
        add(pid, 0.5 + var[2], "提案パターン")
    if not scores:   # intent 不明: role と relation だけで全パターンから探す
        for pid, p in g["patterns"].items():
            w = p.get("when", {})
            v = (1.5 if slide.get("role") in w.get("roles", []) else 0) + len(rel & set(w.get("relations", []))) * 1.0
            if v > 0:
                add(pid, v, "役割・関係が一致")
    images = settings.get("images", "おまかせ")
    out = []
    for pid, (s, why) in scores.items():
        p = g["patterns"][pid]
        w = p.get("when", {})
        st = p["structure"]
        mods = [pn["module"] for pn in st.get("panes", [])]
        if slide.get("role") in w.get("roles", []):
            s += 1.0
        s += 0.5 * len(rel & set(w.get("relations", [])))
        need_img = [m for m in mods if m in IMAGE_MODULES]
        if need_img and not (mat & {"photo", "screenshot", "external_figure", "logos", "people_org"}):
            s -= 3.0
            why.append("画像素材が必要だが手元にない")
        if images == "図形のみ" and need_img:
            s -= 5.0
        if supported:
            ratio = sum(m in supported for m in mods) / max(len(mods), 1)
            s += 1.5 * ratio
            if ratio < 1:
                why.append(f"compose 未対応部品あり: {[m for m in mods if m not in supported]}")
        if p.get("status") == "observed":
            s += 0.3
        out.append({"pattern": pid, "name": p["name_ja"], "score": round(s, 2), "why": why[:4],
                    "structure": st, "summary": p.get("summary", ""), "cautions": p.get("cautions", [])[:3]})
    out.sort(key=lambda x: -x["score"])
    return out


def select_deck(outline, g=None):
    g = g or load_grammar()
    settings = outline.get("settings", {})
    var = VARIATION.get(settings.get("variation", "バランス"), VARIATION["バランス"])
    supported = _supported()
    used, prev_grid, used_sk = {}, None, {}
    result = []
    # 型（family）の選択: 目的・時機・話の段・内容の形・前とのつながり → 人の資料の規則（layout_select.py）
    try:
        import layout_select as _ls
        fam_sel = {r["no"]: r for r in _ls.select(outline)}
        _fi = _ls.load_rules().get("families", {})
        pat_fam = {p: f for f, v in _fi.items() for p in v.get("patterns", [])}
        sk_fam = {}
        for f, v in _fi.items():
            for k in v.get("skeletons", []):
                sk_fam.setdefault(k, f)
    except Exception:
        fam_sel, pat_fam, sk_fam = {}, {}, {}
    for no, s in enumerate(outline.get("slides", []), start=1):
        if s.get("type", "content") != "content":
            prev_grid = None
            continue
        fr = fam_sel.get(no)
        fam_rank = {o["family"]: k for k, o in enumerate(fr["top3"])} if fr else {}
        if fr and s.get("family"):
            fam_rank = {s["family"]: 0}
        cands = candidates(s, g, settings, supported)
        for c in cands:      # 型の上位案に入る構成パターンを上げる
            k = fam_rank.get(pat_fam.get(c["pattern"]))
            if k is not None:
                c["score"] += (2.5, 1.5, 0.8)[k]
                c["why"] = [f"型 {pat_fam[c['pattern']]}（{k + 1} 位）"] + c["why"]
        best = None
        rel = s.get("relations") or s.get("relation") or []
        rel = {rel} if isinstance(rel, str) else set(rel)
        for c in cands:
            adj = c["score"] - var[0] * used.get(c["pattern"], 0)
            if prev_grid and c["structure"].get("grid") == prev_grid:
                adj -= var[1]
            mods = {p_.get("module") for p_ in c["structure"].get("panes", [])}
            # 並列でない関係を、同じ大きさのカードの並びで描かない（人の資料で M-CARD は 2%）
            if rel & NON_PARALLEL and "parallel" not in rel and mods and mods <= EQUAL_ARRAY:
                adj -= 3.0
            # 締めの帯は人の資料で 10%。毎回付く型は少し下げる
            if c["structure"].get("closing") not in (None, "C-NONE", "C-NOTE"):
                adj -= 0.4
            c["adjusted"] = round(adj, 2)
        cands.sort(key=lambda c: -c["adjusted"])
        if s.get("composition") and s["composition"] in g["patterns"]:
            best = next((c for c in cands if c["pattern"] == s["composition"]), None)
        best = best or (cands[0] if cands else None)
        if best:
            used[best["pattern"]] = used.get(best["pattern"], 0) + 1
            prev_grid = best["structure"].get("grid")
        sk_top = []
        try:
            import skeleton as _sk
            n_items = s.get("n_items")
            n_items = n_items or (s.get("shape") or {}).get("n_items")
            for sc, sk in _sk.search(s.get("intent"), next(iter(rel), None), n_items, s.get("density"), top=12):
                sc -= var[0] * used_sk.get(sk["id"], 0)
                k = fam_rank.get(sk_fam.get(sk["id"]))
                if k is not None:
                    sc += (4.0, 2.5, 1.2)[k]
                sk_top.append({"id": sk["id"], "name": sk.get("name"), "score": round(sc, 2)})
            sk_top.sort(key=lambda x: -x["score"])
            sk_top = sk_top[:3]
            if s.get("skeleton"):
                used_sk[s["skeleton"]] = used_sk.get(s["skeleton"], 0) + 1
        except Exception:
            pass
        result.append({"no": no, "title": s.get("title", ""), "intent": s.get("intent"), "skeletons": sk_top,
                       "family": fr["family"] if fr else None, "family_label": fr["label"] if fr else "",
                       "family_top3": fr["top3"] if fr else [], "family_avoid": fr["avoid"] if fr else [],
                       "timing": fr["timing"] if fr else None,
                       "chosen": best["pattern"] if best else None,
                       "top3": [{k: c[k] for k in ("pattern", "name", "adjusted", "why", "summary")} for c in cands[:3]],
                       "structure": best["structure"] if best else None,
                       "cautions": best["cautions"] if best else []})
    chosen = {r["chosen"] for r in result if r["chosen"]}
    seqs = []
    for sq in g["compositions"]["deck_sequences"]:
        pats = [st["pattern"] for st in sq.get("sequence", [])]
        overlap = len(set(pats) & chosen)
        if overlap:
            seqs.append({"id": sq["id"], "name": sq["name_ja"], "overlap": overlap, "sequence": pats,
                         "summary": sq.get("summary", "")})
    seqs.sort(key=lambda x: -x["overlap"])
    story = None
    st_id = outline.get("story_template")
    if st_id:
        story = next((t for t in g["compositions"]["story_templates"] if t["id"] == st_id), None)
    return {"slides": result, "deck_sequences": seqs[:6], "story_template": story}


def apply_selection(outline, sel):
    """選ばれたパターンの構造を、未記入のスライドに雛形として入れる（中身は Claude が書く）。"""
    by_no = {r["no"]: r for r in sel["slides"]}
    for no, s in enumerate(outline.get("slides", []), start=1):
        r = by_no.get(no)
        if not r or not r["structure"] or s.get("panes"):
            continue
        st = r["structure"]
        s["composition"] = r["chosen"]
        s["grid"] = st.get("grid")
        s["panes"] = [{"pos": p.get("pos"), "module": p.get("module"), "variant": p.get("variant")} for p in st.get("panes", [])]
        s["connectors"] = list(st.get("connectors", []))
        s["devices"] = list(st.get("devices", []))
        if st.get("closing") and st["closing"] != "C-NONE":
            s["closing"] = {"type": st["closing"], "text": ""}
    return outline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outline")
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    a.outline = _paths.check_path(a.outline, write=a.apply)  # --apply では outline に書き戻す
    a.out = a.out and _paths.check_path(a.out, write=True)
    with open(a.outline, encoding="utf-8") as f:
        ol = json.load(f)
    sel = select_deck(ol)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(sel, f, ensure_ascii=False, indent=1)
    for r in sel["slides"]:
        alts = " / ".join(f"{c['pattern']}({c['adjusted']})" for c in r["top3"])
        print(f"{r['no']:>2} [{r['intent']}] {r['title'][:24]:<24} → {r['chosen']}  候補: {alts}")
        if r.get("family"):
            ft = " / ".join(f"{o['family']}({o['p']:.0%})" for o in r["family_top3"])
            why = (r["family_top3"][0].get("rules") or r["family_top3"][0].get("why") or [])[:2]
            print(f"     型: {r['family']} {r['family_label']} [{r['timing']}]  上位: {ft}" + (f"  理由: {' / '.join(why)}" if why else ""))
            for w in r.get("family_avoid", []):
                print(f"     注意: {w}")
        if r.get("skeletons"):
            print("     骨格: " + " / ".join(f"{k['id']} {k['name'][:18]}({k['score']})" for k in r["skeletons"]))
    if sel["deck_sequences"]:
        print("デッキ横断の型の候補:")
        for sq in sel["deck_sequences"]:
            print(f"  {sq['id']} {sq['name']}: {' → '.join(sq['sequence'])}")
    if a.apply:
        apply_selection(ol, sel)
        with open(a.outline, "w", encoding="utf-8") as f:
            json.dump(ol, f, ensure_ascii=False, indent=1)
        print("applied →", a.outline)


if __name__ == "__main__":
    main()
