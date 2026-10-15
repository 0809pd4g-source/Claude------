# -*- coding: utf-8 -*-
"""ONS回答の下調べ（最小版）

台帳②（ONS問い合わせ管理台帳・厚労省エスカレ分）の「ONS問い合わせ」シートと
技術解説書2.1.0版の原本PDFから、対象の件ごとに下調べのひな形MDを1本出す。

- 台帳は一時フォルダにコピーしてから読み取りのみで開く（保存の処理は書いていない）。
  実行前後で台帳のSHA-256を比べ、変わっていればエラーにする。
- 外部ネットワークは使わない（PyMuPDF・openpyxl・sqlite3・標準ライブラリだけ）。
- 結論・言い回しは人が書く。このスクリプトは材料を並べるだけ。

使い方（README.md 参照）:
  python ons_shitashirabe.py --ledger <台帳xlsx> --round 20261020 [--ids 539,540] [--out <出力フォルダ>]

設計: 07_ONS問合せ対応/ONS問合せ会議/_wip/20261009_ONS回答下調べ自動化_設計案_v1.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import math
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# cp932のコンソールでも絵文字（✅⚠️❌）・機種依存文字で止まらないように
for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TOOL_VERSION = "v1（最小版・2026-10-15）"

HERE = Path(__file__).resolve().parent                     # .../ONS問合せ会議/00_共通/03_scripts
MEETING_DIR = HERE.parent.parent                           # .../ONS問合せ会議
AGENT_DIR = MEETING_DIR.parent.parent                      # .../_agent
CACHE_DIR = HERE / "_cache"
DEFAULT_LEDGER = Path.home() / "Downloads" / "(原本)【電カル共有】ONS問い合わせ管理台帳（厚労省エスカレ分）.xlsx"
DEFAULT_PDF_DIR = AGENT_DIR / "02_仕様・技術" / "20260723_技術解説書2.1.0版" / "01_input"
SHEET_NAME = "ONS問い合わせ"
DOC_LABEL = "技術解説書2.1.0版"

# ---------------------------------------------------------------------------
# 文字の正規化・2文字単位の索引
# ---------------------------------------------------------------------------
_STRIP_RE = re.compile(r"[\s、。，,．\.・「」『』（）()\[\]【】{}:：;；\"'“”‘’⚫◼●■□◆◇※＊*\-‐―─－~〜～>＞<＜→⇒=＝/／|｜!！?？]")


def norm(s: str) -> str:
    """照合用：NFKC・小文字化し、空白・句読点・括弧・記号を除く。"""
    s = unicodedata.normalize("NFKC", s or "").lower()
    return _STRIP_RE.sub("", s)


def bigrams(s: str) -> list[str]:
    n = norm(s)
    return [n[i:i + 2] for i in range(len(n) - 1)]


class TfIdf:
    """2文字単位のTF-IDF（日本語の辞書なしで使える）。"""

    def __init__(self, docs: list[str]):
        self.n = len(docs)
        self.df: Counter = Counter()
        toks = [bigrams(d) for d in docs]
        for t in toks:
            self.df.update(set(t))
        self.vecs = [self.vec_from_tokens(t) for t in toks]

    def idf(self, g: str) -> float:
        return math.log((self.n + 1) / (self.df.get(g, 0) + 1)) + 1.0

    def vec_from_tokens(self, toks: list[str]) -> dict:
        tf = Counter(toks)
        v = {g: (1 + math.log(c)) * self.idf(g) for g, c in tf.items()}
        nrm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {g: x / nrm for g, x in v.items()}

    def vec(self, text: str) -> dict:
        return self.vec_from_tokens(bigrams(text))

    @staticmethod
    def cos(a: dict, b: dict) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(g, 0.0) for g, x in a.items())


# ---------------------------------------------------------------------------
# 台帳の読み込みと往復の分割
# ---------------------------------------------------------------------------
@dataclass
class Segment:
    kind: str          # 質問 / 基金コメント / 厚労省回答 / 前置き など
    round: int | None
    date: str
    heading: str
    text: str


@dataclass
class Record:
    no: int
    category: str
    date: str          # 起票日 YYYY-MM-DD
    inc: str
    asker: str
    subject: str
    j: str
    k: str
    l: str
    m: str
    n: str
    o: str
    memo_s: str
    memo_t: str
    j_segs: list = field(default_factory=list)
    k_segs: list = field(default_factory=list)
    l_segs: list = field(default_factory=list)

    @property
    def latest_round(self) -> int:
        rs = [s.round for s in self.j_segs if s.kind == "質問" and s.round]
        return max(rs) if rs else 1

    def latest_question(self) -> Segment | None:
        qs = [s for s in self.j_segs if s.kind == "質問"]
        if not qs:
            return None
        return max(qs, key=lambda s: (s.round or 0))

    def latest_k(self) -> Segment | None:
        ks = [s for s in self.k_segs if s.kind == "基金コメント"]
        if not ks:
            return None
        return max(ks, key=lambda s: (s.round or 0))

    @property
    def done(self) -> bool:
        return self.m.startswith("ONS回答済") or self.m.startswith("取り下げ")


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, dt.datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    # CSVから貼られた行は全体が "..." で囲まれていることがある
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].replace('""', '"')
    return s


_DATE_IN = r"\s*[（(]\s*([^）)\n]{0,30}?)\s*[）)]"
J_Q_RE = re.compile(r"【お問(?:い)?合(?:わ)?せ\s*(\d+)\s*回目】(?:" + _DATE_IN + ")?")
J_ANS_RE = re.compile(r"【お問(?:い)?合(?:わ)?せ\s*(\d+)\s*回目に対する([^】]{0,20}?)回答】(?:" + _DATE_IN + ")?")
K_COMMENT_RE = re.compile(
    r"【(?:お問(?:い)?合(?:わ)?せ\s*(\d+)\s*回目に対する)?\s*((?:支払基金|DX審査支払機構|ND|FJ|NTTD|ONS)[^】]{0,8}?(?:コメント|回答))(?:[_ー\-]?(\d{8}))?】(?:" + _DATE_IN + ")?")
K_DONE_RE = re.compile(r"【ONS回答済[^】]{0,20}】")
# そのほかの回答・コメントの見出し（「【お問合せ1,2回目に対するONS回答】」「【厚労省コメント_20250101】」など）。「【回答案…】」は機構コメントの中身なので除く
K_OTHER_RE = re.compile(r"【(?!回答案)[^】]{0,30}?(?:回答|コメント)(?:[_ー\-]?\d{8})?】(?:" + _DATE_IN + ")?")
L_ANS_RE = re.compile(
    r"【(?:(?:お問(?:い)?合(?:わ)?せ|問い合わせ)\s*(\d+)\s*回目(?:に対する|への)\s*(?:厚労省様?)?(?:回答|コメント)"
    r"|厚労省回答|(\d+)回目の厚労省回答|更問\s*\d*\s*(?:回目)?への回答|[\d/]+更問の回答)】(?:" + _DATE_IN + ")?")
REQ_RE = re.compile(r"(回答案作成依頼|回答案確認依頼|回答方針確認依頼|方針確認依頼|作成依頼|確認依頼)")


def _split(text: str, patterns: list[tuple[re.Pattern, str]]) -> list[Segment]:
    hits = []
    for pat, kind in patterns:
        for m in pat.finditer(text):
            hits.append((m.start(), m.end(), kind, m))
    hits.sort(key=lambda h: h[0])
    # 重なりを除く
    clean, last_end = [], -1
    for h in hits:
        if h[0] >= last_end:
            clean.append(h)
            last_end = h[1]
    segs: list[Segment] = []
    if not clean:
        if text.strip():
            segs.append(Segment("見出しなし", None, "", "", text.strip()))
        return segs
    pre = text[:clean[0][0]].strip()
    if pre:
        segs.append(Segment("前置き", None, "", "", pre))
    for i, (s, e, kind, m) in enumerate(clean):
        nxt = clean[i + 1][0] if i + 1 < len(clean) else len(text)
        groups = [g for g in m.groups() if g]
        rnd = None
        date = ""
        rm = re.search(r"(\d{1,2}(?:\s*[,、・]\s*\d{1,2})*)\s*回目", m.group(0))
        if rm:
            rnd = max(int(x) for x in re.findall(r"\d+", rm.group(1)))   # 「1,2回目」は2
        dm = re.search(r"[（(]\s*([^）)]*)[）)]\s*$", m.group(0))
        if dm:
            date = dm.group(1)
        else:
            d8 = re.search(r"(\d{8})", m.group(0))
            date = d8.group(1) if d8 else ""
        segs.append(Segment(kind, rnd, date, m.group(0), text[e:nxt].strip()))
    return segs


def split_record(r: Record) -> None:
    r.j_segs = _split(r.j, [(J_Q_RE, "質問"), (J_ANS_RE, "回答（J列）")])
    r.k_segs = _split(r.k, [(K_COMMENT_RE, "基金コメント"), (K_DONE_RE, "ONS回答済の見出し"), (K_OTHER_RE, "回答・コメント")])
    r.l_segs = _split(r.l, [(L_ANS_RE, "厚労省回答")])


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


LOAD_WARNINGS: list[str] = []


def load_ledger(path: Path) -> list[Record]:
    import openpyxl  # 読み取り専用で使う。保存（save）は呼ばない
    tmpdir = Path(tempfile.mkdtemp(prefix="ons_ledger_"))
    try:
        tmp = tmpdir / "ledger_copy.xlsx"
        shutil.copy2(path, tmp)
        with warnings.catch_warnings():
            # 「Data Validation extension is not supported」は読み取りには影響しない（保存しないため）
            warnings.simplefilter("ignore")
            wb = openpyxl.load_workbook(tmp, read_only=True, data_only=True)
            if SHEET_NAME not in wb.sheetnames:
                raise SystemExit(f"シート「{SHEET_NAME}」が見つかりません: {wb.sheetnames}")
            ws = wb[SHEET_NAME]
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    head = [str(c or "") for c in rows[0]]

    def col(prefix: str, default: int) -> int:
        for i, h in enumerate(head):
            if h.startswith(prefix):
                return i
        return default

    c = dict(cat=col("カテゴリ", 0), no=col("#", 1), date=col("起票日", 2), inc=col("ID", 3),
             asker=col("問合せ者", 4), subj=col("件名", 8), j=col("問合せ内容", 9), k=col("要約・内部履歴", 10),
             l=col("回答案", 11), m=col("回答状況", 12), n=col("更新日付", 13), o=col("問い合わせ共有会", 14))
    # S・T列（見出しなしのメモ列）の位置を確かめる：R列が「ナレッジ化」で、S・T列の見出しが空であること
    LOAD_WARNINGS.clear()
    head += [""] * 25
    if not (head[17].startswith("ナレッジ") and not head[18].strip() and not head[19].strip()):
        LOAD_WARNINGS.append(
            f"台帳の列の並びが想定と違います（R列「{head[17]}」・S列「{head[18]}」・T列「{head[19]}」）。"
            "S・T列のメモが別の列を指している可能性があるので、台帳で確認してください")
    recs = []
    for row in rows[1:]:
        row = list(row) + [None] * 25
        try:
            no = int(str(row[c["no"]]).strip())
        except (TypeError, ValueError):
            continue
        r = Record(no=no, category=_cell(row[c["cat"]]), date=_cell(row[c["date"]])[:10], inc=_cell(row[c["inc"]]),
                   asker=_cell(row[c["asker"]]), subject=_cell(row[c["subj"]]), j=_cell(row[c["j"]]),
                   k=_cell(row[c["k"]]), l=_cell(row[c["l"]]), m=_cell(row[c["m"]]), n=_cell(row[c["n"]]),
                   o=_cell(row[c["o"]]), memo_s=_cell(row[18]), memo_t=_cell(row[19]))
        split_record(r)
        recs.append(r)
    return recs


# ---------------------------------------------------------------------------
# 技術解説書のページ索引（sqliteにキャッシュ）
# ---------------------------------------------------------------------------
@dataclass
class Page:
    pdf_index: int     # 1始まり
    printed: int       # 印刷上の番号
    headings: str
    context: str       # 直前までの「機能N：」見出し
    text: str


HEAD_RE = re.compile(r"^\s*(機能\d+[：:].{0,40}|表\s?\d+[\.．].{0,40}|図\s?\d+[\.．].{0,40}|[（(]\d+[）)]\s?.{2,40}|\d+\.\d+(?:\.\d+)?\s.{2,40})\s*$")


def find_pdf(pdf_arg: str | None) -> Path:
    if pdf_arg:
        return Path(pdf_arg)
    cands = sorted(DEFAULT_PDF_DIR.glob("*技術解説書*2.1.0*.pdf"))
    if not cands:
        raise SystemExit(f"技術解説書2.1.0版のPDFが見つかりません: {DEFAULT_PDF_DIR}（--pdf で指定）")
    return cands[0]


def build_pages(pdf: Path) -> list[Page]:
    import fitz
    doc = fitz.open(pdf)
    pages, ctx = [], ""
    for i in range(doc.page_count):
        t = doc[i].get_text()
        lines = [ln.strip() for ln in t.splitlines()]
        nonempty = [ln for ln in lines if ln]
        printed = int(nonempty[0]) if nonempty and nonempty[0].isdigit() else i + 1
        heads = []
        for j, ln in enumerate(lines):
            if HEAD_RE.match(ln):
                heads.append(ln)
            elif ln == "◼" and j + 1 < len(lines) and lines[j + 1]:
                heads.append("◼" + lines[j + 1])
        start_ctx = ctx
        for h in heads:
            if h.startswith("機能"):
                ctx = h
        pages.append(Page(i + 1, printed, " / ".join(heads[:4]), start_ctx, t))
    doc.close()
    return pages


def load_pages(pdf: Path) -> tuple[list[Page], str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = sha256(pdf)
    db = CACHE_DIR / "pages_index.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table if not exists meta(k text primary key, v text)")
    con.execute("create table if not exists pages(doc text, pdf_index int, printed int, headings text, context text, text text)")
    row = con.execute("select v from meta where k='pdf_sha256'").fetchone()
    if not row or row[0] != digest:
        pages = build_pages(pdf)
        con.execute("delete from pages")
        con.executemany("insert into pages values(?,?,?,?,?,?)",
                        [(DOC_LABEL, p.pdf_index, p.printed, p.headings, p.context, p.text) for p in pages])
        con.execute("insert or replace into meta values('pdf_sha256',?)", (digest,))
        con.execute("insert or replace into meta values('pdf_path',?)", (str(pdf),))
        con.commit()
    pages = [Page(*r) for r in con.execute(
        "select pdf_index, printed, headings, context, text from pages order by pdf_index")]
    con.close()
    return pages, digest


# ---------------------------------------------------------------------------
# ページ参照の取り出し（「技術解説書2.1.0版 P.132」など）
# ---------------------------------------------------------------------------
PAGE_REF_RE = re.compile(r"(?<![A-Za-z])[PpＰｐ]\s?[\.．]?\s?(\d{1,3})(?:\s?([-－〜~～])\s?[PpＰｐ]?[\.．]?\s?(\d{1,3}))?(?!\d)")
OTHER_DOCS = ["手引き", "記述仕様", "共通表", "運用マニュアル", "実装ガイド", "IG", "別紙", "記載一覧", "仕様書", "指針", "マニュアル", "ガイドライン", "患者サマリー編", "チェックリスト"]
VER_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)\s?版")


@dataclass
class PageRef:
    start: int
    end: int
    version: str        # "2.1.0" / 旧版の番号 / ""（版の書きなし）
    assumed: bool       # 版の書きがなく2.1.0版と推定した
    pos: int


def page_refs(text: str, rec_date: str = "") -> list[PageRef]:
    """技術解説書のページ参照を拾う。他の資料（手引き・記述仕様等）の参照は除く。"""
    out = []
    t = unicodedata.normalize("NFKC", text or "")
    # URLは資料名とページ番号の間を長く空けるので短くする（「手引き(https://…)のp.10」）
    t = re.sub(r"https?://\S+", "URL", t)
    for m in PAGE_REF_RE.finditer(t):
        a = int(m.group(1))
        b = int(m.group(3)) if m.group(3) else a   # 「P.132-133」の範囲。「P.95、P.177」は別々に拾う
        if b < a or b - a > 5:
            b = a
        win = t[max(0, m.start() - 60):m.start()]
        p_tech = win.rfind("技術解説書")
        p_other = max((win.rfind(d) for d in OTHER_DOCS), default=-1)
        if p_other > p_tech:
            continue
        if p_tech < 0:
            # 資料名の書きがないページ参照は、近くに他の資料名が無いときだけ技術解説書とみなす
            if p_other >= 0:
                continue
        vm = list(VER_RE.finditer(win[p_tech:] if p_tech >= 0 else ""))
        ver, assumed = "", False
        if vm:
            v = vm[-1].group(1)
            ver = "2.1.0" if v in ("2.1.0", "2.1") else v
        else:
            if rec_date >= "2026-06-01":
                ver, assumed = "2.1.0", True
        if 1 <= a <= 400:
            out.append(PageRef(a, b, ver, assumed, m.start()))
    return out


def tech_pages(text: str, rec_date: str = "", only_explicit_tech: bool = False) -> set[int]:
    s = set()
    for r in page_refs(text, rec_date):
        if r.version == "2.1.0":
            s.update(range(r.start, r.end + 1))
    return s


# ---------------------------------------------------------------------------
# 抜粋の照合
# ---------------------------------------------------------------------------
EXCERPT_HEAD_RE = re.compile(r"【\s*(?:※\s*\d*\s*)?参考\s*[：:]\s*([^】]*?)抜粋\s*】")
DASH_LINE_RE = re.compile(r"^\s*[-－ー―─]{8,}\s*$", re.M)


@dataclass
class Excerpt:
    source: str        # どの列・どのブロックか
    doc: str           # 見出しの資料名部分
    pages: list[int]
    version: str
    text: str


@dataclass
class CheckResult:
    item: Excerpt
    status: str        # ✅ ⚠️ ❌ ―
    found_pages: list[int]
    detail: str


def extract_excerpts(text: str, source: str) -> list[Excerpt]:
    out = []
    t = text or ""
    for m in EXCERPT_HEAD_RE.finditer(t):
        head = unicodedata.normalize("NFKC", m.group(1))
        body_start = m.end()
        # 見出し行の残りの「-----」を飛ばす
        nl = t.find("\n", body_start)
        if nl < 0:
            nl = len(t)
        rest_of_line = t[body_start:nl]
        if re.fullmatch(r"\s*[-－ー―─]*\s*", rest_of_line):
            body_start = nl + 1
        dm = DASH_LINE_RE.search(t, body_start)
        nxt_head = EXCERPT_HEAD_RE.search(t, body_start)
        body_end = len(t)
        if dm:
            body_end = dm.start()
        if nxt_head and nxt_head.start() < body_end:
            body_end = nxt_head.start()
        body = t[body_start:body_end].strip()
        refs = page_refs(head)
        pages = []
        for r in refs:
            pages.extend(range(r.start, r.end + 1))
        vm = VER_RE.search(head)
        ver = ""
        if vm:
            ver = "2.1.0" if vm.group(1) in ("2.1.0", "2.1") else vm.group(1)
        out.append(Excerpt(source, head.strip(), pages, ver, body))
    return out


def _excerpt_keys(body: str) -> list[str]:
    """抜粋の本文を文（。・改行・（中略）で区切る）に分け、照合に使う形（空白・記号を除いた文全体）にする。
    文の頭だけでなく文末まで、文全体がページの文字に含まれるかを見る。"""
    keys = []
    body = re.sub(r"[（(]\s*中略\s*[）)]", "\n", body)
    for ln in re.split(r"[\n。]", body):
        ln = re.sub(r"^\s*[PpＰｐ][\.．]?\s?\d{1,3}\s*", "", ln)          # 行頭の「P.95」
        ln = re.sub(r"^\s*[【\[]?[^】\]]{0,20}[】\]]\s*", "", ln) if ln.strip().startswith(("【", "[")) else ln
        n = norm(ln)
        if len(n) >= 10:
            keys.append(n)
    return keys


def strip_page_no(text: str) -> str:
    """ページ先頭の印刷上の番号を除く（文がページをまたぐときに番号が挟まらないように）。"""
    return re.sub(r"^\s*\d{1,3}[ \t]*\n", "", text, count=1)


class PageText:
    def __init__(self, pages: list[Page]):
        self.by_printed = {p.printed: p for p in pages}
        self.norm = {p.printed: norm(strip_page_no(p.text)) for p in pages}
        self.pages = pages

    def window(self, pages: list[int]) -> str:
        """書かれたページ（範囲）＋次のページの冒頭（文がページをまたぐため）。"""
        s = "".join(self.norm.get(p, "") for p in pages)
        if pages:
            s += self.norm.get(max(pages) + 1, "")[:400]
        return s

    def find(self, key: str) -> list[int]:
        return [p for p, t in self.norm.items() if key in t]


def _diverge(key: str, win: str) -> str:
    """抜粋の文がページの文字とどこから食い違うかを短く示す（記号・空白を除いた形）。"""
    n = len(key)
    while n > 5 and key[:n] not in win:
        n -= 1
    if n <= 5:
        return f"文頭から一致しない（「{key[:15]}…」）"
    i = win.find(key[:n])
    return f"文頭から{n}字目まで一致し、台帳「…{key[max(0, n - 8):n + 15]}…」／PDF「…{win[i + max(0, n - 8):i + n + 15]}…」"


def check_excerpt(ex: Excerpt, pt: PageText) -> CheckResult:
    if "技術解説書" not in ex.doc:
        return CheckResult(ex, "―", [], "技術解説書以外の資料のため照合の対象外（最小版）")
    if ex.version and ex.version != "2.1.0":
        return CheckResult(ex, "―", [], f"旧版（{ex.version}版）の引用のため照合不可（PDFが手元にない）")
    if not ex.pages:
        return CheckResult(ex, "―", [], "見出しにページ番号がない")
    keys = _excerpt_keys(ex.text)
    if not keys:
        return CheckResult(ex, "―", [], "照合できる長さの文がない")
    win = pt.window(ex.pages)
    hit = [k for k in keys if k in win]
    if len(hit) == len(keys):
        return CheckResult(ex, "✅", ex.pages, f"抜粋の{len(keys)}文すべてが、文頭から文末まで書かれたページの文字と一致")
    miss = [k for k in keys if k not in win]
    elsewhere = sorted({p for k in miss for p in pt.find(k)})
    if hit and not elsewhere:
        return CheckResult(ex, "⚠️", ex.pages,
                           f"{len(keys)}文中{len(hit)}文は文末まで一致。残りはPDFの文字と食い違う：{_diverge(miss[0], win)}（図表・言い換え・誤字・抜粋の加工の可能性）")
    if elsewhere:
        return CheckResult(ex, "⚠️", elsewhere,
                           f"{len(keys)}文中{len(hit)}文が書かれたページで文末まで一致。ほかは別のページ（P.{'・P.'.join(map(str, elsewhere[:5]))}）で見つかった")
    return CheckResult(ex, "❌", [], "書かれたページにも他のページにも見つからない（旧版の引用・Webの資料・図の中の文字・言い換えの可能性）")


QUOTE_RE = re.compile(r"「([^「」]{4,80})」")


@dataclass
class RefCheck:
    source: str
    ref_text: str
    pages: list[int]
    assumed: bool
    terms: list
    status: str
    detail: str


def check_plain_refs(text: str, source: str, rec_date: str, pt: PageText) -> list[RefCheck]:
    """抜粋のない参照（「P.132に記載のとおり」「（参考：技術解説書2.1.0版 P.132）」）を調べる。
    その文の「」の言葉がそのページにあるかを見る。"""
    out = []
    t = unicodedata.normalize("NFKC", text or "")
    t = re.sub(r"https?://\S+", "URL", t)       # page_refs と同じ置き換え（位置を合わせる）
    # 抜粋の見出しの中の参照は除く
    excerpt_spans = [(m.start(), m.end()) for m in EXCERPT_HEAD_RE.finditer(t)]
    for r in page_refs(t, rec_date):
        if any(a <= r.pos <= b for a, b in excerpt_spans):
            continue
        if r.version != "2.1.0":
            continue
        # 「>」「＞」で始まる行は問合せ文の引用なので、案の根拠としては調べない
        ls = t.rfind("\n", 0, r.pos) + 1
        if t[ls:ls + 1] in (">", "＞"):
            continue
        # 参照を含む文（参照が文末の後ろの括弧書きなら直前の文）
        s0 = max(t.rfind("。", 0, r.pos), t.rfind("\n", 0, r.pos))
        seg_before = t[s0 + 1:r.pos]
        rest = re.sub(r"参考|技術解説書|v?\d+(?:\.\d+)*\s?版|に記載(?:の)?(?:とおり|通り)?", "", seg_before)
        if not norm(rest) and s0 > 0:
            s1 = max(t.rfind("。", 0, s0), t.rfind("\n", 0, s0))
            sent = t[s1 + 1:s0 + 1]
        else:
            e = t.find("。", r.pos)
            sent = t[s0 + 1:(e + 1 if e > 0 else len(t))]
        terms = [q for q in QUOTE_RE.findall(sent)]
        pages = list(range(r.start, r.end + 1))
        if not terms:
            out.append(RefCheck(source, sent.strip()[:160], pages, r.assumed, [], "―",
                                "「」で示した言葉がないため自動では照合しない（人が確認）"))
            continue
        win = pt.window(pages)
        res = []
        for q in terms:
            k = norm(q)   # 「」の言葉は全文で探す
            if not k:
                continue
            if k in win:
                res.append((q, "✅", []))
            else:
                res.append((q, "❌", pt.find(k)[:5]))
        if all(x[1] == "✅" for x in res):
            st, de = "✅", "「」の言葉はすべて書かれたページにある"
        elif any(x[1] == "❌" and not x[2] for x in res):
            st = "❌"
            de = "記載が見つからない：" + "、".join(f"「{q[:20]}」" for q, s, o in res if s == "❌" and not o)
        else:
            st = "⚠️"
            de = "別のページで見つかった：" + "、".join(f"「{q[:20]}」→P.{'・P.'.join(map(str, o))}" for q, s, o in res if s == "❌")
        out.append(RefCheck(source, sent.strip()[:160], pages, r.assumed, terms, st, de))
    return out


# ---------------------------------------------------------------------------
# 類似の過去回答・根拠ページの候補
# ---------------------------------------------------------------------------
KW_RE = re.compile(r"[A-Z]{2,5}-IF-\d{3}|機能\s?\d{1,2}|[A-Za-z][A-Za-z_]{3,}(?:\.[A-Za-z_]+)*")
KW_STOP = {"http", "https", "www", "html", "xmlns", "div", "status", "urn", "uuid", "reference", "code", "coding",
           "system", "display", "title", "entry", "text", "the", "and", "for", "with", "this", "that", "jpfhir",
           "fhir", "clins", "codesystem", "document", "section", "additional", "xhtml", "true", "false", "null",
           "value", "type", "json", "xml", "pdf", "ons", "inc", "service", "now", "sysparm", "article", "view",
           "kb_article_view", "vendorons", "com", "service-now"}


def keywords(text: str) -> set[str]:
    out = set()
    for k in KW_RE.findall(unicodedata.normalize("NFKC", text or "")):
        kk = k.replace(" ", "").lower()
        if kk in KW_STOP or len(kk) < 4:
            continue
        out.add(kk)
    return out


def query_text(r: Record) -> str:
    q = r.latest_question()
    k = r.latest_k()
    parts = [r.subject, r.subject]   # 件名は重みを2倍
    parts.append(q.text if q else r.j)
    if k:
        parts.append(k.text)
    return "\n".join(parts)


def doc_text(r: Record) -> str:
    return "\n".join([r.subject, r.subject, r.j, r.k, r.l])


def answer_head(r: Record, n: int = 200) -> str:
    ans = [s for s in r.l_segs if s.kind == "厚労省回答"]
    t = ans[0].text if ans else r.l
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:n] + "…") if len(t) > n else t


def mark_unanswered(r: Record) -> str:
    if r.m.startswith("ONS回答済"):
        return ""
    if r.m.startswith("取り下げ"):
        return "（取り下げ）"
    return "（未回答）"


def answer_date(r: Record) -> str:
    m = re.search(r"(\d{8}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})", r.m)
    if m:
        return m.group(1)
    return r.n


class Engine:
    def __init__(self, recs: list[Record], pages: list[Page]):
        self.recs = recs
        self.by_no = {r.no: r for r in recs}
        self.by_inc = {r.inc: r.no for r in recs if r.inc}
        self.rec_idx = TfIdf([doc_text(r) for r in recs])
        self.page_idx = TfIdf([p.text for p in pages])
        self.pages = pages
        self.pt = PageText(pages)
        self.rec_pages = {r.no: tech_pages(r.l + "\n" + r.k, r.date) for r in recs}
        self.rec_kw = {r.no: keywords(r.subject + "\n" + r.j) for r in recs}
        self.page_users = defaultdict(list)       # ページ → そのページを根拠にした過去の#
        for r in recs:
            for p in tech_pages(r.l, r.date):
                self.page_users[p].append(r.no)

    # 台帳に書かれた参照（K・S・T列の「#nnn」と「INCnnnnnnn」をD列で#に引き当てる）
    def ledger_refs(self, r: Record) -> list[tuple[int, str]]:
        out, seen = [], set()
        for lab, txt in (("S列", r.memo_s), ("T列", r.memo_t), ("K列", r.k)):
            t = unicodedata.normalize("NFKC", txt or "")
            for m in re.finditer(r"INC\d{7}|#\d{2,3}(?!\d)", t):
                tok = m.group(0)
                no = self.by_inc.get(tok) if tok.startswith("INC") else int(tok[1:])
                if not no or no == r.no or no not in self.by_no or no in seen:
                    continue
                seen.add(no)
                ctx = re.sub(r"\s+", " ", t[max(0, m.start() - 12):m.end() + 12]).strip()
                out.append((no, f"{lab}「…{ctx}…」"))
        return out

    # 類似の過去回答
    def similar(self, r: Record, top: int = 5, exclude: set | None = None):
        qv = self.rec_idx.vec(query_text(r))
        qpages = tech_pages(query_text(r), r.date)
        qkw = keywords(r.subject + "\n" + (r.latest_question().text if r.latest_question() else r.j))
        exclude = (exclude or set()) | {r.no}
        scored = []
        for i, o in enumerate(self.recs):
            if o.no in exclude:
                continue
            base = TfIdf.cos(qv, self.rec_idx.vecs[i])
            sp = qpages & self.rec_pages[o.no]
            sk = qkw & self.rec_kw[o.no]
            # 加点は同じページだけ（同じ言葉の加点は試験で順位を下げたため0。理由の表示にだけ使う）
            score = base + 0.02 * min(len(sp), 3)
            scored.append((score, base, sorted(sp), sorted(sk), o))
        scored.sort(key=lambda x: -x[0])
        return scored[:top]

    # 根拠ページの候補
    def page_candidates(self, r: Record, top: int = 8, max_cited: int = 5):
        qt = query_text(r)
        qv = self.page_idx.vec(qt)
        cited = []
        q = r.latest_question()
        k = r.latest_k()
        # 同じ行の前回までの往復（前回の機構コメント・前回の厚労省回答）で引いたページ。
        # L列の既存案（相談中の案）は「既存案の根拠の照合」で別に見るので、ここには入れない
        prev_txt = "\n".join([s.text for s in r.k_segs if s.kind == "基金コメント" and k is not None and s is not k]
                             + [s.text for s in r.l_segs if s.kind == "厚労省回答"])
        sources = (("問合せ者の引用", q.text if q else r.j), ("機構コメントの引用", k.text if k else ""),
                   ("同じ行の前回までの往復で引用", prev_txt))
        for src, txt in sources:
            for pr in page_refs(txt, r.date):
                if pr.version == "2.1.0":
                    for p in range(pr.start, pr.end + 1):
                        if p not in [c[0] for c in cited] and p in self.pt.by_printed:
                            cited.append((p, src + ("（版の書きなし・2.1.0版と推定）" if pr.assumed else "")))
        cited = cited[:max_cited]
        scores = []
        for i, p in enumerate(self.pages):
            scores.append((TfIdf.cos(qv, self.page_idx.vecs[i]), p.printed))
        scores.sort(key=lambda x: -x[0])
        rank = {p: (i + 1, s) for i, (s, p) in enumerate(scores)}
        out = []
        for p, why in cited:
            out.append((p, why, rank[p][0], rank[p][1]))
        for s, p in scores:
            if len(out) >= top:
                break
            if p in [o[0] for o in out]:
                continue
            out.append((p, "全文検索", rank[p][0], s))
        return out, qt

    def snippet(self, printed: int, qt: str, width: int = 260) -> str:
        page = self.pt.by_printed[printed]
        flat = re.sub(r"[ \t]*\n[ \t]*", "", strip_page_no(page.text))
        flat = re.sub(r"[ 　]{2,}", " ", flat)
        sents = [s for s in re.split(r"(?<=。)", flat) if s.strip()]
        if not sents:
            return ""
        qset = set(bigrams(qt))
        best_i, best = 0, -1.0
        for i, s in enumerate(sents):
            g = set(bigrams(s))
            if not g:
                continue
            sc = sum(self.page_idx.idf(x) for x in g & qset) / (1 + math.log(1 + len(g)))
            if sc > best:
                best, best_i = sc, i
        a, b = max(0, best_i - 1), min(len(sents), best_i + 2)
        snip = "".join(sents[a:b]).strip()
        if len(snip) > width * 2:
            snip = snip[:width * 2] + "…"
        return snip


# ---------------------------------------------------------------------------
# A/B区分の候補
# ---------------------------------------------------------------------------
B_WORDS = ["同意", "制度", "将来", "今後", "周知", "費用", "法第", "個人情報", "運用", "方針", "本格運用", "全国", "保険者", "責任", "許容", "可否"]
A_WORDS = ["Composition", "Bundle", "identifier", "entry", "section", "要素", "電文", "XML", "項目", "コード", "リソース", "多重度", "IF-"]


def ab_candidate(r: Record, sims, checks: list, refchecks: list):
    rows = []
    a = b = 0
    memo = "\n".join([r.memo_s, r.memo_t] + [ln for ln in r.l.splitlines() if "黒川" in ln or ln.strip().startswith("★")])
    if re.search(r"方針確認不要|確認不要", memo):
        rows.append(("台帳のメモ（L・S・T列）", "A寄り", "「方針確認不要」の記載")); a += 1
    elif re.search(r"方針(?:ご)?(?:確認|相談)|モデルチーム|ご相談事項|相談", memo):
        m = re.search(r".{0,15}(?:方針(?:ご)?(?:確認|相談)|モデルチーム|ご相談事項|相談).{0,15}", memo)
        rows.append(("台帳のメモ（L・S・T列）", "B寄り", f"「{m.group(0).strip()}」")); b += 1
    else:
        rows.append(("台帳のメモ（L・S・T列）", "―", "該当する記載なし"))
    k = r.latest_k()
    req = REQ_RE.search(k.text) if k else None
    has_draft = bool(k and re.search(r"【回答案", k.text))
    if req and "確認依頼" in req.group(1) and has_draft:
        rows.append(("基金の依頼区分（K列・最新回）", "A寄り", f"「{req.group(1)}」・回答案(仮)あり")); a += 1
    elif req and "作成依頼" in req.group(1):
        rows.append(("基金の依頼区分（K列・最新回）", "B寄り" if not has_draft else "―",
                     f"「{req.group(1)}」" + ("・回答案(仮)あり" if has_draft else "・回答案(仮)なし")))
        if not has_draft:
            b += 1
    else:
        rows.append(("基金の依頼区分（K列・最新回）", "―", "依頼区分の記載が見つからない" if not req else f"「{req.group(1)}」"))
    if sims and sims[0][1] >= 0.35:
        rows.append(("似た過去回答", "A寄り", f"#{sims[0][4].no}（文字の重なり{sims[0][1]:.2f}）が近い")); a += 1
    elif sims:
        rows.append(("似た過去回答", "B寄り", f"一番近い#{sims[0][4].no}でも文字の重なり{sims[0][1]:.2f}（前例が薄い）")); b += 1
    q = r.subject + (r.latest_question().text if r.latest_question() else r.j)
    bw = [w for w in B_WORDS if w in q]
    aw = [w for w in A_WORDS if w.lower() in q.lower()]
    if len(bw) > len(aw):
        rows.append(("テーマの言葉", "B寄り", "、".join(bw[:6]))); b += 1
    elif aw:
        rows.append(("テーマの言葉", "A寄り", "、".join(aw[:6]))); a += 1
    else:
        rows.append(("テーマの言葉", "―", "目立つ言葉なし"))
    bad = [c for c in checks if c.status == "❌"] + [c for c in refchecks if c.status == "❌"]
    if bad:
        rows.append(("既存案の根拠の照合", "B寄り", f"❌ {len(bad)}件（資料に記載が見つからない）")); b += 1
    elif any(c.status == "✅" for c in checks + refchecks):
        rows.append(("既存案の根拠の照合", "A寄り", "抜粋が書かれたページにある")); a += 1
    else:
        rows.append(("既存案の根拠の照合", "―", "照合できる既存案なし"))
    cand = "A（読み合せ）" if a > b else ("B（回答方針確認）" if b > a else "決め手なし（人が判断）")
    return cand, a, b, rows


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------
def md_quote(text: str, limit: int | None = None) -> str:
    t = (text or "").strip()
    if limit and len(t) > limit:
        t = t[:limit] + "…（以下略。全文は台帳）"
    if not t:
        return "> （なし）"
    return "\n".join("> " + ln if ln.strip() else ">" for ln in t.splitlines())


def esc(s: str) -> str:
    return (s or "").replace("|", "｜").replace("\n", " ")


def analyze(eng: Engine, r: Record):
    sims = eng.similar(r)
    pages, qt = eng.page_candidates(r)
    exs = []
    # 既存案（L列の厚労省回答より前＝相談中の案）・前回までの厚労省回答・K列の回答案(仮)
    for s in r.l_segs:
        src = "L列の既存案" if s.kind in ("前置き", "見出しなし") else f"L列の前回回答（{s.date or s.heading}）"
        exs.append((src, s.text))
    k = r.latest_k()
    if k:
        exs.append((f"K列 最新回の機構コメント・回答案(仮)（{k.date}）", k.text))
    checks, refchecks = [], []
    for src, txt in exs:
        for ex in extract_excerpts(txt, src):
            checks.append(check_excerpt(ex, eng.pt))
        refchecks.extend(check_plain_refs(txt, src, r.date, eng.pt))
    ab = ab_candidate(r, sims, checks, refchecks)
    return sims, pages, qt, checks, refchecks, ab


def render(eng: Engine, targets: list[Record], ledger: Path, ledger_hash: str, pdf: Path, round_id: str,
           warn_old: str) -> str:
    now = dt.datetime.now()
    mtime = dt.datetime.fromtimestamp(ledger.stat().st_mtime)
    rd = dt.datetime.strptime(round_id, "%Y%m%d").strftime("%Y-%m-%d")
    L = []
    L.append(f"# ONS下調べ（{rd} 会議向け）※自動生成のひな形。結論・言い回しは未記入")
    L.append("")
    L.append(f"> 作成日: {now:%Y-%m-%d}")
    L.append(f"> 元データ: 台帳②「{SHEET_NAME}」シート（`{ledger.name}`、{mtime:%Y-%m-%d %H:%M} 保存）。読み取りのみ。実行前後でファイルのハッシュが一致することを確認済み（SHA-256 先頭12桁 {ledger_hash[:12]}）")
    if warn_old:
        L.append(f"> ⚠️ {warn_old}")
    for w in LOAD_WARNINGS:
        L.append(f"> ⚠️ {w}")
    nos = [r.no for r in eng.recs]
    L.append(f"> 索引: 過去の問合せ {len(eng.recs)}件（#{min(nos)}〜#{max(nos)}）／ページ索引：{DOC_LABEL} {len(eng.pages)}ページ（原本PDF `{pdf.name}`）")
    L.append(f"> 生成: {now:%Y-%m-%d %H:%M}（`07_ONS問合せ対応/ONS問合せ会議/00_共通/03_scripts/ons_shitashirabe.py` {TOOL_VERSION}）")
    L.append("> 読み方: 「自動」の欄は機械的に拾った候補で**未確認**。照合の「✅」は「抜粋の各文が、文頭から文末まで（空白・記号を除いて）書かれたページの文字と一致した」ことだけを示し、回答の言い回しが根拠と合っていることは示さない。ページの確定・結論・言い回しは人が書く（`01_定常業務/ルール・ガイド/ONS回答作成ガイド.md`）")
    L.append("")
    L.append("## 一覧")
    L.append("")
    L.append("| # | 問合せ者（N回目） | 件名 | 台帳M列 | 基金の依頼区分 | A/B候補（推測） | 似た過去回答（自動） | 照合で⚠️❌ |")
    L.append("|---|---|---|---|---|---|---|---|")
    results = {}
    for r in targets:
        res = analyze(eng, r)
        results[r.no] = res
        sims, pages, qt, checks, refchecks, ab = res
        k = r.latest_k()
        req = REQ_RE.search(k.text).group(1) if k and REQ_RE.search(k.text) else "―"
        flag = sum(1 for c in checks + refchecks if c.status in ("⚠️", "❌"))
        refs = [f"#{n}（台帳の参照）" for n, _ in eng.ledger_refs(r)]
        sim_s = "・".join(refs + [f"#{s[4].no}" for s in sims[:3]])
        L.append(f"| {r.no} | {esc(r.asker)}（{r.latest_round}回目） | {esc(r.subject)} | {esc(r.m.splitlines()[0][:20] if r.m else '') or '（空）'} | {req} | {ab[0]} | {sim_s} | {flag}件 |")
    L.append("")
    for r in targets:
        sims, pages, qt, checks, refchecks, ab = results[r.no]
        L.append("---")
        L.append("")
        L.append(f"## #{r.no} {r.asker}（{r.latest_round}回目）｜{r.subject}")
        L.append("")
        L.append(f"- 起票日 {r.date}／{r.inc}／カテゴリ {r.category or '（空）'}／台帳M列「{r.m or '（空）'}」・N列 {r.n or '（空）'}")
        L.append("")
        # 経緯
        L.append("### 経緯（同じ行の前回まで）")
        L.append("")
        lq = r.latest_question()
        prev_q = [s for s in r.j_segs if s.kind == "質問" and lq and s.round != lq.round]
        prev_a = [s for s in r.l_segs if s.kind == "厚労省回答"]
        lk = r.latest_k()
        # K列の最新回より前の区切り（前回までの機構コメント・ND/FJ回答・ONS回答済の見出しなど）。
        # 台帳は新しい順に書くので、逆にして古い順に出す
        prev_k = [s for s in r.k_segs if s is not lk][::-1]
        if not prev_q and not prev_a and not prev_k:
            L.append("- 前回までの往復なし（1回目）")
        if prev_q:
            L.append("#### 前回までのご質問（J列・回の順・全文）")
            L.append("")
        for s in sorted(prev_q, key=lambda s: s.round or 0):
            L.append(f"**{s.heading or f'お問合せ{s.round}回目'}**")
            L.append("")
            L.append(md_quote(s.text))
            L.append("")
        if prev_k:
            L.append("#### 前回までの機構コメント・ND/FJ回答など（K列・古い順・全文）")
            L.append("")
        for s in prev_k:
            head = s.heading or ("（見出しの前の文）" if s.kind == "前置き" else "（見出しなし）")
            L.append(f"**{head}**")
            L.append("")
            L.append(md_quote(s.text))
            L.append("")
        if prev_a:
            L.append("#### 前回までの厚労省回答（L列・古い順・全文）")
            L.append("")
        for s in prev_a[::-1]:
            L.append(f"**{s.heading}**")
            L.append("")
            L.append(md_quote(s.text))
            L.append("")
        unk = [s for s in r.j_segs if s.kind in ("見出しなし", "前置き")]
        if unk:
            L.append(f"- ⚠️ J列に回の見出し（【お問合せN回目】）で分けられない文がある（{sum(len(s.text) for s in unk)}字）。原文を台帳で確認")
            L.append("")
        # 今回の質問
        L.append(f"### 今回のご質問（原文・J列 {r.latest_round}回目）")
        L.append("")
        L.append(md_quote(lq.text if lq else r.j))
        L.append("")
        L.append("### 聞かれていること（1行）")
        L.append("")
        L.append("（記入）")
        L.append("")
        L.append("### 基金コメント・回答案(仮)（K列・最新回）")
        L.append("")
        k = r.latest_k()
        if k:
            req = REQ_RE.search(k.text)
            L.append(f"- {k.heading}" + (f"　依頼区分：**{req.group(1)}**" if req else "　依頼区分：（見つからない）"))
            L.append("")
            L.append(md_quote(k.text))
        else:
            L.append("- （K列に回のコメントの見出しが見つからない）")
            if r.k:
                L.append("")
                L.append(md_quote(r.k, 1500))
        L.append("")
        L.append("### 台帳のメモ・既存案（L列・S列・T列）")
        L.append("")
        draft = [s for s in r.l_segs if s.kind in ("前置き", "見出しなし")]
        if draft:
            L.append("**L列の既存案（厚労省回答の見出しより前）**")
            L.append("")
            L.append(md_quote("\n".join(s.text for s in draft)))
            L.append("")
        else:
            L.append("- L列の既存案：なし")
        for lab, v in (("S列（見出しなし）", r.memo_s), ("T列（見出しなし）", r.memo_t)):
            if v:
                L.append(f"**{lab}のメモ**")
                L.append("")
                L.append(md_quote(v))
                L.append("")
        L.append("")
        # 照合
        L.append("### 既存案の根拠の照合（自動）")
        L.append("")
        L.append("※判定のしかた：抜粋を文（。・改行・（中略））に分け、空白・記号を除いた**文全体（文頭から文末まで）**が、書かれたページ（＋次のページの冒頭）の文字に含まれるかを見る。"
                 "✅＝全文が一致／⚠️＝一部の文が食い違う・別のページにある（どこから食い違うかを示す）／❌＝どのページにもない／―＝対象外。"
                 "抜粋のない参照は「」の言葉だけを見る。いずれも言い回しの正しさは見ていない")
        L.append("")
        if not checks and not refchecks:
            L.append("- 照合の対象（「【参考：…抜粋】」やページの参照）が見つからない")
        if checks:
            L.append("| 結果 | どこの案か | 見出し | 見つかったページ | 説明 |")
            L.append("|---|---|---|---|---|")
            for c in checks:
                fp = "・".join(f"P.{p}" for p in c.found_pages) or "―"
                L.append(f"| {c.status} | {esc(c.item.source)} | {esc(c.item.doc)} | {fp} | {esc(c.detail)} |")
            L.append("")
        if refchecks:
            L.append("**抜粋のない参照（「P.nnに記載のとおり」など）**")
            L.append("")
            L.append("| 結果 | どこの案か | 参照しているページ | その文（先頭） | 説明 |")
            L.append("|---|---|---|---|---|")
            for c in [c for c in refchecks if c.status != "―"]:
                pg = "・".join(f"P.{p}" for p in c.pages) + ("（版の書きなし・推定）" if c.assumed else "")
                L.append(f"| {c.status} | {esc(c.source)} | {pg} | {esc(c.ref_text[:90])} | {esc(c.detail)} |")
            rest = [c for c in refchecks if c.status == "―"]
            if rest:
                pgs = sorted({p for c in rest for p in c.pages})
                L.append(f"| ― | （まとめ） | {'・'.join(f'P.{p}' for p in pgs)} | 「」の言葉がない参照{len(rest)}か所 | 自動では照合しない（人が確認） |")
            L.append("")
        L.append("**人が見る欄：回答の言い回しが根拠と合っているか**（自動では判定しない。抜粋と回答文を1文ずつ突き合わせる。ガイド§6）")
        L.append("")
        L.append("| 回答（案）の文 | 根拠の文（資料・ページ） | 合っているか |")
        L.append("|---|---|---|")
        L.append("| （記入） | （記入） | □ |")
        L.append("")
        # 類似
        L.append("### 似た過去回答（上位5件・自動）")
        L.append("")
        L.append("※同じ論点の参考。前回回答の引用ではない（「前回ご案内のとおり」は同じ行の前回回答にだけ使う。ガイド§3）")
        L.append("")
        L.append("| 順位 | # | 問合せ者 | 起票日 | 回答状況（日付） | 根拠ページ（L列） | 一致した理由 | 回答の冒頭 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for no, where in eng.ledger_refs(r):
            o = eng.by_no[no]
            rp = "・".join(f"P.{p}" for p in sorted(eng.rec_pages[o.no])[:6]) or "―"
            L.append(f"| 台帳の参照 | {o.no}{mark_unanswered(o)} | {esc(o.asker)} | {o.date} | {esc(o.m.splitlines()[0] if o.m else '')} | {rp} | {esc('台帳に書かれた参照：' + where)} | {esc(answer_head(o))} |")
        for i, (score, base, sp, sk, o) in enumerate(sims, 1):
            why = [f"文字の重なり {base:.2f}"]
            if sp:
                why.append("同じページ " + "・".join(f"P.{p}" for p in sp))
            if sk:
                why.append("同じ言葉 " + "・".join(sk[:3]))
            rp = "・".join(f"P.{p}" for p in sorted(eng.rec_pages[o.no])[:6]) or "―"
            L.append(f"| {i} | {o.no}{mark_unanswered(o)} | {esc(o.asker)} | {o.date} | {esc(o.m.splitlines()[0] if o.m else '')}{('（' + answer_date(o) + '）') if answer_date(o) and answer_date(o) not in o.m else ''} | {rp} | {esc('／'.join(why))} | {esc(answer_head(o))} |")
        L.append("")
        # ページ候補
        L.append(f"### 根拠ページの候補（上位{len(pages)}件・自動）：{DOC_LABEL}")
        L.append("")
        L.append("※PDFから文字を取り出して検索した候補。□は原本PDFで目視確認した印。確定ページは人が決める（ベンダの引用ページもそのまま使わない。ガイド§6）")
        L.append("")
        L.append("| 確認 | ページ | 拾った理由 | 見出し（このページ） | 該当箇所（前後の文） | 同じページを使った過去回答 |")
        L.append("|---|---|---|---|---|---|")
        for p, why, rk, sc in pages:
            pg = eng.pt.by_printed[p]
            head = pg.headings or pg.context or "―"
            if pg.context and pg.context not in head:
                head = f"{pg.context} ／ {head}"
            users = [n for n in eng.page_users.get(p, []) if n != r.no][-5:]
            us = "・".join(f"#{n}" for n in users) or "―"
            label = why if why == "全文検索" else f"**{why}**（検索順位{rk}位）"
            L.append(f"| □ | P.{p} | {label} | {esc(head)} | {esc(eng.snippet(p, qt))} | {us} |")
        nb = sorted({p + d for p, why, rk, sc in pages if why != "全文検索" for d in (-1, 1)} - {p for p, *_ in pages})
        nb = [p for p in nb if p in eng.pt.by_printed]
        if nb:
            L.append("")
            L.append(f"- 引用されたページの前後も読む（文が次のページに続くことがある）：" + "・".join(f"P.{p}" for p in nb))
        L.append("")
        # A/B
        L.append(f"### A/B区分の候補（推測）：{ab[0]}（A寄り{ab[1]}・B寄り{ab[2]}）")
        L.append("")
        L.append("| 材料 | 向き | 根拠 |")
        L.append("|---|---|---|")
        for m, d, why in ab[3]:
            L.append(f"| {m} | {d} | {esc(why)} |")
        L.append("")
        L.append("決めるのは人（A＝読み合せ／B＝回答方針確認）：（記入）")
        L.append("")
        L.append("### 回答案（ACN案）")
        L.append("")
        L.append(f"【厚労省回答】（{now:%Y}MMDD）")
        L.append("（記入）")
        L.append("")
        L.append("### 基金仮案との比較")
        L.append("")
        L.append("| 観点 | 基金仮案 | ACN案 | 理由 |")
        L.append("|---|---|---|---|")
        for v in ("結論", "前置き", "根拠", "言い方"):
            L.append(f"| {v} | （記入） | （記入） | （記入） |")
        L.append("")
        L.append("### 本田さん確認事項（相談文）")
        L.append("")
        L.append("要否：□（Aなら空欄のままでよい）")
        L.append("")
        L.append("（記入：論点・ACN案・根拠1つ・補足）")
        L.append("")
        L.append("### ★厚労省様への相談事項（台帳L列に記入するもの）")
        L.append("")
        L.append("要否：□")
        L.append("")
        L.append("（記入）")
        L.append("")
        L.append("### 機構への連携事項（台帳K列に記入するもの）")
        L.append("")
        L.append("要否：□")
        L.append("")
        L.append("（記入）")
        L.append("")
        L.append("### 想定される質問")
        L.append("")
        L.append("| 想定される質問 | 答え | 根拠 |")
        L.append("|---|---|---|")
        L.append("| （記入） | （記入） | （記入） |")
        L.append("")
    L.append("---")
    L.append("")
    L.append("## やったこと・やっていないこと")
    L.append("")
    L.append("**やったこと（自動）**")
    L.append(f"- 台帳の「{SHEET_NAME}」シートを一時フォルダのコピーから読み取りのみで読み、J・K・L列を回の見出しで分けた")
    L.append(f"- 似た過去回答：件名（2倍の重み）＋最新回の質問＋最新回の機構コメントと、過去の全件（件名・J・K・L列）の2文字単位の重なりに、同じページ・同じ言葉（IF番号・リソース名など）の加点をして並べた")
    L.append(f"- 根拠ページの候補：{DOC_LABEL}の原本PDFを1ページずつ文字にして同じ方法で検索し、質問・機構コメントで引用されたページを先頭に置いた")
    L.append(f"- 既存案の照合：L列・K列の「【参考：…抜粋】」の文が、書かれたページ（と次のページの冒頭）にあるかを、空白・記号を除いた文全体（文頭から文末まで）で調べた。抜粋のない参照は、その文の「」の言葉がそのページにあるかを調べた")
    L.append("")
    L.append("**やっていないこと（人が行う・最小版の対象外）**")
    L.append("- 回答文・結論・言い回しの作成と、言い回しが根拠と合っているかの判定")
    L.append(f"- {DOC_LABEL}以外の資料（FHIR記述仕様・共通表・患者サマリー編・運用マニュアル・外部IF仕様書・別紙・保険者向け手引き・Webの資料）の検索と照合。これらを引いた抜粋は「―（対象外）」と出している")
    L.append("- 旧版（2.0.0版・1.3.0版など）を引いた抜粋の照合（PDFが手元にない）")
    L.append("- 図・表の画像の中の文字の照合（PDFから文字で取れないため❌や⚠️になることがある）")
    L.append("- 台帳①（SharePoint）・台帳②の他シート（コールセンター・厚労エスカレ以外）の確認")
    L.append("- 台帳への書き込み（①②とも）")
    L.append("")
    return "\n".join(L)


def next_version_path(out_dir: Path, round_id: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    vs = []
    for p in out_dir.glob(f"{round_id}_ONS下調べ_v*.md"):
        m = re.search(r"_v(\d+)\.md$", p.name)
        if m:
            vs.append(int(m.group(1)))
    n = max(vs) + 1 if vs else 1
    return out_dir / f"{round_id}_ONS下調べ_v{n}.md"


def select_targets(recs: list[Record], ids: list[int] | None) -> list[Record]:
    by = {r.no: r for r in recs}
    if ids:
        miss = [i for i in ids if i not in by]
        if miss:
            raise SystemExit(f"台帳に見つからない#: {miss}")
        return [by[i] for i in ids]
    return [r for r in recs if not r.done]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ONS回答の下調べ（最小版）：台帳②と技術解説書2.1.0版から、件ごとの下調べMDを出す")
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="台帳②のxlsx（読み取りのみ）。省略時はDownloadsの手元コピー")
    ap.add_argument("--round", required=True, help="会議の回（YYYYMMDD）。出力先 ONS問合せ会議/<回>/02_output/ とファイル名に使う")
    ap.add_argument("--ids", help="対象の#（カンマ区切り）。省略時は台帳M列が「ONS回答済」「取り下げ」以外の全件")
    ap.add_argument("--out", help="出力フォルダ（試験用など）。省略時は ONS問合せ会議/<回>/02_output/")
    ap.add_argument("--pdf", help="技術解説書2.1.0版のPDF（省略時は 02_仕様・技術/20260723_技術解説書2.1.0版/01_input/）")
    a = ap.parse_args(argv)

    if not re.fullmatch(r"\d{8}", a.round):
        raise SystemExit("--round は YYYYMMDD で指定してください")
    ledger = Path(a.ledger)
    if not ledger.exists():
        raise SystemExit(f"台帳が見つかりません: {ledger}")
    if a.out:
        out_dir = Path(a.out)
    else:
        rdir = MEETING_DIR / a.round
        if not rdir.exists():
            raise SystemExit(f"回のフォルダがありません: {rdir}（先に /new-project 等で作るか --out を指定）")
        out_dir = rdir / "02_output"

    h_before = sha256(ledger)
    recs = load_ledger(ledger)
    pdf = find_pdf(a.pdf)
    pages, _ = load_pages(pdf)
    eng = Engine(recs, pages)
    ids = [int(x) for x in re.split(r"[,\s、]+", a.ids.strip()) if x] if a.ids else None
    targets = select_targets(recs, ids)
    if not targets:
        raise SystemExit("対象の件がありません（--ids で指定してください）")
    age = (dt.datetime.now() - dt.datetime.fromtimestamp(ledger.stat().st_mtime)).days
    warn = f"台帳の手元コピーが{age}日前の保存です。SharePointの最新を落としてから使うと確実です" if age >= 3 else ""
    text = render(eng, targets, ledger, h_before, pdf, a.round, warn)
    h_after = sha256(ledger)
    if h_before != h_after:
        raise SystemExit("台帳のハッシュが実行前後で変わりました。出力を中止します（台帳を確認してください）")
    out = next_version_path(out_dir, a.round)
    out.write_text(text, encoding="utf-8")
    print(f"出力: {out}")
    print(f"対象: {len(targets)}件 " + ",".join(f"#{r.no}" for r in targets))
    print(f"台帳のハッシュ: 実行前後で一致（{h_before[:12]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
