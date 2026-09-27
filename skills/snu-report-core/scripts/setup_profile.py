#!/usr/bin/env python3
"""작업 폴더 준비와 사용자 정보 설정 — 처음 쓰는 사람도 바로 쓸 수 있게.

  python setup_profile.py --check --course logic      # 매번 먼저: 설치할 것, 작업 폴더, 빠진 정보 (없으면 exit 0)
  python setup_profile.py --init                      # 현재 폴더를 작업 폴더로 (profile.yaml, inbox/, courses/, out/)
  python setup_profile.py --name 홍길동 --student-id 2025-12345 [--department 전기정보공학부] [--track 회로]
  python setup_profile.py --course logic --team 7 --teammates "김철수, 이영희"
  python setup_profile.py --style-sample <본인 보고서 .txt>

작업 폴더 = profile.yaml이 있는 폴더 (현재 폴더에서 위로 찾는다).
저장 위치: profile.yaml (개인 정보), courses/<과목>/course.yaml (조, 조원. 과목 기본값은 과목 스킬의 course.yaml).
--check 결과는 한 줄씩 `need:`(설치·준비), `missing:`(사용자에게 물을 것) 형식이라 AI가 그대로 처리할 수 있다.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ws import ENGINE, course_config, course_defaults, find_workspace, known_courses, remember_engine  # noqa: E402

ID_RE = re.compile(r"^\d{4}-\d{5}$")
NAME_RE = re.compile(r"^[가-힣A-Za-z]{2,20}$")
REQUIREMENTS = ENGINE.parent / "requirements.txt"
PY_MODULES = {"yaml": "pyyaml", "docx": "python-docx", "sympy": "sympy", "schemdraw": "schemdraw",
              "matplotlib": "matplotlib", "numpy": "numpy", "openpyxl": "openpyxl", "fitz": "pymupdf"}

# (항목, 필수 여부, 질문)
PROFILE_FIELDS = [
    ("name", True, "이름이 뭐야? (제출 파일명과 제목에 들어가)"),
    ("student_id", True, "학번은? (2025-12345 형식, 파일명에 들어가)"),
    ("department", False, "학과는? (비우면 전기정보공학부)"),
    ("track", False, "관심 분야나 트랙이 있어? (소감문에서 나와 연결할 때 씀, 없으면 비워도 돼)"),
]
COURSE_FIELDS = [
    ("team", True, "이 과목 몇 조야? (제목 블록에 들어가)"),
    ("teammates", False, "조원 이름은? (쉼표로, 없으면 비워도 돼)"),
]
PROFILE_HEAD = "# 개인 정보 (모든 과목 공통). 과목별 조·조원은 courses/<과목>/course.yaml\n"
PROFILE_BLANK = """name: ""              # 홍길동
student_id: ""        # 2025-12345
department: 전기정보공학부
track: ""             # 관심 분야·트랙 (소감문에 씀, 선택)
style_samples: []     # 본인이 쓴 보고서 .txt 경로 (선택)
"""
WS_GITIGNORE = """# 빌드 결과 (다시 만들 수 있음)
courses/*/*/build/
.snu-engine
__pycache__/
.DS_Store
~$*.docx
"""


def load(p: Path) -> dict:
    import yaml
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def save(p: Path, data: dict, header: str):
    import yaml
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(header + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def empty(v) -> bool:
    return v is None or (isinstance(v, str) and (not v.strip() or v.strip().startswith("["))) or v == []


def check_deps() -> list[str]:
    need = []
    miss = [pkg for mod, pkg in PY_MODULES.items() if importlib.util.find_spec(mod) is None]
    if miss:
        need.append(f"need: python 패키지 {', '.join(miss)} — pip install -r \"{REQUIREMENTS}\""
                    " (시스템 Python이 막으면 --break-system-packages 또는 --user)")
    if not shutil.which("pandoc"):
        need.append("need: pandoc — docx 변환에 필요. Windows: winget install JohnMacFarlane.Pandoc,"
                    " macOS: brew install pandoc, Linux: apt-get install pandoc")
    return need


def init_workspace(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if not (root / "profile.yaml").exists():
        (root / "profile.yaml").write_text(PROFILE_HEAD + PROFILE_BLANK, encoding="utf-8")
    for key in known_courses(None):
        (root / "inbox" / key).mkdir(parents=True, exist_ok=True)
        (root / "inbox" / key / ".gitkeep").touch()
    (root / "courses").mkdir(exist_ok=True)
    (root / "out").mkdir(exist_ok=True)
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(WS_GITIGNORE, encoding="utf-8")
    elif ".snu-engine" not in gi.read_text(encoding="utf-8"):
        gi.write_text(gi.read_text(encoding="utf-8").rstrip("\n") + "\n.snu-engine\n", encoding="utf-8")
    remember_engine(root)
    return root


def check(root: Path | None, course: str | None) -> list[str]:
    out = check_deps()
    if root is None:
        cwd = Path.cwd().resolve()
        where = "현재 폴더가 홈 폴더 자체라 ~/snu-reports를 만들어 거기서" if cwd == Path.home().resolve() else f"현재 폴더({cwd})를"
        out.append(f"need: 작업 폴더 없음 — {where} 작업 폴더로 만든다: python \"{ENGINE / 'setup_profile.py'}\" --init")
        out += [f"missing: {k} — {q}" for k, req, q in PROFILE_FIELDS if req]
        if course and "team" in course_defaults(course):
            out += [f"missing: {course}.{k} — {q}" for k, req, q in COURSE_FIELDS if req]
        return out
    remember_engine(root)
    prof = load(root / "profile.yaml")
    for k, req, q in PROFILE_FIELDS:
        if req and empty(prof.get(k)):
            out.append(f"missing: {k} — {q}")
    if not empty(prof.get("student_id")) and not ID_RE.match(str(prof["student_id"])):
        out.append(f"invalid: student_id={prof['student_id']} — 학번 형식이 2025-12345가 아니야. 다시 알려 줘")
    if course:
        if course not in known_courses(root):
            out.append(f"need: 과목 '{course}'을 모름 — 가능한 과목: {', '.join(known_courses(root))}")
        elif "team" in course_defaults(course):
            c = course_config(root, course)
            for k, req, q in COURSE_FIELDS:
                if req and empty(c.get(k)):
                    out.append(f"missing: {course}.{k} — {q}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, help="작업 폴더 (기본: 현재 폴더에서 profile.yaml을 위로 찾음)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--init", action="store_true", help="작업 폴더 만들기 (--root 또는 현재 폴더)")
    ap.add_argument("--course")
    ap.add_argument("--name")
    ap.add_argument("--student-id")
    ap.add_argument("--department")
    ap.add_argument("--track")
    ap.add_argument("--team")
    ap.add_argument("--teammates", help='쉼표로 구분 ("김철수, 이영희"). 학번까지: "김철수:2025-11111, 이영희"')
    ap.add_argument("--style-sample", action="append", help="사용자 본인이 쓴 보고서 텍스트 (문체 기준)")
    a = ap.parse_args()

    if a.init:
        root = init_workspace((a.root or Path.cwd()).resolve())
        print(f"✓ 작업 폴더: {root}")
    else:
        root = a.root.resolve() if a.root else find_workspace()

    if a.check:
        miss = check(root, a.course)
        print("\n".join(miss) if miss else f"ok: 설정 완료 (작업 폴더 {root})")
        sys.exit(1 if miss else 0)

    wants_write = any(x is not None for x in (a.name, a.student_id, a.department, a.track, a.team,
                                               a.teammates, a.style_sample))
    if not wants_write:
        return
    if root is None:
        sys.exit("✗ 작업 폴더 없음 — 먼저 --init")

    pp = root / "profile.yaml"
    prof = load(pp)
    changed = False
    if a.name:
        if not NAME_RE.match(a.name):
            sys.exit(f"✗ 이름 형식 확인: {a.name!r} (한글·영문 2–20자, 공백 없이)")
        prof["name"], changed = a.name, True
    if a.student_id:
        if not ID_RE.match(a.student_id):
            sys.exit(f"✗ 학번 형식 확인: {a.student_id!r} (2025-12345)")
        prof["student_id"], changed = a.student_id, True
    if a.department:
        prof["department"], changed = a.department, True
    if a.track is not None:
        prof["track"], changed = a.track, True
    if a.style_sample:
        cur = prof.get("style_samples") or []
        prof["style_samples"] = cur + [s for s in a.style_sample if s not in cur]
        changed = True
    if changed:
        if empty(prof.get("department")):
            prof["department"] = "전기정보공학부"
        save(pp, prof, PROFILE_HEAD)
        print(f"✓ {pp.relative_to(root)}")

    if a.course and (a.team is not None or a.teammates is not None):
        if a.course not in known_courses(root):
            sys.exit(f"✗ 과목 '{a.course}'을 모름 — 가능한 과목: {', '.join(known_courses(root))}")
        cp = root / "courses" / a.course / "course.yaml"
        c = load(cp) or {"key": a.course}
        if a.team is not None:
            c["team"] = str(a.team).replace("조", "").strip()
        if a.teammates is not None:
            mates = []
            for t in [x.strip() for x in a.teammates.split(",") if x.strip()]:
                n, _, sid = t.partition(":")
                mates.append({"name": n.strip(), "student_id": sid.strip()})
            c["teammates"] = mates
        head = cp.read_text(encoding="utf-8").split("\n", 1)[0] if cp.exists() else ""
        save(cp, c, head + "\n" if head.startswith("#") else
             "# 이 과목에서 나만 다른 값 (조, 조원). 과목명·파일명 규칙 기본값은 과목 스킬의 course.yaml\n")
        print(f"✓ {cp.relative_to(root)}")


if __name__ == "__main__":
    main()
