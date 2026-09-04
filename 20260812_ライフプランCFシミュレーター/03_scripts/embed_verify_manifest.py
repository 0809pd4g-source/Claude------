# -*- coding: utf-8 -*-
"""検証を実行し、その結果を成果物のHTMLに埋め込む。

なぜ要るか
----------
HTMLには「参照PDFと一致しています」と書いてあるが、照合しているのは
別ファイルのPythonスクリプトで、受け取る人はHTML1つしか持っていない。
つまり**その一文を信じるしかない**状態だった。
しかもその一文は手で書いていたので、計算を変えたのに記述だけ古く残った
（v22で住民税を前年計上に変えたのに、検証の記述は更新していなかった）。

そこで、検証スクリプトの出力をそのままHTMLへ埋め込む。
手で書かないので古くならず、受け取った人も
「いつ・何件・どういう結果か」を画面で確認できる。

何を埋め込むか
--------------
検証日時／対象ファイル／版／各スクリプトの合格・既知差異・失敗の件数／
基準データ（参照PDFの期待値）のSHA-256／エンジンのSHA-256。

版のずれの検知
--------------
埋め込んだ版（VERIFY.version）と実行時の VERSION.tag を画面で比べる。
違えば「この検証結果は別の版のものです」と出る。
版を上げたのに検証し直していない、という取り違えをここで捕まえる。

使い方
------
    python 03_scripts/embed_verify_manifest.py [対象HTML]

引数がなければ 02_output のいちばん新しい版を対象にする。
"""
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "02_output"
SCRIPTS = ROOT / "03_scripts"

# 実行する検証。name は画面に出す見出し。
CHECKS = [
    {"name": "スモークテスト", "file": "smoke_test.py",
     "what": "全画面の描画・制度の検算・恒等式・古い保存データからの復旧"},
    {"name": "参照PDFの4パターン照合", "file": "verify_4patterns.py",
     "what": "FP資料の①〜④について、各年の収支・資産・ローン残高を突き合わせ"},
    {"name": "参照PDF①の詳細照合", "file": "verify_against_pdf.py",
     "what": "償還表・給与推計・収入・子ども関連費・税額まで細かく突き合わせ"},
]


def target_html(argv):
    if len(argv) > 1:
        return Path(argv[1])
    # 「汎用版」は別系統なので対象にしない。
    # 名前順で最後に来るため、指定しないと誤ってそちらに埋め込んでしまう。
    cands = [x for x in sorted(OUT.glob("*_v[0-9]*.html"))
             if "汎用版" not in x.name]
    if not cands:
        sys.exit("02_output に対象のHTMLがありません")
    # 版番号の大きいものを選ぶ（v9 と v10 を名前順で比べると v9 が後になるため）
    def vnum(path):
        import re as _re
        m = _re.search(r"_v(\d+)\.html$", path.name)
        return int(m.group(1)) if m else -1
    return max(cands, key=vnum)


def run(script):
    """検証を実行して、標準出力と終了コードを返す。"""
    r = subprocess.run([sys.executable, str(SCRIPTS / script)],
                       capture_output=True, cwd=str(ROOT))
    txt = r.stdout.decode("utf-8", errors="replace")
    return txt, r.returncode


def parse(txt):
    """出力から件数を読む。スクリプトごとに書式が違うので両方に対応する。"""
    res = {"ok": None, "known": None, "ng": None, "verdict": None}
    m = re.search(r"一致\s*(\d+)\s*件(?:\s*／\s*既知の差異\s*(\d+)\s*件)?"
                  r"\s*／\s*不一致\s*(\d+)\s*件", txt)
    if m:
        res["ok"] = int(m.group(1))
        res["known"] = int(m.group(2)) if m.group(2) else 0
        res["ng"] = int(m.group(3))
    m2 = re.search(r"結果:\s*(\S+)", txt)
    if m2:
        res["verdict"] = m2.group(1)
    return res


def sha(b):
    return hashlib.sha256(b).hexdigest()


def engine_hash(html_text):
    """**`<script>` ブロック全体**のハッシュ（計算エンジン部分だけではない）。
    埋め込んだ VERIFY 自体は除く（埋め込むたびに値が変わってしまうため）。

    ★名前が `engineSha` なので「計算エンジンの指紋」と読めるが、実際は画面側も含む。
      画面だけを直しても値が変わる。2026-09-01に、読み上げ名の修正（UIのみ）で
      値が変わったのを見て**計算を壊したかと疑った**（PDF照合は56・12・0で不変だった）。
      名前と中身が違うほうが、値がずれていることより危ない。"""
    js = re.search(r"<script>(.*?)</script>", html_text, re.S).group(1)
    js = re.sub(r"const VERIFY = \{.*?\};\n", "", js, flags=re.S)
    return sha(js.encode("utf-8"))


def main():
    html_path = target_html(sys.argv)
    text = html_path.read_text(encoding="utf-8")
    ver = re.search(r'const VERSION = \{tag:"([^"]+)", date:"([^"]+)"', text)
    if not ver:
        sys.exit("VERSION 定数が見つかりません")

    print(f"対象: {html_path.name}（{ver.group(1)}）\n")
    checks = []
    for c in CHECKS:
        print(f"  実行中: {c['file']} …", flush=True)
        txt, code = run(c["file"])
        p = parse(txt)
        checks.append({
            "name": c["name"], "script": c["file"], "what": c["what"],
            "ok": p["ok"], "known": p["known"], "ng": p["ng"],
            "verdict": p["verdict"], "exit": code,
        })
        got = (f"一致{p['ok']}／既知{p['known']}／不一致{p['ng']}"
               if p["ok"] is not None else (p["verdict"] or "?"))
        print(f"    → {got}（終了コード {code}）")

    # 基準データ（参照PDFの期待値が書かれた照合スクリプト）のハッシュ
    base = b"".join((SCRIPTS / c["file"]).read_bytes() for c in CHECKS)
    manifest = {
        "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "file": html_path.name,
        "version": ver.group(1),
        "checks": checks,
        "baselineSha": sha(base)[:16],
        "engineSha": engine_hash(text)[:16],
    }

    ref = ROOT / "04_reference"
    ref.mkdir(exist_ok=True)
    (ref / "verify_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    # ★`VERSION.file` を実物のファイル名へ書き戻す。
    #   手で書くと必ずずれる（v27はv26のまま2版ずれていた）。
    text, n_file = re.subn(r'(file:")[^"]*(")', r'\g<1>' + html_path.name + r'\g<2>', text, count=1)
    if n_file:
        print(f"  VERSION.file を {html_path.name} に同期しました")

    # HTMLへ埋め込む（既にあれば差し替える）
    block = "const VERIFY = " + json.dumps(manifest, ensure_ascii=False) + ";\n"
    if re.search(r"const VERIFY = \{.*?\};\n", text, re.S):
        text = re.sub(r"const VERIFY = \{.*?\};\n", block, text, flags=re.S)
        how = "差し替え"
    else:
        anchor = "const VERSION = {"
        i = text.index(anchor)
        text = text[:i] + block + text[i:]
        how = "新規挿入"
    html_path.write_text(text, encoding="utf-8")

    tot_ng = sum(c["ng"] or 0 for c in checks)
    bad = [c for c in checks if c["exit"] != 0]
    print(f"\n埋め込み{how}: {html_path.name}")
    print(f"  検証日時 {manifest['at']} ／ 基準データ {manifest['baselineSha']}"
          f" ／ スクリプト全体 {manifest['engineSha']}（画面の修正でも変わります）")
    print(f"  不一致の合計 {tot_ng} 件"
          + (f" ／ 異常終了 {len(bad)} 件" if bad else ""))
    print("\n" + ("OK すべて通りました" if tot_ng == 0 and not bad
                  else "★ 通っていない検証があります"))


if __name__ == "__main__":
    main()
