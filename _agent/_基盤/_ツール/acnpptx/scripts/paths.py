"""
パス解決の一元化。

- SKILL_DIR: このスキルの配置先（プラグインのキャッシュでも ~/.claude/skills/acnpptx でも可）。
  スクリプトの位置から自動算出する。読み取り専用として扱う（プラグイン更新で置き換わる）。
- DATA_DIR: ユーザーデータ（追加テーマ・マスター・プレビュー・抽出画像・非表示リスト）。
  環境変数 ACNPPTX_DATA があればそれ、なければ ~/.acnpptx。プラグイン更新後も残る。
  ACNPPTX_DATA は ~/.acnpptx か作業フォルダ（CWD）の中だけを受け付ける。
- 引数・環境変数で受け取ったパスは check_path() を通し、許可フォルダ
  （作業フォルダ配下・DATA_DIR・SKILL_DIR〔読み取りのみ〕）の外なら処理を止める。
"""

import json
import os
import re
import sys
from pathlib import Path

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
ASSETS_DIR = os.path.join(SKILL_DIR, "assets")
GRAMMAR_DIR = os.path.join(SKILL_DIR, "grammar")


def _fail(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _data_dir() -> str:
    default = Path.home() / ".acnpptx"
    env = os.environ.get("ACNPPTX_DATA")
    if not env:
        return str(default)
    p = Path(env).resolve()
    if not (p.is_relative_to(default.resolve()) or p.is_relative_to(Path.cwd().resolve())):
        _fail(f"ACNPPTX_DATA は ~/.acnpptx か作業フォルダの中を指定してください: {env}")
    return str(p)


DATA_DIR = _data_dir()


def check_path(p, write: bool = False) -> str:
    """引数・環境変数で受け取ったパスが許可フォルダの内側か確かめ、解決済みの絶対パスを返す。
    許可フォルダ: 作業フォルダ（CWD）配下・DATA_DIR・SKILL_DIR（SKILL_DIR は読み取りのみ）。外なら処理を止める。"""
    roots = [Path.cwd(), Path(DATA_DIR)] + ([] if write else [Path(SKILL_DIR)])
    rp = Path(p).resolve()
    if any(rp.is_relative_to(r.resolve()) for r in roots):
        return str(rp)
    where = f"作業フォルダ（{Path.cwd()}）の中、{DATA_DIR}" + ("" if write else f"、{SKILL_DIR}（読み取りのみ）")
    _fail(f"許可されていない場所への{'書き込み' if write else '読み込み'}です: {p}\n"
          f"  使える場所: {where}\n"
          f"  作業フォルダの外のファイルは、作業フォルダにコピーしてから指定してください")

BUILTIN_THEMES_DIR = os.path.join(ASSETS_DIR, "themes")
USER_THEMES_DIR = os.path.join(DATA_DIR, "themes")
USER_MASTERS_DIR = os.path.join(DATA_DIR, "masters")
BUILTIN_PREVIEWS_DIR = os.path.join(ASSETS_DIR, "master_previews")
USER_PREVIEWS_DIR = os.path.join(DATA_DIR, "master_previews")
EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted")
HIDDEN_THEMES_FILE = os.path.join(DATA_DIR, "hidden_themes.json")

_SAFE_NAME = re.compile(r"[\w.\-]+")


def is_safe_theme_name(name: str) -> bool:
    """テーマ名がファイル名として安全か（パス区切り・シェルの特殊文字・.. を含まない）。"""
    return bool(_SAFE_NAME.fullmatch(name)) and name not in (".", "..")


def safe_theme_name(name: str) -> str:
    """任意の文字列（ファイル名など）を安全なテーマ名にする。"""
    s = re.sub(r"[^\w.\-]+", "-", name.strip().lower()).strip(".-")
    return s or "theme"


def ensure_data_dir(sub: str = "") -> str:
    path = os.path.join(DATA_DIR, sub) if sub else DATA_DIR
    os.makedirs(path, exist_ok=True)
    return path


def hidden_themes() -> set:
    if not os.path.isfile(HIDDEN_THEMES_FILE):
        return set()
    with open(HIDDEN_THEMES_FILE, encoding="utf-8") as f:
        return set(json.load(f))


def set_hidden_themes(names) -> None:
    ensure_data_dir()
    with open(HIDDEN_THEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(set(names)), f, ensure_ascii=False, indent=2)


def find_theme(name: str):
    """テーマ JSON のパスを返す。ユーザー追加 → 組み込みの順。見つからなければ None。"""
    name = name.removesuffix(".json")
    if not is_safe_theme_name(name):
        return None
    fname = name + ".json"
    for d in (USER_THEMES_DIR, BUILTIN_THEMES_DIR):
        p = os.path.join(d, fname)
        if os.path.isfile(p):
            return check_path(p)
    return None


def list_themes(include_hidden: bool = False):
    """[{name, path, builtin}] を返す。ユーザー追加が同名の組み込みを上書きする。"""
    hidden = set() if include_hidden else hidden_themes()
    found = {}
    for d, builtin in ((BUILTIN_THEMES_DIR, True), (USER_THEMES_DIR, False)):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json") and not fn.startswith("_") and is_safe_theme_name(fn[:-5]):
                name = fn[:-5]
                found[name] = {"name": name, "path": os.path.join(d, fn), "builtin": builtin}
    return [v for k, v in found.items() if k not in hidden]


def resolve_theme_file(theme_json_path: str, rel: str) -> str:
    """テーマ JSON 内の相対パス（template 等）を解決する。
    ユーザーテーマは DATA_DIR 基準、組み込みは SKILL_DIR 基準。"""
    if os.path.isabs(rel):
        return check_path(rel)
    base = DATA_DIR if Path(theme_json_path).resolve().is_relative_to(Path(DATA_DIR).resolve()) else SKILL_DIR
    return check_path(os.path.join(base, rel))


def preview_dir(theme_name: str) -> str:
    """テーマのプレビュー画像ディレクトリ（存在するほう。なければユーザー側の書き込み先）。"""
    if not is_safe_theme_name(theme_name):
        raise ValueError(f"invalid theme name: {theme_name!r}")
    for d in (USER_PREVIEWS_DIR, BUILTIN_PREVIEWS_DIR):
        p = os.path.join(d, theme_name)
        if os.path.isdir(p):
            return check_path(p)
    return check_path(os.path.join(USER_PREVIEWS_DIR, theme_name), write=True)
