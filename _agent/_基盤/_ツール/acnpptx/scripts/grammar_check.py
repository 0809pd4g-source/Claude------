"""
grammar_check.py — 描画前に、アウトライン（outline.json v2）をデザイン文法で機械チェックする。

対象（grammar/rules.json で checked_by=grammar_check のもの＋配置・容量の整合）:
  スライド: MSG-01/02/03/06/07/10/13, TXT-01, BOD-07, DAT-01/02/08, COL-03/04, LAY-07,
            CB-01/02/03/06/08/10/11/24/31/34/35, 部品の容量（項目数・字数）、配置とペイン数、画像必須部品
  デッキ  : DEC-02/03/08, パターンの重複率・連続使用, 指定枚数, 目次の位置
描画後の検査（フォントサイズ・はみ出し・色）は verify_pptx.py / brand_check.py が担当する。

CLI:
  python grammar_check.py outline.json [--json]
  終了コード: ERROR があれば 1
"""

import argparse
import difflib
import json
import os
import re
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

VAGUE = ["など", "様々", "さまざま", "いろいろ", "適切に", "しっかり", "効果的に", "さらなる", "各種", "諸々"]
EMPTY = ["以下の通り", "以下のとおり", "について", "を説明する", "をご紹介", "の概要", "を示す", "を整理した"]
REDUNDANT = ["となっております", "することが重要である", "と考えられる", "ことができる"]
PANE_COUNT = {"G-11": 2, "G-23": 2, "G-32": 2, "G-SIDE": 2, "G-N3": 3, "G-3W": 3, "G-N4": 4, "G-2x2": 4}
HORIZONTAL = {"G-11", "G-23", "G-32", "G-N3", "G-N4", "G-N5", "G-3W", "G-IO", "G-SIDE"}
ITEM_KEYS = {"M-BULLETS": "items", "M-NUMLIST": "items", "M-CHECKLIST": "items", "M-ROWHEAD": "rows",
             "M-CARDSTACK": "cards", "M-CHEVRON": "steps", "M-PHASE": "phases", "M-KPI-TILE": "tiles",
             "M-KPI-STACK": "tiles", "M-GANTT": "tasks", "M-DIAGRAM-FLOW": "nodes", "M-LAYER": "layers",
             "M-CYCLE": "nodes", "M-ICONGRID": "items", "M-CARD": "items", "M-HEADCOL": "items",
             "M-TABLE": "rows", "M-MATRIX-SYM": "rows"}
IMAGE_KEYS = ("image", "asset", "svg")
MARK = re.compile(r"(?:\*\*|==)(.+?)(?:\*\*|==)")     # **太字** ／ ==太字＋濃い紫==


def _load(name):
    with open(os.path.join(_paths.GRAMMAR_DIR, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def _texts(obj):
    """部品データ中の文字列をすべて取り出す。"""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("module", "pos", "variant", "svg", "image", "asset", "chart_type", "type", "status"):
                continue
            yield from _texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _texts(v)


def _item_texts(pane):
    key = ITEM_KEYS.get(pane.get("module"))
    items = pane.get(key) or []
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, dict):
            out.append(" ".join(_texts({k: v for k, v in it.items() if k not in ("items", "children")})))
        elif isinstance(it, list):
            out.append(" ".join(map(str, it)))
    return out


EQUAL_ARRAY_MODULES = {"M-CARD", "M-HEADCOL", "M-BADGECOL", "M-KPI-TILE", "M-ICONGRID"}
NON_PARALLEL = {"sequence", "hierarchy", "cause", "flow", "converge", "solve", "mutual"}


def signature(s):
    if s.get("skeleton"):
        return "K:" + s["skeleton"]
    if s.get("composition"):
        return s["composition"]
    mods = sorted({p.get("module") for p in s.get("panes", [])})
    return f"{s.get('grid')}|{'+'.join(mods)}"


def _lang_ja(outline):
    lang = (outline.get("lang") or (outline.get("settings") or {}).get("lang") or "ja")
    return str(lang).lower().startswith(("ja", "日本"))


def _msg_lines(msg, outline):
    """描画したときのメッセージの行数（Meiryo UI の実測字幅）。測れなければ None。"""
    if not _lang_ja(outline):
        return None
    try:
        import helpers as _h
        return _h.message_lines(msg)
    except Exception:
        return None


def _title_width(title, outline):
    """タイトル（28pt 太字）の幅（インチ）。"""
    if not _lang_ja(outline):
        return None
    try:
        import helpers as _h
        return sum(_h.char_em(c, True) for c in _h.tidy_ja(title)) * 28 / 72
    except Exception:
        return None


# 和文の文末（述語）: 動詞・形容詞・助動詞の終わり。体言止め（「〜の全体像」「〜へ」）は文として扱わない
_PRED_END = re.compile(r"(る|た|だ|い|す|う|く|ぬ|ず|ん|よ|ね|か|ろ|れ|け|せ|め|て)$")


def _is_sentence(sent, outline):
    if not _lang_ja(outline):
        return True
    s = re.sub(r"[（(][^（）()]*[）)]\s*$", "", sent.strip())      # 末尾の括弧書き（数値の補足）は除いて判定
    s = re.sub(r"[」』\s]+$", "", s)
    return bool(_PRED_END.search(s)) if s else True


def check(outline):
    mods_vocab = {m["id"]: m for m in _load("modules")["modules"]}
    try:
        import skeleton as _sk
        skeletons = _sk.load_all()
    except Exception:
        skeletons = {}
    try:
        from compose import SUPPORTED_MODULES
        supported = set(SUPPORTED_MODULES)
    except Exception:
        supported = set()
    issues = []
    try:
        style = _load("style_stats")
    except Exception:
        style = {}

    def add(level, no, rule, msg):
        issues.append({"level": level, "slide": no, "rule": rule, "msg": msg})

    slides = outline.get("slides", [])
    contents = [(no, s) for no, s in enumerate(slides, start=1) if s.get("type", "content") == "content"]
    for no, s in contents:
        title, msg = s.get("title", ""), s.get("message", "")
        panes = s.get("panes", [])
        modset = [p.get("module") for p in panes]
        grid = s.get("grid", "G-1")
        rel = s.get("relations") or s.get("relation") or []
        rel = {rel} if isinstance(rel, str) else set(rel)
        conns = [c if isinstance(c, str) else c.get("type") for c in s.get("connectors", [])]
        # ── メッセージ・タイトル ──
        if not msg.strip():
            add("ERROR", no, "MSG-01", "メッセージ（リード）が空")
        else:
            plain = MARK.sub(r"\1", msg)
            sents = [p for p in re.split(r"[。！？]", plain) if p.strip()]
            nl = _msg_lines(msg, outline)
            if nl and nl > 2:
                add("ERROR", no, "MSG-02", f"メッセージが描画で {nl} 行になる（最大 2 行。1〜2 文に詰める）")
            elif len(sents) >= 3:
                add("WARN", no, "MSG-02", f"メッセージが {len(sents)} 文（1〜2 文で、読めば中身が分かる形に）")
            elif not nl and len(plain) > 80:
                add("WARN", no, "MSG-02", f"メッセージは 2 行（80 字）以内に（{len(plain)}字）")
            if sents and not _is_sentence(sents[-1], outline):
                add("WARN", no, "MSG-12", "メッセージが文になっていない（体言止め・断片）。主語と述語のある文で言い切る")
            for w in EMPTY:
                if w in msg:
                    add("WARN", no, "MSG-03", f"情報のない表現「{w}」→ 主張を言い切る")
            if len(plain) < 40 and s.get("panes"):
                add("WARN", no, "MSG-13", f"メッセージが薄い（{len(plain)} 字。人の資料の中央値 61 字）— それだけ読めばページの中身が分かるよう、"
                    "結論に「何を・どうやって・どれだけ」（対象・手段・数字）を足す。2 行・2 文まで使ってよい")
            if any(sn.count("、") >= 3 for sn in sents) or any(w in msg for w in REDUNDANT):
                add("WARN", no, "MSG-06", "列挙が多い／文末が冗長")
            for w in VAGUE:
                if w in msg:
                    add("WARN", no, "MSG-07", f"曖昧語「{w}」")
            if title and difflib.SequenceMatcher(None, title, msg).ratio() >= 0.8:
                add("WARN", no, "MSG-10", "タイトルとメッセージがほぼ同じ")
        tw = _title_width(title, outline)
        if tw and tw > 12.3:
            add("ERROR", no, "TITLE", f"タイトルが 2 行になる（約 {tw:.1f}in > 12.3in）。短い論点にし、結論はメッセージへ")
        elif len(title) > 28:
            add("WARN", no, "TITLE", f"タイトルが長い（{len(title)}字、1行28字以内）")
        if re.search(r"[。]", title):
            add("WARN", no, "TITLE", "タイトルが文になっている（句点）。タイトルは論点、結論はメッセージに書く")
        bc = s.get("breadcrumb") or ""
        if bc and ("。" in bc or len(bc) > 24):
            add("WARN", no, "BC-01", "パンくずは現在地（章 > 小見出し）だけにする（文・24 字超）")
        # ── 配置とペイン ──
        if s.get("skeleton"):
            _check_skeleton(add, no, s, skeletons)
        elif not panes:
            add("ERROR", no, "LAYOUT", "panes が空（panes か skeleton を指定）")
        need = PANE_COUNT.get(grid)
        if need and len(panes) != need:
            add("ERROR", no, "LAYOUT", f"{grid} はペイン {need} 個（現在 {len(panes)}）")
        for i, p in enumerate(panes):
            m = p.get("module")
            if m not in mods_vocab:
                if m not in supported:
                    add("ERROR", no, "VOCAB", f"未知の部品 {m}")
                continue      # compose 独自の部品（artifacts.py: M-CODE など）は容量の表が無いので以降の検査を省く
            if supported and m not in supported and not s.get("custom"):
                add("INFO", no, "COMPOSE", f"{m} は compose 未対応（custom 描画が必要）")
            cap = mods_vocab[m].get("capacity", {})
            key = ITEM_KEYS.get(m)
            if key:
                n = len(p.get(key) or [])
                if m in ("M-CARD", "M-HEADCOL") and n == 0 and p.get("text"):
                    n = cap.get("min_items", 1)
                if m in ("M-TABLE", "M-MATRIX-SYM"):
                    if cap.get("max_rows") and n > cap["max_rows"]:
                        add("WARN", no, "CAPACITY", f"{m}: 行 {n} > {cap['max_rows']}")
                    if cap.get("max_cols") and len(p.get("columns") or []) > cap["max_cols"] + 1:
                        add("WARN", no, "CAPACITY", f"{m}: 列が多い")
                else:
                    if cap.get("max_items") and n > cap["max_items"]:
                        add("WARN", no, "CAPACITY", f"{m}: 項目 {n} > 上限 {cap['max_items']}（{cap.get('text', '')}）")
                    if cap.get("min_items") and 0 < n < cap["min_items"] and m not in ("M-KPI-TILE", "M-KPI-STACK"):
                        add("WARN", no, "CAPACITY", f"{m}: 項目 {n} < 目安 {cap['min_items']}")
                if cap.get("max_chars"):
                    for t in _item_texts(p):
                        if len(MARK.sub(r"\1", t)) > cap["max_chars"] * 2.2:
                            add("WARN", no, "CAPACITY", f"{m}: 1項目が長い（{len(t)}字）「{t[:15]}…」")
                            break
            for t in _texts(p):
                if t.count("。") >= 2 or len(t) > 80:
                    add("WARN", no, "TXT-01", f"1項目に2文以上／80字超「{t[:15]}…」")
                    break
            mi = mods_vocab[m].get("accepts_images") or {}
            if mi.get("required"):
                has = any(p.get(k) for k in IMAGE_KEYS) or any(
                    isinstance(it, dict) and it.get("icon") for it in (p.get("items") or []))
                if not has:
                    add("ERROR", no, "IMAGE", f"{m} は画像が必須（image / asset / svg を指定）")
            if grid in HORIZONTAL and panes:
                pw = 12.5 / len(panes)
                if cap.get("min_w_in") and pw < cap["min_w_in"] - 0.3:
                    add("WARN", no, "L-01", f"{m} の幅が足りない（約{pw:.1f}in < {cap['min_w_in']}in）")
            if m == "M-CHART":
                if not p.get("title") or not p.get("unit"):
                    add("ERROR", no, "CB-06", "チャートにタイトルと単位を付ける")
                if p.get("chart_type") in ("pie", "doughnut") and len(p.get("labels") or p.get("categories") or []) <= 2:
                    add("WARN", no, "CB-31", "2区分だけの円グラフ → 大きな数字1つで足りる")
                if not (s.get("source") or p.get("source")):
                    add("WARN", no, "DAT-01", "チャートに出所がない")
            if m == "M-FIGREF" and not (p.get("source") or s.get("source")):
                add("ERROR", no, "CB-35", "引用図に出典がない")
            if m == "M-SCREEN" and not (p.get("caption") or p.get("callouts")):
                add("WARN", no, "CB-11", "画面キャプチャに注目点（吹き出し・番号）がない")
        if modset.count("M-TABLE") >= 2:
            add("WARN", no, "CB-10", "表を2つ並べない（統合するか上下に分ける）")
        if modset and set(modset) == {"M-BULLETS"}:
            add("WARN", no, "CB-34", "箇条書きだけの本文 → 関係を図解化するか見出しで分割")
            total = sum(len(t) for p in panes for t in _texts(p))
            if total > 300:
                add("WARN", no, "BOD-07", f"箇条書きだけで {total} 字")
        if rel & NON_PARALLEL and modset and set(modset) <= EQUAL_ARRAY_MODULES and "parallel" not in rel:
            add("ERROR", no, "CB-EQ", f"関係が {'/'.join(sorted(rel))} なのに同じ大きさのカードを並べる部品だけ"
                                      "（時系列→M-TIMELINE/M-CHEVRON、階層→M-LAYER、因果→矢印、工程の成果物→M-PIPELINE、または骨格）")
        if rel and rel <= {"parallel", "add"} and (set(conns) & {"R-CAUSE", "R-SOLVE"} or "M-CHEVRON" in modset):
            add("WARN", no, "CB-01", "並列の要素を矢印・シェブロンでつないでいる")
        if "sequence" in rel and set(modset) <= {"M-NUMLIST", "M-BULLETS"} and not conns:
            add("WARN", no, "CB-02", "順序があるのに番号だけ → 矢印・シェブロンで示す")
        if "solve" in rel and grid in ("G-11", "G-23", "G-32") and "R-SOLVE" not in conns and "R-CAUSE" not in conns:
            add("WARN", no, "CB-03", "課題→解決の横並びに ⇒（R-SOLVE）を置く")
        if ("contrast" in rel or "R-VS" in conns) and len(panes) == 2 and grid in HORIZONTAL and panes[0].get("module") != panes[1].get("module"):
            add("WARN", no, "CB-08", "比較の左右で部品が違う（同じ構造の鏡像にする）")
        if grid in HORIZONTAL and len(panes) >= 2 and len({p.get("module") for p in panes}) == 1:
            lens = [sum(len(t) for t in _texts(p)) for p in panes]
            if min(lens) > 0 and max(lens) / min(lens) > 2.0:
                add("WARN", no, "LAY-07", f"並列ペインの文字量差が大きい（{min(lens)}〜{max(lens)}字）")
        if "R-ADD" in conns and isinstance(s.get("connectors", [None])[0], dict):
            if len([c for c in s["connectors"] if (c.get("type") if isinstance(c, dict) else c) == "R-ADD"]) < len(panes) - 1:
                add("WARN", no, "CB-24", "＋は全要素の間に揃える")
        # ── 密度（人の資料の意図別の文字量と比べる） ──
        body_chars = sum(len(MARK.sub(r"\1", t)) for t in list(_texts(panes)) + list(_texts(s.get("content") or {})))
        band = ((style.get("by_intent") or {}).get(s.get("intent") or "", {}) or {}).get("chars") or             ((style.get("all") or {}).get("chars"))
        # 投影用（mode=present）は人の資料（読み物中心）より文字が少なくてよい: p25 の 5 割を下回るときだけ
        k_den = 0.5 if outline.get("mode") == "present" else 0.9
        # 読む資料（提案書・報告書）で p25 の 6 割を下回るページは、中身の無いページとして ERROR（v6.8）
        thin = band and body_chars and outline.get("mode") != "present" and body_chars < band["p25"] * 0.6             and s.get("density") != "low" and s.get("role") != "Appendix"
        if thin:
            add("ERROR", no, "DENSITY", f"中身の無いページ（本文 {body_chars} 字。人の資料の「{s.get('intent') or '全体'}」は "
                                        f"p25 {int(band['p25'])} 字）。各段・各項目に説明と根拠（数値・固有名・手順・条件）を込める")
        elif band and body_chars and body_chars < band["p25"] * k_den and s.get("density") != "low"                 and s.get("role") != "Appendix":
            add("WARN", no, "DENSITY", f"本文が {body_chars} 字と少ない（人の資料の「{s.get('intent') or '全体'}」は中央値 "
                                       f"{int(band['p50'])} 字・p25 {int(band['p25'])} 字）。各項目に根拠（数値・固有名・例）を足す")
        for p in panes:                 # 循環図・ハブの段は、名前だけでなく説明を付ける（中身の無い図にしない）
            if p.get("module") in ("M-CYCLE", "M-RING", "M-HUB"):
                short = [nd.get("label", "") for nd in p.get("nodes") or [] if isinstance(nd, dict)
                         and len(MARK.sub(r"\1", (nd.get("text") or "") + "".join(_texts(nd.get("body") or [])))) < 30]
                if short and outline.get("mode") != "present":
                    add("WARN", no, "CAPACITY", f"{p['module']}: 段の説明が短い（{'・'.join(short[:4])}）。各段に説明＋箇条書き 2 つ"
                                                "（body）を書く")
        # ── 強調・データ ──
        emph = list(s.get("emphasis") or [])
        body_emph = []
        for t in _texts(panes):
            body_emph += MARK.findall(t)
        dense_pg = s.get("density") in ("high", "max")
        # 密なページは各ブロックの要点 1 句を強調する（人の資料は 1 枚 6〜10 か所）。メッセージとの結びつきは問わない
        limit = 10 if dense_pg else 3
        if len(emph) + len(body_emph) > limit:
            add("WARN", no, "COL-04", f"強調が多い（{len(emph) + len(body_emph)}箇所。{'密なページは 10' if dense_pg else '3'} か所まで）")
        if not dense_pg:
            emph += body_emph
        for e in emph:
            if msg and e not in msg and not any(ch in msg for ch in [e[:2]]):
                add("WARN", no, "COL-03", f"強調語「{e}」がメッセージと結びついていない")
                break
        if s.get("dummy_data") and not s.get("illustrative"):
            add("ERROR", no, "DAT-08", "ダミー値には illustrative: true を付け、source に試算・仮置きの前提を書く")
        has_num = any(m in ("M-KPI-TILE", "M-KPI-STACK") for m in modset)
        if has_num and not s.get("source") and not s.get("illustrative"):
            add("WARN", no, "DAT-01", "数値の出所がない（source か illustrative を付ける）")
    # ── 型の選択（目的・時機・内容の形と、選んだ型が人の資料の規則に合うか） ──
    _family_checks(outline, add)
    _v64_checks(outline, add)
    _v65_checks(outline, add)
    _v69_checks(outline, add)
    # ── デッキ ──
    if contents:
        heads = " ".join(s.get("title", "") + s.get("message", "") for _, s in contents[:3])
        if not re.search(r"目的|ゴール|背景|狙い|本資料|purpose|goal|agenda", heads, re.I):
            add("WARN", None, "DEC-02", "冒頭3枚に目的・背景がない")
        tails = " ".join(s.get("title", "") + s.get("message", "") + json.dumps(s.get("closing", ""), ensure_ascii=False)
                         for _, s in contents[-2:])
        if not re.search(r"Next|ToDo|今後|次の|次に|ネクスト|まとめ|提言|お願い|C-NEXTACTION", tails, re.I):
            add("WARN", None, "DEC-03", "最後の2枚に次のアクション・まとめがない")
        sigs = [signature(s) for _, s in contents]
        for (n1, _), (n2, _), a, b in zip(contents, contents[1:], sigs, sigs[1:]):
            if a == b:
                add("WARN", n2, "DEC-08", f"直前のスライドと同じ構成（{a}）")
        uniq = len(set(sigs))
        rate = 1 - uniq / len(sigs)
        limit = {"統一感": 0.6, "バランス": 0.4, "多彩": 0.25}.get(outline.get("settings", {}).get("variation", "バランス"), 0.4)
        if rate > limit:
            add("WARN", None, "DIVERSITY", f"構成の重複率 {rate:.0%} > 目安 {limit:.0%}（{uniq}種/{len(sigs)}枚）")
        bars = sum(1 for _, s in contents if (s.get("closing") or {}).get("type", "C-NONE") not in ("C-NONE", "C-NOTE")
                   if isinstance(s.get("closing"), dict))
        if bars / len(contents) > 0.3:
            add("WARN", None, "CLOSING", f"締めの帯が {bars}/{len(contents)} 枚（人の資料は 10%。帯は要所だけにし、"
                                         "ほかは M-CALLOUT・V-ANNOT・メッセージで結論を示す）")
        mn = outline.get("settings", {}).get("min_body_slides")
        if mn and len(contents) < mn:
            add("ERROR", None, "COUNT", f"本文 {len(contents)} 枚 < 指定 {mn} 枚")
    secs = [(no, s) for no, s in enumerate(slides, start=1) if s.get("type") == "section"]
    if secs:
        mode = (outline.get("settings") or {}).get("divider", "auto")
        per = len(contents) / len(secs)
        if per < 6:
            add("ERROR", None, "DIVIDER", f"中扉が多い（本文 {len(contents)} 枚に {len(secs)} 枚。人の資料は本文 13〜15 枚に 1 枚、"
                                         "目次＋現在地でも 9 枚に 1 枚）→ section スライドを外し、目次の items を "
                                         "{title, description} にして各章の結論を書く（位置はパンくずで示す）")
        elif per < 13 and mode == "section":
            add("WARN", None, "DIVIDER", "本文が少ないので、中扉は settings.divider \"agenda\"（目次＋現在地）にする")
        for no, s in secs:
            if not (s.get("description") or s.get("message")):
                add("ERROR", no, "DIVIDER", "中扉に章の結論文（description）が無い")
    types = [s.get("type", "content") for s in slides]
    if "agenda" in types and "cover" in types and types.index("agenda") != types.index("cover") + 1:
        add("WARN", None, "ORDER", "目次は表紙の直後に置く")
    return issues


def chosen_family(s, fams):
    """スライドで使う型: family 欄 → 骨格 → 構成パターン → 主な部品 の順に引く。"""
    if s.get("family"):
        return s["family"]
    for key, field in (("skeleton", "skeletons"), ("composition", "patterns")):
        if s.get(key):
            for f, v in fams.items():
                if s[key] in v.get(field, []):
                    return f
    try:
        from layout_select import MODULE_FAMILY
    except Exception:
        MODULE_FAMILY = {}
    for p in s.get("panes", []):
        if p.get("module") in MODULE_FAMILY:
            return MODULE_FAMILY[p["module"]]
    return None


def _family_checks(outline, add):
    try:
        import layout_select as _ls
    except Exception:
        return
    rules = _ls.load_rules()
    if not rules.get("prior"):
        return
    fams = rules.get("families", {})
    tm = _ls.timings(outline)
    dt = _ls.deck_type(outline)
    prev = None
    filled = 0
    for no, s in enumerate(outline.get("slides", []), start=1):
        if s.get("type", "content") != "content":
            continue
        filled += bool(s.get("purpose") and s.get("story_step"))
        fam = chosen_family(s, fams)
        feat = _ls.features(s, tm.get(no), dt, prev)
        if fam and not s.get("layout_reason"):     # 推奨と違う型を理由付きで選んだスライドは検査しない
            ranked = _ls.score_families(feat, rules, top=3)
            can = _ls.drawable_families(s, rules) or {fam}
            best = max(can, key=lambda f: next((o["p"] for o in ranked if o["family"] == f), 0))
            fam = best
            for w in _ls.avoid_hits(feat, fam, rules):
                add("WARN", no, "SEL-01", w + "。layout_select.py の上位案を検討する")
            p = next((o["p"] for o in ranked if o["family"] == fam), 0)
            if s.get("purpose") and p < 0.02 and ranked:
                top = "・".join(f"{o['family']}({o['p']:.0%})" for o in ranked[:3])
                add("WARN", no, "SEL-02", f"型 {fam} はこの目的・時機・内容の形では人の資料でほぼ選ばれない（上位: {top}）")
            if fam == prev and s.get("from_prev") not in ("parallel_next", None):
                add("WARN", no, "SEL-03", f"直前と同じ型（{fam}）。同じ型を続けるのは同格の項目を並べるとき（from_prev=parallel_next）だけ")
        prev = fam
    n = sum(1 for s in outline.get("slides", []) if s.get("type", "content") == "content")
    if n >= 5 and filled < n * 0.5:
        add("WARN", None, "SEL-00", f"purpose・story_step が {filled}/{n} 枚にしか無い。型の選択（layout_select.py）の手がかりになるので全スライドに書く")


def _has_icon(v):
    """スライドの中にアイコンの指定（icon / icons: "auto"）があるか。"""
    if isinstance(v, dict):
        if v.get("icons") == "auto" or v.get("icon") not in (None, "", False, "none"):
            return True
        return any(_has_icon(x) for x in v.values())
    if isinstance(v, list):
        return any(_has_icon(x) for x in v)
    return False


def _modules(s):
    return [p.get("module", "M-BULLETS") for p in s.get("panes") or []]


def _v64_checks(outline, add):
    """定型ページ（STD-01）・廃止の作り（PYR-01）・人の資料に無い部品の組（COMBO-01）・アイコン（ICON-01/02）・同じ部品の連続（RHY-01）。"""
    try:
        import layout_select as _ls
    except Exception:
        return
    rules = _ls.load_rules()
    fams = rules.get("families", {})
    combos = rules.get("combos") or {}
    seen = combos.get("modules", {})
    pairs = combos.get("pairs", {})
    dt = _ls.deck_type(outline)
    body = [(no, s) for no, s in enumerate(outline.get("slides", []), start=1) if s.get("type", "content") == "content"]
    iconish, with_icon = 0, 0
    run_mod, run = None, 0
    for no, s in body:
        mods = _modules(s)
        reason = s.get("layout_reason")
        sp = _ls.standard_page(s, dt)
        if sp and mods and not reason and not any(m in sp[1].get("modules", []) for m in mods):
            add("WARN", no, "STD-01", f"定型ページ「{sp[0]}」は {' / '.join(sp[1]['modules'])} で描く（{sp[1].get('how', '')}）")
        for p in s.get("panes") or []:
            if p.get("module") == "M-ORG-PYRAMID" or (p.get("module") == "M-ORG" and p.get("layers")):
                add("WARN", no, "PYR-01", "体制ピラミッドは廃止。体制は M-ORG（左右の体制図）、会議体は M-TABLE の表で別に示す")
        ms = sorted(set(m for m in mods if m in seen))
        if not reason:
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    if pairs.get(f"{ms[i]}|{ms[j]}", 0) < 2:
                        add("WARN", no, "COMBO-01", f"{ms[i]} と {ms[j]} の組み合わせは人の資料にほぼ無い（主図を 1 つにするか、よく使われる組にする）")
        fam = chosen_family(s, fams)
        if fam and (fams.get(fam, {}).get("icon_rate") or 0) >= 0.35 and fam != "org" and not sp:
            iconish += 1
        with_icon += _has_icon(s)
        m0 = mods[0] if mods else None
        run = run + 1 if m0 and m0 == run_mod else 1
        run_mod = m0
        if run == 3 and m0 not in ("M-TABLE",):
            add("WARN", no, "RHY-01", f"{m0} が 3 枚続く（同じ見た目を 3 ページ以上続けない。内容の形に合う別の型にする）")
    if iconish >= 3 and with_icon == 0:
        add("WARN", None, "ICON-01", f"アイコンを使うことが多い型（工程・層・並列・ハブ・循環など）が {iconish} 枚あるのに、"
            "アイコンが 1 つも無い。icon: \"q:英語の概念語\" か icons: \"auto\" で入れる（人の資料はこれらの型の 4〜8 割でアイコンを使う）")
    if body and with_icon > len(body) * 0.6:
        add("WARN", None, "ICON-02", f"アイコンのあるスライドが {with_icon}/{len(body)} 枚と多い（人の資料は本文の約 2〜3 割。表・グラフ・定型ページには入れない）")


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in ("module", "icon", "icon_q", "grid", "style", "type", "header_style", "col_style", "fill"):
                yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


def _v65_checks(outline, add):
    """密なページの作法（v6.5）。
    EMPH-01: 密なページ（density high）に文中の強調（**語**）が無い（人の資料は本文ボックスの 38% に部分強調）
    EMPH-02: 1 つの文で強調が 2 句を超える／字数の 6 割を超える（強調が効かない）
    EMPH-03: 色付きの強調（==語==）が 1 つの文で 2 句以上／1 枚で 4 句以上（紫が多く見える。人の部分強調の 75% は色なし）
    STD-02:  提案書の本文の最初の 3 枚に要旨（エグゼクティブサマリー・目的と骨子）が無い
    DENS-01: 提案書・報告書の本文ページの字数の中央値が 300 字未満（情報が薄い。人の提案書は 400〜650 字）"""
    import re
    import statistics
    try:
        import layout_select as _ls
        dt = _ls.deck_type(outline)
    except Exception:
        dt = outline.get("deck_type")
    body = [(no, s) for no, s in enumerate(outline.get("slides", []), start=1) if s.get("type", "content") == "content"]
    counts = []
    for no, s in body:
        texts = list(_strings(s.get("panes") or [])) + list(_strings(s.get("closing") or []))
        n = sum(len(MARK.sub(r"\1", t)) for t in texts)
        counts.append(n)
        if s.get("density") in ("high", "max") and n >= 250 and not any("**" in t or "==" in t for t in texts):
            add("WARN", no, "EMPH-01", "密なページに強調が無い。各ブロックの要点 1 句を **語**（太字）にする。"
                "特に効かせる 1 句だけ ==語==（太字＋濃い紫）")
        colored = [m for t in texts for m in re.findall(r"==(.+?)==", t)]
        if len(colored) >= 4 or any(len(re.findall(r"==(.+?)==", t)) >= 2 for t in texts):
            add("WARN", no, "EMPH-03", f"色付きの強調（==語==）が {len(colored)} 句。色は 1 文 1 句・1 枚 3 句まで"
                "（ほかは **語** の太字だけにする）")
        for t in texts:
            marks = MARK.findall(t)
            plain = len(MARK.sub(r"\1", t))
            if len(marks) > 2 or (marks and plain >= 20 and sum(len(m) for m in marks) > plain * 0.6):
                add("WARN", no, "EMPH-02", f"強調が多い（「{t[:18]}…」で {len(marks)} 句）。1 文の強調は 1〜2 句、字数の 6 割まで")
                break
    if dt == "proposal" and body:
        head = body[:3]
        def is_summary(s):
            t = (s.get("title", "") + s.get("story_step", "") + s.get("page_type", ""))
            return any(k in t for k in ("サマリ", "要旨", "骨子", "Executive", "summary")) or \
                any(p.get("style") == "summary" for p in s.get("panes") or [])
        if not any(is_summary(s) for _, s in head):
            add("WARN", None, "STD-02", "提案書の冒頭（本文の最初の 3 枚）に要旨が無い。エグゼクティブサマリー（M-ZONE style summary）"
                "か「目的と骨子」（M-ZONE×2＋R-TRI）を置き、続けて選ばれる理由（M-ROWHEAD の Why 型）を置く")
    if dt in ("proposal", "report") and len(counts) >= 5:
        med = statistics.median(counts)
        if med < 300:
            add("WARN", None, "DENS-01", f"本文ページの字数の中央値が {int(med)} 字と少ない（人の提案書は 400〜650 字）。"
                "中身のページは density high にし、ゾーン → 小見出し → 箇条書き 2 段 → 強調 → ⇒ 結論 の型で書く")


_DATE_YM = re.compile(r"(?<!\d)(20)?(\d{2})\s*年\s*(\d{1,2})\s*月|(?<!\d)(20\d{2})\s*[/.\-]\s*(\d{1,2})(?!\d)")
_VAGUE_COLS = {"概要", "内容", "備考", "その他", "イメージ", "説明", "注記", "詳細"}
_LAYOUT_TALK = re.compile(r"左(側)?に|右(側)?に|上(の)?図|下(の)?図|下表|上表|次の(表|図)|以下に(示|整理|記載)")
_BIG_NUM = re.compile(r"(?<![\d,.\-/:A-Za-z])(\d{5,}|[1-9]\d{3})(?![\d,.:/年%％\-A-Za-z])")


def _ym(text):
    """文中の年月（「25年4月」「2026年1月」「2026/04」）を (年, 月) で返す。"""
    out = []
    for m in _DATE_YM.finditer(text):
        if m.group(2):
            y, mo = 2000 + int(m.group(2)), int(m.group(3))
        else:
            y, mo = int(m.group(4)), int(m.group(5))
        if 1 <= mo <= 12 and 2000 <= y <= 2100:
            out.append((y, mo, m.group(0)))
    return out


def _parse_ym(v):
    if not v:
        return None
    m = re.match(r"\s*(20\d{2})\D+(\d{1,2})", str(v))
    if m:
        return int(m.group(1)), int(m.group(2))
    d = _ym(str(v))
    return (d[0][0], d[0][1]) if d else None


def _v69_checks(outline, add):
    """v6.9 の検査（ユーザーの指摘とデリバリーマニュアルから）。
    STAMP-01: 成果物・画面の見本ではないページに「イメージ」の札（V-STAMP）。要旨・実績・現状・効果などに付けない
    DAT-09:   illustrative（試算・仮置き）なのに、source に試算の前提が無い（札では示さない）
    MSG-14:   メッセージに改行が入っている（枠の幅で自然に折り返す）
    MSG-15:   メッセージが構成の説明（「左に〜、右に〜」「下表の通り」）。結論と解釈を書く
    DATE-00:  提案書・報告書で as_of（作成日）と anchors（題材の製品・制度の開始日）が無い
    DATE-01:  実績・事例の時期が、題材の開始日（anchors）より前（まだ存在しないものの実績になる）
    DATE-02:  実績・事例の時期が作成日（as_of）より後（未来の実績）
    DATE-03:  スケジュール・計画の時期が作成日より前（過去に始まる計画）
    DENS-02:  提案書・報告書（本文 10 枚以上）に density "max" の詳細ページが無い／high 以上が 4 割未満
    TBL-01:   表の列名が曖昧（概要・内容・備考・その他・イメージ）。一列一意で、列の中身を名前にする
    NUM-01:   4 桁以上の数に桁区切りが無い（10260万円 → 10,260万円）"""
    try:
        import compose as _c
        stamp_ok = _c.stamp_allowed
    except Exception:
        stamp_ok = None
    try:
        import layout_select as _ls
        dt = _ls.deck_type(outline)
    except Exception:
        dt = outline.get("deck_type")
    as_of = _parse_ym(outline.get("as_of") or outline.get("date"))
    anchors = [(a.get("name", ""), _parse_ym(a.get("date"))) for a in outline.get("anchors") or [] if isinstance(a, dict)]
    anchors = [(n, d) for n, d in anchors if d]
    if dt in ("proposal", "report") and not (outline.get("as_of") and outline.get("anchors")):
        add("WARN", None, "DATE-00", "as_of（作成日。例 \"2026-10\"）と anchors（題材の製品・機能・制度の提供開始日と出典）を"
            "書く。実績・事例・スケジュールの時期がこれと矛盾しないかを DATE-01〜03 で確かめる")
    body = [(no, s) for no, s in enumerate(outline.get("slides", []), start=1) if s.get("type", "content") == "content"]
    for no, s in body:
        title = s.get("title", "") or ""
        msg = s.get("message", "") or ""
        mods = {p.get("module") for p in s.get("panes") or []}
        devs = [d if isinstance(d, str) else d.get("type") for d in s.get("devices") or []]
        if stamp_ok and "V-STAMP" in devs and not stamp_ok(s):
            add("ERROR", no, "STAMP-01", "「イメージ」の札は成果物・画面・構築イメージなど、これから作る物の見本だけに付ける"
                "（要旨・実績・現状・課題・効果・見積・体制には付けない）。試算・仮置きは source に前提を書く")
        if s.get("illustrative") and stamp_ok and not stamp_ok(s) and \
                not re.search(r"試算|前提|仮置|仮の|想定|例示|架空|サンプル", s.get("source") or ""):
            add("WARN", no, "DAT-09", "試算・仮置きの値は札ではなく source に「試算の前提: 開発者 800 名 × …」のように書く")
        if re.search(r"[\r\n\v]", msg):
            add("ERROR", no, "MSG-14", "メッセージに改行がある。改行は入れず、枠の幅で自然に折り返す")
        if _LAYOUT_TALK.search(MARK.sub(r"\1", msg)):
            add("WARN", no, "MSG-15", "メッセージが構成の説明になっている（「左に〜」「下表の通り」）。結論と解釈を書く")
        texts = [title, msg] + list(_strings(s.get("panes") or [])) + [s.get("source") or ""]
        joined = " ".join(texts)
        is_case = s.get("story_step") == "事例" or bool(mods & {"M-CASELIST", "M-CASE"}) or re.search(r"実績|事例", title)
        is_plan = s.get("story_step") == "計画" or "M-GANTT" in mods or re.search(r"スケジュール|ロードマップ", title)
        dates = _ym(" ".join(list(_strings(s.get("panes") or []))))
        if is_case and dates:
            for y, mo, raw in dates:
                for name, d in anchors:
                    if (y, mo) < d:
                        add("ERROR", no, "DATE-01", f"実績・事例の時期「{raw}」が {name} の開始（{d[0]}年{d[1]}月）より前。"
                            "題材の提供開始日を調べ直し、時期をそれ以降にする")
                        break
                if as_of and (y, mo) > as_of and not re.search(r"計画|予定|見込", joined):
                    add("ERROR", no, "DATE-02", f"実績・事例の時期「{raw}」が作成日（{as_of[0]}年{as_of[1]}月）より後")
        if is_plan and dates and as_of:
            past = [raw for y, mo, raw in dates if (y, mo) < as_of]
            if past and min(dates)[:2] < as_of:
                add("WARN", no, "DATE-03", f"スケジュールの時期「{past[0]}」が作成日（{as_of[0]}年{as_of[1]}月）より前")
        for p in s.get("panes") or []:
            if p.get("module") in ("M-TABLE", "M-MATRIX-SYM"):
                vague = [c for c in p.get("columns") or [] if isinstance(c, str) and c.strip() in _VAGUE_COLS]
                if vague:
                    add("WARN", no, "TBL-01", f"表の列名が曖昧（{'・'.join(vague)}）。列の中身を表す名前にする（一列一意）")
        nums = [m.group(1) for t in texts for m in _BIG_NUM.finditer(MARK.sub(r"\1", t))
                if not (len(m.group(1)) == 4 and 1990 <= int(m.group(1)) <= 2100)]
        if nums:
            add("WARN", no, "NUM-01", f"桁区切りの無い数（{'・'.join(nums[:3])}）。1,000 以上は 3 桁ごとにカンマを入れる")
    if dt in ("proposal", "report") and len(body) >= 10:
        mx = sum(1 for _, s in body if s.get("density") == "max")
        hi = sum(1 for _, s in body if s.get("density") in ("high", "max"))
        if mx == 0:
            add("ERROR", None, "DENS-02", "細かい詳細ページ（density \"max\"、本文 600〜900 字）が 1 枚も無い。提案書・報告書には"
                "現状分析の詳細・課題×打ち手・施策一覧・フェーズ別の実施事項×成果物・効果の内訳と前提などを 2 枚以上入れる")
        elif mx < 2 or hi / len(body) < 0.4:
            add("WARN", None, "DENS-02", f"詳細ページが少ない（max {mx} 枚・high 以上 {hi}/{len(body)} 枚）。max を 2 枚以上、"
                "high 以上を本文の 4 割以上にする")


def _check_skeleton(add, no, s, skeletons):
    sid = s["skeleton"]
    sk = skeletons.get(sid)
    if sk is None:
        add("ERROR", no, "SKELETON", f"骨格 {sid} が grammar/skeletons.json に無い")
        return
    c = s.get("content") or {}
    for i, rp in enumerate(sk.get("repeat", [])):
        key = "units" if i == 0 else f"units{i + 1}"
        items = c.get(key) or []
        if not items:
            add("ERROR", no, "SKELETON", f"{sid}: {key} が空（{rp['min']}〜{rp['max']} 個、項目 {list(rp.get('unit_fields', {}))}）")
            continue
        if not (rp["min"] <= len(items) <= rp["max"]):
            add("WARN", no, "SKELETON", f"{sid}: {key} は {rp['min']}〜{rp['max']} 個（現在 {len(items)}）")
        for fld, pos in rp.get("unit_fields", {}).items():
            sh = sk["shapes"][rp["units"][0][pos]]
            slot = sk["slots"].get(sh.get("slot")) if sh.get("slot") else None
            for k, it in enumerate(items):
                v = it.get(fld)
                if v in (None, "", []):
                    add("WARN", no, "SKELETON", f"{sid}: {key}[{k}].{fld} が空")
                elif slot:
                    n = len(MARK.sub(r"\1", "".join(v) if isinstance(v, list) else str(v)))
                    if n > slot.get("fit", slot.get("cap", 99)) * 1.25 + 4:
                        add("WARN", no, "CAPACITY", f"{sid}: {key}[{k}].{fld} が長い（{n}字 / 目安 {slot.get('fit')}字）")
    for name, f in sk.get("fixed", {}).items():
        v = c.get(name)
        if v in (None, "", [], {}):
            add("WARN", no, "SKELETON", f"{sid}: {name}（{f.get('role')}）が空")
        elif f.get("cap") and isinstance(v, (str, list)):
            slot = sk["slots"].get(sk["shapes"][f["shape"]].get("slot"), {})
            n = len(MARK.sub(r"\1", "".join(v) if isinstance(v, list) else v))
            if n > slot.get("fit", f["cap"]) * 1.25 + 4:
                add("WARN", no, "CAPACITY", f"{sid}: {name} が長い（{n}字 / 目安 {slot.get('fit')}字）")


def summarize(outline):
    contents = [s for s in outline.get("slides", []) if s.get("type", "content") == "content"]
    sigs = [signature(s) for s in contents]
    mods = {p.get("module") for s in contents for p in s.get("panes", [])}
    grids = {s.get("grid") for s in contents}
    max_run, run = 1, 1
    for a, b in zip(sigs, sigs[1:]):
        run = run + 1 if a == b else 1
        max_run = max(max_run, run)
    return {"body_slides": len(contents), "distinct_compositions": len(set(sigs)),
            "repeat_rate": round(1 - len(set(sigs)) / max(len(sigs), 1), 3), "max_consecutive": max_run if sigs else 0,
            "distinct_modules": len(mods), "distinct_grids": len(grids),
            "sequences": [q.get("id") for q in outline.get("sequences", [])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outline")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    with open(_paths.check_path(a.outline), encoding="utf-8") as f:
        ol = json.load(f)
    iss = check(ol)
    summ = summarize(ol)
    if a.json:
        print(json.dumps({"summary": summ, "issues": iss}, ensure_ascii=False, indent=1))
    else:
        for i in iss:
            where = f"#{i['slide']}" if i["slide"] else "deck"
            print(f"[{i['level']}] {where:<5} {i['rule']:<9} {i['msg']}")
        n_err = sum(i["level"] == "ERROR" for i in iss)
        n_warn = sum(i["level"] == "WARN" for i in iss)
        print(f"--- ERROR {n_err} / WARN {n_warn} / summary {json.dumps(summ, ensure_ascii=False)}")
    sys.exit(1 if any(i["level"] == "ERROR" for i in iss) else 0)


if __name__ == "__main__":
    main()
