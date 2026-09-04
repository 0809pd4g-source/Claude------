# -*- coding: utf-8 -*-
r"""計算エンジンが画面（UI）側に依存していないかを、**AST**で見る検査。

**なぜ作ったか（2026-08-31）**
検証スクリプトはHTMLの `<script>` から `/* 状態 */` の手前までを切り出して動かす。
そこから後ろの関数・可変のUI状態を触ると `not defined` で落ちる。
同じ混線が v19・v21・v22 と3回再発したので、機械で洗うことにした。

**v23でASTへ移行した理由（外部レビューの指摘）**
初版は「行頭（列0）の `function` 宣言だけ」を正規表現で見ていた。
これでは次を取りこぼす。

  - アロー関数・関数式（v22のエンジン領域にも `yen2man`・`fmtMan`・`fmtMan1`・
    `fmtYen`・`clone`・`num` の6件があった）
  - 入れ子の関数
  - `const f = render; f()` のような別名経由
  - `globalThis["document"]` のような添字経由
  - オブジェクト／クラスのメソッド

**この検査の限界（先に書く）**
- `eval` や動的に組み立てた名前は追えない。
- 別名は「UI関数をそのまま代入した」形だけを見る（関数を返す関数などは追わない）。
- 「0件だから正しい」ではなく「見えている範囲では問題がない」と読むこと。

使い方:
  python 03_scripts/check_engine_boundary.py 02_output/xxx.html
  python 03_scripts/check_engine_boundary.py --selftest   # 負試験6種
"""
import io
import re
import sys
from pathlib import Path

import esprima

ROOT = Path(__file__).resolve().parent.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# エンジンから触ってはいけないもの（画面・保存領域・可変のUI状態）
FORBIDDEN = {
    "document", "window", "globalThis", "localStorage", "sessionStorage",
    "alert", "confirm", "prompt", "navigator", "location", "matchMedia",
    "requestAnimationFrame", "getComputedStyle",
    # 可変のUI状態（呼び出しの外で変わるので、引数で渡すこと）
    "SIM", "PLANS", "TAB", "VIEW_REAL", "VIEW_MONTHLY",
    "CF_ONEYEAR", "CF_YEAR", "EDU_ONEYEAR", "EDU_YEAR",
}
# 例外（理由を必ず書くこと）
ALLOW = set()


def pick_html():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    cands = [p for p in (ROOT / "02_output").glob("*_v*.html") if "汎用版" in p.name]
    if not cands:
        raise SystemExit("汎用版のHTMLが 02_output に見つかりません")
    return max(cands, key=lambda p: int(re.search(r"_v(\d+)\.html$", p.name).group(1)))


def biggest_script(html):
    """いちばん大きい `<script>` の中身と、HTML内での開始位置を返す。"""
    best = None
    for m in re.finditer(r"<script>(.*?)</script>", html, re.S):
        if best is None or len(m.group(1)) > len(best.group(1)):
            best = m
    if best is None:
        raise SystemExit("<script> が見つかりません")
    return best.group(1), best.start(1)


def node_kids(node):
    for k in dir(node):
        if k.startswith("_") or k in ("type", "loc", "range", "toDict"):
            continue
        try:
            v = getattr(node, k)
        except Exception:
            continue
        if isinstance(v, list):
            for x in v:
                if hasattr(x, "type"):
                    yield k, x
        elif hasattr(v, "type"):
            yield k, v


FUNC_TYPES = {"FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"}


def normalize_modern(src):
    """esprima(Python版)が解釈できない新しい構文を、**文字数を変えずに**均す。

    ★オプショナルチェーン `a?.[k]` / `a?.b` と論理代入 `??=` `||=` `&&=` は
      esprima 4系が解釈できない。この検査が見たいのは**識別子の参照**だけなので、
      意味の同じ形へ置き換えて構わない。
    ★**長さを変えない**こと。範囲（range）で境界の前後を判定しているため、
      1文字でもずれると engine/UI の判定が狂う。
    """
    src = src.replace("?.[", "  [").replace("?.(", "  (")
    src = re.sub(r"\?\.(?=[A-Za-z_$])", " .", src)
    src = src.replace("??=", "|| ").replace("||=", "|| ").replace("&&=", "&& ")
    src = re.sub(r"(?<=\d)_(?=\d)", "0", src)      # 数値区切り 1_000
    return src


def analyze(script, boundary_off, engine_start=0):
    """関数を全部集め、エンジン側（engine_start〜境界）から見た違反を返す。"""
    tree = esprima.parseScript(normalize_modern(script), loc=True, range=True,
                               tolerant=True)

    funcs = []          # {name, start, engine, node}
    def name_of(node, parent_key, holder):
        if getattr(node, "id", None) is not None:
            return node.id.name
        return holder

    def walk(node, holder=None):
        if node.type in FUNC_TYPES:
            nm = name_of(node, None, holder)
            funcs.append({"name": nm, "start": node.range[0],
                          "engine": engine_start <= node.range[0] < boundary_off,
                          "node": node})
        # 変数宣言 `const f = () => …` は名前を子へ渡す
        if node.type == "VariableDeclarator" and getattr(node, "id", None) is not None:
            nm = getattr(node.id, "name", None)
            for k, kid in node_kids(node):
                walk(kid, nm if k == "init" else holder)
            return
        if node.type in ("Property", "MethodDefinition"):
            key = getattr(node, "key", None)
            nm = getattr(key, "name", None) or getattr(key, "value", None)
            for k, kid in node_kids(node):
                walk(kid, nm if k == "value" else holder)
            return
        for _k, kid in node_kids(node):
            walk(kid, holder)

    walk(tree)

    engine_names = {f["name"] for f in funcs if f["engine"] and f["name"]}
    ui_names = {f["name"] for f in funcs if not f["engine"] and f["name"]} - engine_names

    findings = []

    def line_of(node):
        return node.loc.start.line

    def scan_body(fn):
        """1つの関数の中で、ローカルに定義されていない禁止識別子・UI関数参照を探す。"""
        local = set()
        for p in (getattr(fn["node"], "params", None) or []):
            for nm in re.findall(r"[A-Za-z_$][\w$]*", getattr(p, "name", "") or ""):
                local.add(nm)

        def collect_locals(node):
            if node.type in FUNC_TYPES and node is not fn["node"]:
                # 入れ子関数は別途 funcs に入っているので中身は見ない
                if getattr(node, "id", None) is not None:
                    local.add(node.id.name)
                return
            if node.type == "VariableDeclarator" and getattr(node.id, "name", None):
                local.add(node.id.name)
            for _k, kid in node_kids(node):
                collect_locals(kid)
        for _k, kid in node_kids(fn["node"]):
            collect_locals(kid)

        def visit(node):
            if node.type in FUNC_TYPES and node is not fn["node"]:
                return                       # 入れ子は自分の番で見る
            if node.type == "Identifier":
                nm = node.name
                if nm in ALLOW or nm in local:
                    return
                if nm in FORBIDDEN:
                    findings.append({"kind": "禁止識別子", "fn": fn["name"] or "(無名)",
                                     "line": line_of(node), "what": nm})
                return
            # ★UI関数は「呼んだ」「別名に代入した」ときだけ数える。
            #   ただの同名の変数（`r`・`sum` など1文字の局所変数がUI関数名と衝突する）
            #   まで数えると偽陽性だらけになる（2026-08-31に12件出した）。
            if node.type == "CallExpression":
                cal = node.callee
                if cal.type == "Identifier" and cal.name in ui_names                    and cal.name not in local and cal.name not in ALLOW:
                    findings.append({"kind": "画面側の関数を呼ぶ", "fn": fn["name"] or "(無名)",
                                     "line": line_of(node), "what": cal.name})
                else:
                    visit(cal)
                for a in (getattr(node, "arguments", None) or []):
                    visit(a)
                return
            if node.type in ("VariableDeclarator", "AssignmentExpression"):
                rhs = getattr(node, "init", None) or getattr(node, "right", None)
                if rhs is not None and rhs.type == "Identifier"                    and rhs.name in ui_names and rhs.name not in local:
                    findings.append({"kind": "画面側の関数を別名に代入", "fn": fn["name"] or "(無名)",
                                     "line": line_of(node), "what": rhs.name})
                for _k, kid in node_kids(node):
                    if kid is not rhs:
                        visit(kid)
                if rhs is not None and rhs.type != "Identifier":
                    visit(rhs)
                return
            if node.type == "MemberExpression":
                # `obj.push` の `push` は**プロパティ名**であって識別子の参照ではない。
                # ここを数えると `sum`・`min`・`row` などが大量に誤検出される
                # （2026-08-31にこれで14件の偽陽性を出した）。
                visit(node.object)
                if getattr(node, "computed", False):
                    prop = node.property
                    # `globalThis["document"]` のような添字経由は見る
                    if prop.type == "Literal" and isinstance(getattr(prop, "value", None), str) \
                       and prop.value in FORBIDDEN:
                        findings.append({"kind": "添字経由", "fn": fn["name"] or "(無名)",
                                         "line": line_of(node), "what": prop.value})
                    else:
                        visit(prop)
                return
            if node.type == "Property" and not getattr(node, "computed", False):
                # `{sum: 1}` のキーも参照ではない
                visit(node.value)
                return
            for _k, kid in node_kids(node):
                visit(kid)

        for _k, kid in node_kids(fn["node"]):
            visit(kid)

    for fn in funcs:
        if fn["engine"]:
            scan_body(fn)

    return funcs, engine_names, ui_names, findings


def engine_start(script):
    """エンジン領域の開始位置。

    ★冒頭の「エラーの見える化」ブロックは `document` / `window` を使う**画面側の下ごしらえ**で、
      即時実行関数として閉じている。位置だけで見るとエンジンに入ってしまうため、
      その直後の `"use strict";` を開始点にする。
      （検証スクリプトが切り出す範囲もここから先が実質のエンジン。）
    """
    m = re.search(r'^"use strict";', script, re.M)
    return m.end() if m else 0


def report(html_path, quiet=False):
    html = html_path.read_text(encoding="utf-8")
    script, script_off = biggest_script(html)
    m = re.search(r"/\* =+\s*\n\s*状態\s*\n\s*=+ \*/", html)
    if not m:
        raise SystemExit("`/* 状態 */` の区切りが見つかりません")
    boundary_off = m.start() - script_off
    funcs, engine_names, ui_names, findings = analyze(script, boundary_off, engine_start(script))
    if quiet:
        return findings

    print(f"エンジン／画面の境界の検査（AST）: {html_path.name}")
    print("=" * 78)
    print(f"境界（`/* 状態 */`）: HTML {html[:m.start()].count(chr(10)) + 1} 行目")
    eng = [f for f in funcs if f["engine"]]
    arrows = [f for f in eng if f["node"].type != "FunctionDeclaration"]
    print(f"エンジン側の関数: {len(eng)}件（うちアロー・関数式 {len(arrows)}件）"
          f" ／ 画面側の関数: {len(funcs) - len(eng)}件")

    print("\n" + "-" * 78)
    print("エンジンから、画面側の関数・DOM・保存領域・可変のUI状態を触っていないか")
    print("-" * 78)
    if not findings:
        print("OK  0件")
    else:
        print(f"NG  {len(findings)}件")
        seen = set()
        for f in findings:
            key = (f["fn"], f["what"], f["kind"])
            if key in seen:
                continue
            seen.add(key)
            print(f"  script {f['line']:>6}行  {f['fn']}() が `{f['what']}` を参照（{f['kind']}）")

    print("\n" + "=" * 78)
    print("※ ASTで見ていますが、`eval` や動的に組み立てた名前は追えません。")
    print("   別名は「UI関数をそのまま代入した」形だけを見ます。")
    print("   『0件だから正しい』ではなく『見えている範囲では問題がない』と読んでください。")
    print("   ★負試験は `--selftest` で6種類を流せます。")
    return findings


SELFTESTS = [
    ("アロー関数からdocument",
     "const yen2man = v => v / MAN;", "const yen2man = v => (document.title, v / MAN);"),
    ("入れ子関数からlocalStorage",
     "function livingScale(n){", "function livingScale(n){ (function(){ localStorage.getItem('x'); })();"),
    ("別名経由でUI関数を呼ぶ",
     "function headcount(P){", "function headcount(P){ const f = render; f();"),
    ("添字経由でdocumentを取る",
     "function kokuminNenkin(age", "function kokuminNenkin(age){ globalThis['document']; }\nfunction __unused_kn(age"),
    ("関数式から可変のUI状態を読む",
     "const clone = o =>",
     "const clone = function(o){ return SIM && o; }, __clone2 = o =>"),
    ("宣言関数からdocument",
     "function livingScale(n){", "function livingScale(n){ document.title;"),
]


def selftest(html_path):
    src = html_path.read_text(encoding="utf-8")
    import tempfile
    print("負試験（壊したときに検出できるか）")
    print("=" * 78)
    base = report(html_path, quiet=True)
    print(f"  基準線（無改変）: {len(base)}件  "
          + ("OK 0件" if not base else "NG ここが0でないと負試験の意味がない"))
    if base:
        return 1
    ng = 0
    for name, old, new in SELFTESTS:
        if src.count(old) < 1:
            print(f"  {name}: SKIP（アンカーが見つからない）")
            ng += 1
            continue
        broken = src.replace(old, new, 1)
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                         encoding="utf-8") as f:
            f.write(broken)
            tmp = Path(f.name)
        try:
            found = report(tmp, quiet=True)
        except Exception as e:
            found = []
            print(f"  {name}: 解析に失敗 NG（{type(e).__name__}: {e}）")
        finally:
            tmp.unlink(missing_ok=True)
        ok = len(found) > 0
        print(f"  {name}: {'検出 OK' if ok else '見逃し NG'}（{len(found)}件）")
        if not ok:
            ng += 1
    print("=" * 78)
    print("6種すべて検出できて、はじめてこの検査を信用できます。")
    return 1 if ng else 0


if __name__ == "__main__":
    HTML = pick_html()
    if "--selftest" in sys.argv:
        sys.exit(selftest(HTML))
    sys.exit(1 if report(HTML) else 0)
