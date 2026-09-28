"""작업 폴더와 과목 설정 찾기 — 저장소를 clone해서 쓰든, 스킬로 설치해서 쓰든 똑같이 동작하게.

엔진 E   : 이 파일이 있는 폴더 (snu-report-core/scripts). 과목 스킬은 그 옆 폴더들이다.
작업 폴더 W: profile.yaml이 있는 폴더 (현재 폴더에서 위로 찾는다). 사용자 정보와 과목별 작업물이 쌓인다.
과목 설정 = 과목 스킬의 course.yaml(기본값: 과목명, 파일명 규칙) ← W/courses/<과목>/course.yaml(조, 조원, 바꾼 값)
"""
from __future__ import annotations

from pathlib import Path

ENGINE = Path(__file__).resolve().parent
SKILLS_DIR = ENGINE.parent.parent          # snu-report-core 옆에 snu-logic-lab 등이 있다


def _load(p: Path) -> dict:
    import yaml
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def find_workspace(start: Path | None = None) -> Path | None:
    start = Path(start or Path.cwd()).resolve()
    for d in [start, *start.parents]:
        if (d / "profile.yaml").exists():
            return d
    return None


def course_skills() -> dict[str, Path]:
    """과목 키 → 과목 스킬 폴더 (course.yaml의 key)."""
    out = {}
    for cy in sorted(SKILLS_DIR.glob("*/course.yaml")):
        k = _load(cy).get("key")
        if k:
            out[str(k)] = cy.parent
    return out


def course_defaults(key: str) -> dict:
    d = course_skills().get(key)
    return _load(d / "course.yaml") if d else {}


def course_config(ws: Path | None, key: str) -> dict:
    over = _load(ws / "courses" / key / "course.yaml") if ws else {}
    return {**course_defaults(key), **over}


def known_courses(ws: Path | None) -> list[str]:
    keys = set(course_skills())
    if ws and (ws / "courses").exists():
        keys |= {d.name for d in (ws / "courses").iterdir() if (d / "course.yaml").exists()}
    return sorted(keys)


def remember_engine(ws: Path | None):
    """W/.snu-engine에 엔진 경로를 적는다. 그림 스크립트(make_figs.py)가 이걸 보고 엔진을 import한다."""
    if not ws:
        return
    p = ws / ".snu-engine"
    try:
        if not p.exists() or p.read_text(encoding="utf-8").strip() != str(ENGINE):
            p.write_text(str(ENGINE) + "\n", encoding="utf-8")
    except OSError:
        pass


# ───────── 외부 프로그램 찾기 ─────────
# 방금 설치한 프로그램은 PATH가 바로 갱신되지 않는다 (특히 Windows winget). 알려진 설치 위치도 본다.
_HOME = Path.home()
_LOCAL = Path(__import__("os").environ.get("LOCALAPPDATA", _HOME / "AppData/Local"))
_KNOWN = {
    "pandoc": [_LOCAL / "Pandoc/pandoc.exe", Path("C:/Program Files/Pandoc/pandoc.exe"),
               Path("/opt/homebrew/bin/pandoc"), Path("/usr/local/bin/pandoc")],
    "soffice": [Path("C:/Program Files/LibreOffice/program/soffice.exe"),
                Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")],
    "ngspice": [Path("/opt/homebrew/bin/ngspice"), Path("/usr/local/bin/ngspice"),
                _HOME / ".local/ngspice/Spice64/bin/ngspice_con.exe", Path("C:/Spice64/bin/ngspice_con.exe")],
    "ltspice": [_LOCAL / "Programs/ADI/LTspice/LTspice.exe", Path("C:/Program Files/ADI/LTspice/LTspice.exe"),
                Path("C:/Program Files/LTC/LTspiceXVII/XVIIx64.exe"),
                Path("/Applications/LTspice.app/Contents/MacOS/LTspice")],
    "ltspice-mcp": [_HOME / ".local/bin/ltspice-mcp.exe", _HOME / ".local/bin/ltspice-mcp"],
}


def find_tool(name: str) -> str | None:
    """PATH → 알려진 설치 위치 순서로 찾는다. 환경 변수 SNU_<NAME>(예: SNU_PANDOC)이 있으면 그걸 쓴다."""
    import os
    import shutil
    env = os.environ.get("SNU_" + name.upper().replace("-", "_"))
    if env and Path(env).exists():
        return env
    if name != "ltspice":
        hit = shutil.which(name)
        if hit:
            return hit
    for p in _KNOWN.get(name, []):
        if p.exists():
            return str(p)
    return None
