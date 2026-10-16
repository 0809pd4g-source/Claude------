"""
asset_search.py — アイコン・イラスト素材の意味検索。

素材の出どころ:
  - 組み込み:   <SKILL_DIR>/assets/illustrations/<ID>.png + asset_index.json + asset_tags.json（意味タグ）
                配布版は画像を assets/illustrations_*.zip にまとめてあり、初回に ~/.acnpptx/cache/ へ展開して使う
  - ユーザー抽出: ~/.acnpptx/extracted/<set>/images/<ID>.png + asset_index.json (+ asset_tags.json)
    → ID は "<set>:<ID>" で参照する

検索の流れ（外部の埋め込みモデルは使わない）:
  1. スライドのメッセージ・意図から検索語を作る（例: "顧客接点 スピード 信頼"）
  2. 同義語辞書（assets/synonyms.json）で展開し、タグ（概念・説明・用途・図形名キーワード）と照合して採点
  3. 上位 N 件のコンタクトシートを作る → Claude が画像を見て最終選択する（ユーザーには聞かない）

CLI:
  python asset_search.py "スピード 迅速 時間短縮" --top 20 --sheet cand.png [--kind icon] [--set NAME]
  python asset_search.py --show 0054 0123
"""

import argparse
import glob
import json
import os
import re
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

_CACHE = {}
_PNG_NAME = re.compile(r"[\w\-]+\.png")


def illustrations_dir():
    """組み込みイラストのフォルダ。assets/illustrations/ が無ければ illustrations_*.zip を DATA_DIR に展開して返す。"""
    if "illust" in _CACHE:
        return _CACHE["illust"]
    d = os.path.join(_paths.ASSETS_DIR, "illustrations")
    zips = sorted(glob.glob(d + "_*.zip"))  # 配布の 1 ファイル上限に収まるよう分割してある
    if not os.path.isdir(d) and zips:
        import shutil
        import uuid
        import zipfile
        d = _paths.check_path(os.path.join(_paths.ensure_data_dir("cache"), f"illustrations-{sum(map(os.path.getsize, zips))}"),
                              write=True)
        if not os.path.isdir(d):
            # mkdtemp は Windows で作成者限定の ACL を付け、他のツールから読めなくなるので使わない
            tmp = f"{d}.tmp-{uuid.uuid4().hex}"
            for z in zips:
                with zipfile.ZipFile(z) as zf:
                    for n in zf.namelist():
                        if _PNG_NAME.fullmatch(n):  # 平らな <ID>.png だけを展開（パスを含む名前は無視）
                            zf.extract(n, tmp)
            try:
                os.rename(tmp, d)
            except OSError:  # 並列実行で先に展開された
                shutil.rmtree(tmp, ignore_errors=True)
    _CACHE["illust"] = d
    return d


def _load_json(p, default):
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def _merge(index, tags, prefix, img_dir):
    out = {}
    for k, v in index.items():
        t = tags.get(k, {})
        out[f"{prefix}{k}"] = {
            "id": f"{prefix}{k}", "path": os.path.join(img_dir, f"{k}.png"),
            "keywords": v.get("keywords", []), "source": v.get("source", ""),
            "desc_ja": t.get("desc_ja", ""), "desc_en": t.get("desc_en", ""),
            "concepts": t.get("concepts_ja", []) + t.get("concepts_en", []),
            "uses": t.get("uses", []), "kind": t.get("kind", ""), "style": t.get("style", ""),
            "color": t.get("color", ""), "usable": t.get("usable", True),
            "w": v.get("width_px"), "h": v.get("height_px"),
        }
    return out


def load_assets(include_user=True):
    if "assets" in _CACHE:
        return _CACHE["assets"]
    a = _paths.ASSETS_DIR
    assets = _merge(_load_json(os.path.join(a, "asset_index.json"), {}),
                    _load_json(os.path.join(a, "asset_tags.json"), {}), "", illustrations_dir())
    if include_user and os.path.isdir(_paths.EXTRACTED_DIR):
        for d in sorted(glob.glob(os.path.join(_paths.EXTRACTED_DIR, "*"))):
            idx = _load_json(os.path.join(d, "asset_index.json"), None)
            if idx is None:
                continue
            tags = _load_json(os.path.join(d, "asset_tags.json"), {})
            assets.update(_merge(idx, tags, os.path.basename(d) + ":", os.path.join(d, "images")))
    _CACHE["assets"] = assets
    return assets


def asset_path(asset_id):
    a = load_assets().get(str(asset_id))
    if a:
        return _paths.check_path(a["path"])
    s, _, k = str(asset_id).rpartition(":")
    if not re.fullmatch(r"[\w\-]+", k) or (s and not _paths.is_safe_theme_name(s)):
        raise ValueError(f"invalid asset id: {asset_id!r}")
    if s:
        return _paths.check_path(os.path.join(_paths.EXTRACTED_DIR, s, "images", f"{k}.png"))
    return _paths.check_path(os.path.join(illustrations_dir(), f"{k}.png"))


def _synonyms():
    if "syn" not in _CACHE:
        groups = _load_json(os.path.join(_paths.ASSETS_DIR, "synonyms.json"), {}).get("groups", [])
        m = {}
        for g in groups:
            for w in g:
                m.setdefault(w.lower(), set()).update(x.lower() for x in g)
        _CACHE["syn"] = m
    return _CACHE["syn"]


def expand(query):
    terms = [t.lower() for t in re.split(r"[\s、,，・/／]+", query) if t]
    syn = _synonyms()
    out = {}
    for t in terms:
        out[t] = 1.0
        for s in syn.get(t, ()):
            out.setdefault(s, 0.6)
        # 検索語に含まれる日本語の同義語キーも拾う（例: "顧客接点" → "顧客"）。英字は部分一致させない
        for k, group in syn.items():
            if len(k) >= 2 and not k.isascii() and k in t and k != t:
                for s in group:
                    out.setdefault(s, 0.4)
    return out


def _bigrams(s):
    s = re.sub(r"\s+", "", s.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def search(query, top=20, kind=None, set_name=None, include_unusable=False):
    """[(score, asset_dict)] を返す。"""
    q = expand(query)
    res = []
    for a in load_assets().values():
        if not include_unusable and a["usable"] is False:
            continue
        if kind and a["kind"] and a["kind"] != kind:
            continue
        if set_name is not None and not a["id"].startswith(f"{set_name}:"):
            continue
        concepts = [c.lower() for c in a["concepts"]]
        uses = " ".join(a["uses"]).lower()
        desc = (a["desc_ja"] + " " + a["desc_en"]).lower()
        kws = [k.lower() for k in a["keywords"]]
        sc = 0.0
        words = set(re.findall(r"[a-z0-9]+", desc + " " + " ".join(concepts) + " " + " ".join(kws)))
        for t, wgt in q.items():
            if t.isascii() and len(t) <= 3:   # 短い英字（AI, EC 等）は単語一致のみ（goal / detail への誤一致を防ぐ）
                if t in concepts or t in words:
                    sc += 3 * wgt
                continue
            if t in concepts:
                sc += 3 * wgt
            elif any(t in c for c in concepts):
                sc += 2 * wgt
            if t in desc:
                sc += 2 * wgt
            if t in uses:
                sc += 1.5 * wgt
            if t in kws or any(t in k for k in kws):
                sc += 1 * wgt
        if sc == 0:   # 日本語の言い回し違いの救済（文字 bigram の重なり）
            qb = set().union(*[_bigrams(t) for t in q]) if q else set()
            ab = _bigrams(" ".join(a["concepts"]) + a["desc_ja"])
            ov = len(qb & ab)
            sc = 0.3 * ov if ov >= 2 else 0
        if sc > 0:
            res.append((round(sc, 2), a))
    res.sort(key=lambda x: (-x[0], x[1]["id"]))
    return res[:top]


def make_sheet(results, out_path, cols=5, cell=200):
    from contact_sheet import make_sheet as _ms
    imgs = [a["path"] for _, a in results]
    labels = [a["id"] for _, a in results]
    im = _ms(imgs, labels, cols=cols, cell=cell)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    im.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--kind")
    ap.add_argument("--set", dest="set_name")
    ap.add_argument("--sheet", help="候補のコンタクトシート出力先 PNG")
    ap.add_argument("--show", nargs="*")
    a = ap.parse_args()
    a.sheet = a.sheet and _paths.check_path(a.sheet, write=True)
    if a.show:
        assets = load_assets()
        for i in a.show:
            print(json.dumps(assets.get(i, {"id": i, "error": "not found"}), ensure_ascii=False))
        return
    res = search(a.query, a.top, a.kind, a.set_name)
    for sc, x in res:
        print(f"{x['id']}\t{sc}\t{x['desc_ja'] or ', '.join(x['keywords'])}\t{'/'.join(x['concepts'][:5])}")
    if a.sheet and res:
        print("sheet:", make_sheet(res, a.sheet))
    if not res:
        print("該当なし（語を言い換える・上位概念にする・--kind を外す）", file=sys.stderr)


if __name__ == "__main__":
    main()
