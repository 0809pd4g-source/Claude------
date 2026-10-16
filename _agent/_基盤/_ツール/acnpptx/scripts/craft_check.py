"""
craft_check.py — 「AI が作った感じ」を図形データから判定するリンター。

人が作ったアクセンチュアの資料（31 本・本文約 1,100 枚）の実測分布（grammar/style_stats.json）と比べて、
外れているスライドを指摘する。しきい値は意図（intent）ごと。outline を渡すと意図・関係・構成も使う。

  ERROR（作り直す）
    - 空き箱: 面積 1.5in² 以上の塗り・枠の箱で、中の文字が 12% 未満、中に他の図形も無い
    - 並列でないのに同じ大きさのカードを 3 つ以上並べている（relation が parallel 以外）
    - 同じ構図（骨格・grid＋部品）が 3 枚続く
    - 中扉が多すぎる（本文 6 枚未満ごとに中扉）／中扉に章の結論文が無い
  WARN（見直す）
    - 意図別の人の分布（p10〜p90）から外れる: 線・長方形以外・図形数・文字量・画像
    - 1 枚の中の文字サイズが 1 種類だけ／太字が無い
    - 箱の中の充填率が低い（人の p10 未満）
    - カード主体のスライドが本文の 30% 超／実物・データを主役にしたスライドが 1/3 未満
    - 隣り合うサムネイルが似すぎている（slides/ を渡したとき。dHash）
最後に「人らしさスコア」（指標が人の p10〜p90 に入っている割合）を出す。

Usage:
  python craft_check.py output.pptx [--outline outline.json] [--slides slides/] [--json]
終了コード: ERROR があれば 1
"""
import argparse
import collections
import json
import os
import sys

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS)
import craft_metrics as cm  # noqa: E402
import paths as _paths  # noqa: E402

STATS = os.path.join(os.path.dirname(_SCRIPTS), "grammar", "style_stats.json")
ARTIFACT_MODULES = {"M-CODE", "M-SCREEN-MOCK", "M-PROMPTBOX", "M-CHAT-MOCK", "M-FILETREE", "M-SCREEN", "M-PHOTO",
                    "M-CHART", "M-TABLE", "M-KPI-TILE", "M-KPI-STACK", "M-FIGREF", "M-GANTT", "M-MATRIX-SYM"}
SCORE_KEYS = ("objects", "lines", "nonrect", "chars", "container_fill_med", "size_kinds", "bold_ratio", "coverage")


def load_stats():
    if not os.path.exists(STATS):
        return {}
    return json.load(open(STATS, encoding="utf-8"))


def band(stats, intent, key):
    """意図別（無ければ全体）の分布 {p10, p25, p50, p75, p90}。"""
    bi = (stats.get("by_intent") or {}).get(intent or "", {})
    v = bi.get(key) or (stats.get("all") or {}).get(key)
    return v


def _sig(spec):
    if not spec:
        return None
    if spec.get("skeleton"):
        return "K:" + spec["skeleton"]
    return f"{spec.get('grid')}|{'+'.join(sorted({p.get('module', '') for p in spec.get('panes', [])}))}"


_SKIP_KEYS = {"module", "grid", "variant", "style", "layout", "direction", "chart_type", "legend_kind", "image", "asset",
              "svg", "icon", "photo", "kind", "tone", "id", "parent"}
TABLE_MODULES = {"M-TABLE", "M-MATRIX-SYM", "M-SCORE"}
STRUCTURAL_MODULES = {"M-ARCH", "M-ORG", "M-HUB", "M-HUBSPOKE", "M-EQUATION", "M-TILEMAP", "M-PHASEGRID", "M-SCORE", "M-MATURITY", "M-HOUSE",
                      "M-GANTT"}
TEXT_MODULES = {"M-BULLETS", "M-NUMLIST", "M-CHECKLIST", "M-CALLOUT", "M-QUOTE", "M-ROWHEAD", "M-CARD", "M-CARDSTACK"}
EMPH_KEYS = ("emph", "focus", "highlight", "highlight_col", "highlight_row", "current", "scope_rows")


def _strings(o, out):
    if isinstance(o, str):
        out.append(o)
    elif isinstance(o, list):
        for v in o:
            _strings(v, out)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k not in _SKIP_KEYS:
                _strings(v, out)
    return out


def _grams(texts):
    """文字の 2-gram の集合（記号・空白・強調記法を除く）。和文の語の重なりを測る。"""
    import re
    s = re.sub(r"[\s\*・、。,.()（）「」:：/／\-–—→⇒>|#\d]", "", "".join(texts))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _emph_count(spec):
    """1 枚の中で紫で強調するものの数（部品の emph/focus/highlight などの宣言と、強調枠・注釈の数）。"""
    n = 0
    for p in spec.get("panes", []):
        if any(p.get(k) is not None and p.get(k) is not False for k in EMPH_KEYS):
            n += 1
        for key in ("options", "nodes", "items", "people", "events", "stages", "actors", "children"):
            for it in p.get(key) or []:
                if isinstance(it, dict) and it.get("emph"):
                    n += 1
                    break
    n += sum(1 for d in spec.get("devices", []) if isinstance(d, dict) and d.get("type") in ("V-HILITE", "V-ANNOT"))
    return n


def editorial_checks(specs, errors, warns):
    """捨てる編集・主張の強さ・デッキのリズム（ChatGPT-Pro のレビューで採用した規則）。outline が必要。"""
    import re
    types = []
    n_statement = 0
    for i, spec in enumerate(specs, 1):
        t = spec.get("type", "content")
        if t == "statement":
            n_statement += 1
        if t not in ("content", "statement"):
            continue
        types.append((i, spec.get("page_type") or ("thesis" if t == "statement" else None)))
        if t != "content":
            continue
        tag = f"#{i}"
        panes = spec.get("panes", [])
        # 1) 主図と、同じ内容を説明し直す表・文章を同じページに置かない
        tables = [p for p in panes if p.get("module") in TABLE_MODULES]
        figs = [p for p in panes if p.get("module") not in TABLE_MODULES]
        for tp in tables:
            for fp in figs:
                a, b = _grams(_strings(tp, [])), _grams(_strings(fp, []))
                if min(len(a), len(b)) >= 12:
                    ov = len(a & b) / min(len(a), len(b))
                    msg = (f"{tag} 主図（{fp.get('module')}）と表（{tp.get('module')}）が同じ内容を繰り返している"
                           f"（語の重なり {ov:.0%}）。主図だけにし、具体例は図の各点に 1 行で添え、詳細表は Appendix へ")
                    if ov >= 0.33:
                        errors.append(msg)
                    elif ov >= 0.25:
                        warns.append(msg)
        if len(tables) >= 2:
            warns.append(f"{tag} 表が {len(tables)} つある（1 枚に 2 つの話題が同居していないか。主張 1・主図 1・補足 1 まで）")
        if len(panes) >= 2 and not tables:
            texts = [p for p in panes if p.get("module") in TEXT_MODULES]
            for tp in texts:
                for fp in panes:
                    if fp is tp or fp.get("module") in TEXT_MODULES:
                        continue
                    a, b = _grams(_strings(tp, [])), _grams(_strings(fp, []))
                    if min(len(a), len(b)) >= 15 and len(a & b) / min(len(a), len(b)) >= 0.5:
                        warns.append(f"{tag} {tp.get('module')} が {fp.get('module')} の内容を言い直している。補足は図の中の注釈に移す")
        # 2) タイトルとメッセージで同じことを言わない
        title, msg = spec.get("title", ""), re.sub(r"\*\*", "", spec.get("message", "") or "")
        tg, mg = _grams([re.sub(r"（案）|\(案\)", "", title)]), _grams([msg])
        if len(tg) >= 5 and mg and len(tg & mg) / len(tg) >= 0.8:
            errors.append(f"{tag} メッセージがタイトルを言い直している。タイトルは話題、メッセージは結論（話題に対して何が言えるか）にする")
        # 2b) 本文の 1 項目がメッセージを言い直していない（本文はメッセージの証拠だけにする）
        if len(mg) >= 10:
            worst, worst_t = 0.0, ""
            for t in _strings(panes, []) + _strings(spec.get("closing") or {}, []) + _strings(spec.get("devices") or [], []):
                plain = re.sub(r"\*\*", "", t)
                if len(plain) < 8 or len(plain) < len(msg) * 0.5:
                    continue
                cov = len(_grams([plain]) & mg) / len(mg)
                if cov > worst:
                    worst, worst_t = cov, plain
            if worst >= 0.45:
                m2 = (f"{tag} 本文の「{worst_t[:18]}…」がメッセージを言い直している（重なり {worst:.0%}）。"
                      "本文はメッセージの根拠・内訳・例だけにし、同じ結論を書かない")
                (errors if worst >= 0.6 else warns).append(m2)
        # 3) ◎○△ などの記号には凡例を付ける
        for p in panes:
            if p.get("module") == "M-TABLE":
                cells = "".join(_strings(p.get("rows") or [], []))
                if re.search(r"[◎○△×]", cells) and not p.get("legend"):
                    errors.append(f"{tag} 表に ◎○△ があるのに凡例が無い（M-MATRIX-SYM にするか legend を付ける）")
        # 4) 紫で強調するのは 1 か所
        ne = _emph_count(spec)
        if ne >= 3:
            warns.append(f"{tag} 紫の強調が {ne} か所で競合している（1 枚に 1 か所。設計票の purple に書いた 1 つだけにする）")
    # 5) リズム: 同じページの型を 3 枚続けない／言い切りページは 3 枚まで
    run, prev = 1, None
    for i, pt in types:
        if pt is None:
            prev, run = None, 1
            continue
        run = run + 1 if pt == prev else 1
        prev = pt
        if run >= 3:
            warns.append(f"#{i} 同じページの型（{pt}）が 3 枚続く。Thesis / Evidence / Mechanism / Decision / Action を混ぜる")
    if n_statement > 3:
        warns.append(f"言い切りページが {n_statement} 枚（物語の転換点だけ、3 枚まで）")
    if types and all(pt is None for _, pt in types[:3]) and len(types) >= 8:
        warns.append("page_type（thesis/evidence/mechanism/decision/action）が無い。デッキのリズム表を作ってから組む")


def dhash(path, size=9):
    from PIL import Image
    im = Image.open(path).convert("L").resize((size, size - 1))
    px = list(im.tobytes())
    bits = 0
    for r in range(size - 1):
        for c in range(size - 1):
            bits = (bits << 1) | (px[r * size + c] > px[r * size + c + 1])
    return bits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--outline")
    ap.add_argument("--slides")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    a.pptx = _paths.check_path(a.pptx)
    a.outline = a.outline and _paths.check_path(a.outline)
    a.slides = a.slides and _paths.check_path(a.slides)
    stats = load_stats()
    shapes, slides = cm.mine_pptx(a.pptx)
    by = collections.defaultdict(list)
    for r in shapes:
        by[r["slide"]].append(r)
    outline = json.load(open(a.outline, encoding="utf-8")) if a.outline else None
    specs = outline.get("slides", []) if outline else []
    errors, warns = [], []
    rows = []
    content_nos = []
    sections = []
    for i, sl in enumerate(slides, 1):
        spec = specs[i - 1] if i - 1 < len(specs) else {}
        t = spec.get("type", "content") if spec else None
        if t is None:   # outline 無し: タイトル以外に本文がある 2 枚目以降を本文とみなす
            t = "content" if i > 1 and len(cm.split_regions(by[i])["body"]) >= 2 else "other"
        if t == "section":
            sections.append((i, spec))
        if t != "content":
            continue
        content_nos.append(i)
        m = cm.slide_metrics(by[i])
        it = spec.get("intent")
        rel = spec.get("relation") or spec.get("relations") or []
        rel = [rel] if isinstance(rel, str) else rel
        rows.append((i, spec, m))
        tag = f"#{i}"
        # 構成図・体制図・格子の部品は、領域の枠や同じ大きさの箱が並ぶのが正しい作り（空き箱・均等カードの判定から外す）
        structural = bool({p.get("module") for p in (spec or {}).get("panes", [])} & STRUCTURAL_MODULES)
        # 人の資料でも 1〜2 個の空き箱はある（p90 = 2）。3 個以上か、箱の半分以上が空いていれば作り直す
        if structural:
            pass
        elif m["empty_boxes"] >= 3 or (m["empty_boxes"] >= 2 and m["empty_boxes"] >= 0.5 * max(1, m["containers"])):
            errors.append(f"{tag} 空き箱 {m['empty_boxes']} 個（大きな箱の中に文字が少ない。箱を中身に合わせて小さくし、余白は要素の間に置く）")
        elif m["empty_boxes"]:
            warns.append(f"{tag} 空き箱 {m['empty_boxes']} 個（文字を足すか箱を詰める）")
        if m["array_equal_cards"] >= 3 and rel and "parallel" not in rel and not spec.get("skeleton") and not structural:
            errors.append(f"{tag} 関係が {'/'.join(rel)} なのに同じ大きさのカードを {m['array_equal_cards']} 枚並べている（時系列なら線、階層なら層、因果なら矢印で）")
        elif m["array_equal_cards"] >= 4 and not rel:
            warns.append(f"{tag} 同じ大きさのカードが {m['array_equal_cards']} 枚。本当に並列か確認（1 つだけ強調する・大きさに差を付ける）")
        checks = (("lines", "線・コネクタ", True), ("nonrect", "長方形以外の図形", True),
                  ("objects", "図形の数", False), ("chars", "文字量", False))
        if m["tables"] or m["charts"]:     # 表・グラフが主役のスライドは図形の数で比べない
            checks = (("chars", "文字量", False),)
        for key, label, lo_only in checks:
            b = band(stats, it, key)
            if not b:
                continue
            v = m.get(key) or 0
            if v < b["p10"] and b["p50"] >= 2:
                warns.append(f"{tag} {label}が少ない（{v}。人の資料の{'「' + it + '」' if it else ''}は中央値 {b['p50']:g}、p10 {b['p10']:g}）")
            elif not lo_only and v > b["p90"] * 1.15:
                warns.append(f"{tag} {label}が多い（{v}。人の資料は p90 {b['p90']:g}）")
        fb = band(stats, it, "container_fill_med")
        if m["container_fill_med"] is not None and fb and m["container_fill_med"] < fb["p10"]:
            warns.append(f"{tag} 箱の中が空いている（充填率 {m['container_fill_med']:.2f}。人は中央値 {fb['p50']:.2f}）")
        if m["tables"]:
            pass        # 表のセルの文字は測っていないので、文字サイズ・太字の検査は省く
        elif m["size_kinds"] <= 1 and m["chars"] > 80:
            warns.append(f"{tag} 文字サイズが 1 種類だけ（見出し・本文・注記で差を付ける）")
        if not m["tables"] and (m["bold_ratio"] or 0) == 0 and m["chars"] > 80:
            warns.append(f"{tag} 太字が無い（要点の語句を **太字** に）")
    if specs:
        editorial_checks(specs, errors, warns)
    # 投影用デッキ（mode=present）は本文 14pt 未満を避ける
    if (outline or {}).get("mode") == "present":
        for i, spec, m in rows:
            hist = collections.Counter()
            for r in cm.split_regions(by[i])["body"]:
                for sz, n in ((r.get("text") or {}).get("sizes") or {}).items():
                    if sz != "inh":
                        hist[float(sz)] += n
            small = sum(n for sz, n in hist.items() if sz < 14)
            tot = sum(hist.values()) or 1
            if small / tot > 0.25:
                warns.append(f"#{i} 投影用なのに 14pt 未満の文字が {small / tot:.0%}（16pt を基本に、情報を減らす）")
    # 構図の連続
    run, prev = 1, None
    for i, spec, m in rows:
        s = _sig(spec) or f"auto:{m['objects'] // 5}:{m['array_equal_cards']}:{m['tables']}:{m['charts']}"
        run = run + 1 if s == prev else 1
        prev = s
        if run >= 3 and (spec or {}).get("role") != "Appendix":     # Appendix は同じ表が続いてよい
            errors.append(f"#{i} 同じ構図が 3 枚続く（{s}）")
    # 中扉
    mode = ((outline or {}).get("settings") or {}).get("divider", "auto")
    agenda_div = mode == "agenda" or (mode == "auto" and sections and len(content_nos) / len(sections) < 8)
    if sections:
        per = len(content_nos) / max(1, len(sections))
        if per < 6:
            errors.append(f"中扉が多すぎる（本文 {len(content_nos)} 枚に中扉 {len(sections)} 枚。人の資料は本文 13 枚に 1 枚。"
                          f"中扉を減らし、目次＋現在地（agenda current）かパンくずにする）")
        for i, spec in sections:
            if not (spec.get("description") or spec.get("message")):
                errors.append(f"#{i} 中扉に章の結論文が無い（description に 1 文）")
    # デッキ全体
    if rows:
        card = sum(1 for _, _, m in rows if m["array_equal_cards"] >= 3)
        if card / len(rows) > 0.30:
            warns.append(f"カード主体のスライドが {card}/{len(rows)} 枚（30% 以下に。人の資料は M-CARD 2%）")
        art = 0
        for _, spec, m in rows:
            mods = {p.get("module") for p in (spec or {}).get("panes", [])}
            if mods & ARTIFACT_MODULES or m["pics"] or m["tables"] or m["charts"] or (spec or {}).get("skeleton_has_artifact"):
                art += 1
        if art / len(rows) < 1 / 3:
            warns.append(f"実物・データ（画面・コード・表・グラフ・写真）を使ったスライドが {art}/{len(rows)} 枚（1/3 以上に）")
    ink_parts = []
    if a.slides and os.path.isdir(a.slides) and stats.get("ink"):
        ik = stats["ink"]
        for i in content_nos:
            f = os.path.join(a.slides, f"slide_{i:02d}.png")
            if not os.path.exists(f):
                continue
            tot, low, rows_ = cm.ink(f)
            ink_parts.append(1.0 if tot >= ik["ink"]["p25"] else 0.5 if tot >= ik["ink"]["p10"] else 0.0)
            present = (outline or {}).get("mode") == "present"
            spec_i = specs[i - 1] if i - 1 < len(specs) else {}
            mods_i = {p.get("module") for p in (spec_i or {}).get("panes", [])}
            m_i = next((m for j, _, m in rows if j == i), {})
            # 表・ガント・時間軸は細い線と文字でできていて、人の資料でもインク量が低い（ERROR にしない）
            # アイコンと線で描く図（ハブ・アイコンのフロー・式・アイコン行・循環）も、塗りが少なくインク量が低い
            lineart = bool(mods_i & {"M-HUB", "M-HUBSPOKE", "M-ICONROW", "M-CYCLE"}) or any(
                p.get("module") == "M-DIAGRAM-FLOW" and p.get("style") == "icon" for p in (spec_i or {}).get("panes", []))
            gridlike = bool(mods_i & {"M-TABLE", "M-MATRIX-SYM", "M-GANTT", "M-TIMELINE", "M-SCORE"}) or                 bool(m_i.get("tables")) or lineart
            if lineart and not present and low < ik["lower"]["p10"] and m_i.get("chars", 999) < 250:
                errors.append(f"#{i} 中身の少ない図のページ（{m_i.get('chars')} 字、下 1/3 のインク量 {low:.2f}）。"
                              "各段に説明＋箇条書きを付けるか、図の脇に根拠・基準のパネルを置く")
            elif (present or gridlike) and low < ik["lower"]["p10"]:
                # 投影用は「捨てる編集」で読み物より余白が増えてよい。ほぼ真っ白（p10 の 3 割未満）だけを ERROR にする
                (errors if not gridlike and low < ik["lower"]["p10"] * 0.3 and tot < ik["ink"]["p10"] else warns).append(
                    f"#{i} 本文の下 1/3 が空いている（インク量 {low:.2f}。人の資料は p10 {ik['lower']['p10']:.2f}）。"
                    f"主図を大きくするか、補足を 1 つ（注釈・示唆）置く")
            elif low < ik["lower"]["p10"] and tot < ik["ink"]["p25"]:
                errors.append(f"#{i} 本文の下 1/3 がほぼ空（インク量 {low:.2f}。人の資料は p10 {ik['lower']['p10']:.2f}・中央値 "
                              f"{ik['lower']['p50']:.2f}）。中身を足して下まで使う（根拠・例・表の列・実物）")
            elif tot < ik["ink"]["p25"]:
                warns.append(f"#{i} 全体に薄い（インク量 {tot:.2f}。人の資料は中央値 {ik['ink']['p50']:.2f}）。文字・図・実物を足す")
    if a.slides and os.path.isdir(a.slides):
        pngs = sorted(f for f in os.listdir(a.slides) if f.lower().endswith(".png"))
        hs = {}
        for f in pngs:
            try:
                n = int("".join(ch for ch in f if ch.isdigit()))
                hs[n] = dhash(os.path.join(a.slides, f))
            except Exception:
                pass
        for x, y in zip(content_nos, content_nos[1:]):
            if x in hs and y in hs and bin(hs[x] ^ hs[y]).count("1") <= 6:
                warns.append(f"#{x} と #{y} のサムネイルが似すぎている（構図・明暗・主役の位置を変える）")
    # 人らしさスコア（0〜100）: スライドごとの指標が人の分布の中央（p25〜p75）なら 1、p10〜p90 なら 0.5、外なら 0。
    # 空き箱・並列でない均等カードはそのスライドを 0 点にする。デッキ全体の「締めの帯の率」「塗りの面積」も加える
    parts = []
    for i, spec, m in rows:
        rel = spec.get("relation") or spec.get("relations") or []
        rel = [rel] if isinstance(rel, str) else rel
        if m["empty_boxes"] >= 3 or (m["array_equal_cards"] >= 3 and rel and "parallel" not in rel and not spec.get("skeleton")):
            parts.append(0.0)
            continue
        sc = []
        keys = SCORE_KEYS if not (m["tables"] or m["charts"]) else ("chars", "container_fill_med", "size_kinds", "bold_ratio")
        for k in keys:
            b = band(stats, spec.get("intent"), k)
            v = m.get(k)
            if not b or v is None:
                continue
            sc.append(1.0 if b["p25"] <= v <= b["p75"] else 0.5 if b["p10"] <= v <= b["p90"] else 0.0)
        if sc:
            parts.append(sum(sc) / len(sc))
    deck_parts = []
    if rows and stats.get("all"):
        human_bb = stats["all"].get("bottom_band_rate") or 0.1
        ours_bb = sum(1 for _, _, m in rows if m["bottom_band"]) / len(rows)
        deck_parts.append(max(0.0, 1 - abs(ours_bb - human_bb) / 0.5))
        hp = ((stats["all"].get("area") or {}).get("purple") or {}).get("p75", 0.13)
        ours_p = sorted(m["area"].get("purple", 0) for _, _, m in rows)[len(rows) // 2]
        deck_parts.append(1.0 if ours_p <= hp else max(0.0, 1 - (ours_p - hp) / 0.2))
        hg = ((stats["all"].get("area") or {}).get("gray") or {}).get("p75", 0.05)
        ours_g = sorted(m["area"].get("gray", 0) for _, _, m in rows)[len(rows) // 2]
        deck_parts.append(1.0 if ours_g <= hg else max(0.0, 1 - (ours_g - hg) / 0.2))
    score = None
    if parts:
        s_slide = sum(parts) / len(parts)
        s_deck = sum(deck_parts) / len(deck_parts) if deck_parts else s_slide
        if ink_parts:     # 見た目の密度（画像のインク量）も 1 要素として入れる
            s_deck = (s_deck * 3 + sum(ink_parts) / len(ink_parts) * 2) / 5
        score = round(100 * (0.7 * s_slide + 0.3 * s_deck))
    out = {"errors": errors, "warnings": warns, "human_likeness": score, "content_slides": len(rows),
           "per_slide": [{"slide": i, **{k: m[k] for k in ("objects", "lines", "nonrect", "chars", "container_fill_med",
                                                         "empty_boxes", "array_equal_cards", "size_kinds")}}
                         for i, _, m in rows]}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"craft_check: 本文 {len(rows)} 枚 / ERROR {len(errors)} / WARN {len(warns)} / 人らしさ {score}")
        for e in errors:
            print("  ERROR", e)
        for w in warns:
            print("  WARN ", w)
        if not stats:
            print("  （grammar/style_stats.json が無いため、分布との比較は省略）")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
