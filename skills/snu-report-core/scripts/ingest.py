#!/usr/bin/env python3
"""수업 자료 자동 분류: inbox/ 에 던져 둔 파일을 [Lab NN] 번호로 정리한다.

  python ingest.py                                   # inbox/<과목>/* 전부 처리 (logic, circuit …)
  python ingest.py --course logic                    # 한 과목만
  python ingest.py --course logic 파일1 파일2 ...     # 특정 파일 처리 (원본은 복사, 삭제 안 함)
  python ingest.py --course logic --lab 01 측정값.xlsx  # 파일명에 Lab 번호가 없을 때 직접 지정
  python ingest.py --dry-run                         # 어디로 갈지 미리 보기

과목 폴더: courses/<과목>/ (course.yaml이 있는 폴더). inbox/<과목>/에 올린 파일을 그 과목으로 분류한다.
seminar(소감문)처럼 Lab 번호가 없는 과목은 건너뛴다.

분류 규칙
  파일명에서 Lab 번호 인식:  "[Lab 01] ...", "[Lab01]", "Lab01_...", "Lab 1 ...", "lab01"
  Lab 00                → courses/<과목>/materials/          (공통 규칙: 보고서 가이드라인, 오리엔테이션)
  Lab NN                → courses/<과목>/labNN/materials/    (guidebook.pdf, slides_YYMMDD.pdf 등)
  prelabNN_학번_이름.*   → courses/<과목>/labNN/submitted/    (내가 낸 파일 사본)
  labNN_학번_이름.*      → courses/<과목>/labNN/submitted/
  .xlsx/.csv 등 데이터   → courses/<과목>/labNN/report/raw/
  이미지(.jpg/.png/.heic) → courses/<과목>/labNN/report/photos/
  번호 인식 실패         → inbox/<과목>/_unsorted/ 에 남기고 알려 줌

같은 내용(sha256) 파일은 한 번만 저장. PDF는 옆에 .txt(텍스트 추출)를 만들어 Claude가 바로 읽을 수 있게 한다.
Lab NN 자료가 새로 들어오면 courses/<과목>/labNN/meta.yaml, requirements.md 초안을 만든다 (이미 있으면 건드리지 않음).
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ws import find_tool, find_workspace, known_courses, remember_engine  # noqa: E402

PROFILE: dict = {}
UPLOAD_PREFIX = re.compile(r"^[0-9a-f]{8}-")  # claude 업로드가 붙이는 접두어
LAB_RE = re.compile(r"(?i)(?<![a-z])(pre)?\s*lab\s*[_\- ]?\s*(\d{1,2})(?!\d)")
SUBMIT_RE = re.compile(r"(?i)^(pre)?lab(\d{1,2})_(\d{4}-\d{5})_")
DATE6 = re.compile(r"(?<!\d)(2\d)(0[1-9]|1[0-2])([0-3]\d)(?!\d)")
DATA_EXT = {".xlsx", ".xls", ".csv", ".tsv", ".json"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".bmp", ".gif", ".webp"}
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}


# ───────────────────────── helpers ─────────────────────────
def find_root(start: Path) -> Path:
    return find_workspace(start) or start


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_name(name: str) -> str:
    name = UPLOAD_PREFIX.sub("", name)
    name = re.sub(r"_(\d)(?=\.\w+$)", "", name)  # "파일_1.pdf" 같은 중복 다운로드 꼬리표
    return name


def slug(s: str) -> str:
    s = re.sub(r"(?i)\[?\s*(pre)?lab\s*[_\- ]?\d{1,2}\s*\]?", "", s)
    s = re.sub(r"[^\w가-힣]+", "_", s).strip("_").lower()
    return s or "file"


def classify(path: Path, forced_lab: str | None):
    """→ (lab_num | None, 대상 하위 경로(폴더), 파일명)"""
    name = clean_name(path.name)
    stem, ext = Path(name).stem, Path(name).suffix.lower()

    m = SUBMIT_RE.match(name)
    if m:
        rest = name[m.end():-len(ext)] if ext else name[m.end():]
        if not re.search(r"[A-Za-z가-힣]", rest):  # 업로드 과정에서 한글 이름이 날아간 경우
            rest = PROFILE.get("name", "name")
        canon = f"{'prelab' if m.group(1) else 'lab'}{int(m.group(2)):02d}_{m.group(3)}_{rest}{ext}"
        return f"{int(m.group(2)):02d}", "submitted", canon

    lab = forced_lab
    if lab is None:
        m = LAB_RE.search(stem)
        if m:
            lab = f"{int(m.group(2)):02d}"
    if lab is None:
        return None, None, name

    if ext in DATA_EXT:
        return lab, "report/raw", name if re.search(r"[A-Za-z0-9가-힣]", Path(name).stem) else f"data{ext}"
    if ext in IMG_EXT:
        return lab, "report/photos", name

    low = stem.lower()
    if "guide" in low and "book" in low:
        new = "guidebook"
    elif "guideline" in low:
        new = "report_guideline"
    elif "introduction" in low:
        new = "introduction"
    elif re.search(r"tool", low):
        new = "experimental_tools"
    else:
        rest = slug(stem)
        if not rest or rest == "file":
            new = "slides"
        elif DATE6.fullmatch(rest):
            new = f"slides_{rest}"
        else:
            new = rest
    return lab, "materials", new + ext


def pdf_text(p: Path):
    if p.suffix.lower() != ".pdf":
        return
    if find_tool("pdftotext"):
        subprocess.run([find_tool("pdftotext"), "-layout", str(p), str(p.with_suffix(".txt"))], check=False)
        return
    try:   # pdftotext가 없으면 (Windows 등) pymupdf로
        import pymupdf
        with pymupdf.open(str(p)) as doc:
            p.with_suffix(".txt").write_text("\n\f".join(pg.get_text() for pg in doc), encoding="utf-8")
    except Exception as e:
        print(f"  (텍스트 추출 실패: {p.name}: {e})")


def dest_dir(croot: Path, lab: str, sub: str) -> Path:
    """croot = courses/<과목>"""
    if lab == "00":
        return croot / ("materials" if sub == "materials" else sub)
    return croot / f"lab{lab}" / sub


# ───────────────────────── requirement / meta drafts ─────────────────────────
def _date_from_text(text: str, year: int):
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})?", text)
    if not m:
        return None
    y = int(m.group(3)) if m.group(3) else year
    return dt.date(y, MONTHS[m.group(1).lower()], int(m.group(2)))


def _deadline(text: str, key: str, year: int):
    """'Submission deadline: 23:59 September 27 (Sun)' 류 파싱"""
    pat = {
        "prelab": r"(?is)Prelab report.*?(?:deadline|by)[:\s]*23:59\s+([A-Za-z]+)\s+(\d{1,2})",
        "report": r"(?is)(?<!pre)Lab Report\s.*?by\s+23:59\s+([A-Za-z]+)\s+(\d{1,2})",
    }[key]
    m = re.search(pat, text)
    if not m or m.group(1).lower() not in MONTHS:
        return None
    return dt.date(year, MONTHS[m.group(1).lower()], int(m.group(2)))


def _sunday_before(d: dt.date):
    return d - dt.timedelta(days=(d.weekday() + 1) % 7 or 7)


def _sunday_after(d: dt.date):
    return d + dt.timedelta(days=(6 - d.weekday()) or 7)


def draft_meta_and_requirements(lab_dir: Path, lab: str):
    mat = lab_dir / "materials"
    guide = mat / "guidebook.txt"
    slides = sorted(mat.glob("slides*.txt"))
    gtext = guide.read_text(encoding="utf-8", errors="ignore") if guide.exists() else ""
    stext = "\n".join(s.read_text(encoding="utf-8", errors="ignore") for s in slides)

    # meta.yaml
    meta_p = lab_dir / "meta.yaml"
    if not meta_p.exists():
        year = dt.date.today().year
        title = ""
        m = re.search(r"(?im)^\s*Lab\s*\d+\.\s*(.+?)\s*$\n?(.*)$", gtext)
        if m:
            title = (m.group(1) + (" " + m.group(2).strip() if m.group(2).strip() and not re.match(r"\d", m.group(2).strip()) else "")).strip()
        if not title:
            intro = lab_dir.parent / "materials" / "introduction.txt"
            if intro.exists():
                mm = re.search(rf"Lab\s*{lab}\s*:\s*(.+)", intro.read_text(encoding="utf-8", errors="ignore"))
                title = mm.group(1).strip() if mm else ""
        lab_date = _date_from_text(stext, year)
        notes = []
        pre = _deadline(stext, "prelab", year)
        rep = _deadline(stext, "report", year)
        if lab_date:
            rule_pre, rule_rep = _sunday_before(lab_date), _sunday_after(lab_date)
            if pre != rule_pre:
                notes.append(f"prelab 마감: 슬라이드 {pre} / 규칙상 {rule_pre} — 확인 필요")
                pre = rule_pre if pre is None or pre > lab_date else pre
            if rep != rule_rep:
                notes.append(f"report 마감: 슬라이드 {rep} / 규칙상 {rule_rep} — 확인 필요")
                rep = rule_rep if rep is None or rep < lab_date else rep
        meta = {
            "lab": int(lab),
            "title_en": title,
            "title": "[확인 필요: 한국어 제목]",
            "lab_date": str(lab_date) if lab_date else "[확인 필요]",
            "prelab_due": f"{pre} 23:59" if pre else "[확인 필요]",
            "report_due": f"{rep} 23:59" if rep else "[확인 필요]",
        }
        if notes:
            meta["_notes"] = notes
        meta_p.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print("  + meta.yaml 초안", *[f"\n    ⚠ {n}" for n in notes])

    # requirements.md
    req_p = lab_dir / "requirements.md"
    if not req_p.exists() and (gtext or stext):
        parts = [f"# Lab {lab} 요구사항 (자동 추출 초안 — 원문과 대조 후 사용)\n"]
        for label, pat in (("Prelab", r"Prelab"), ("Lab (실험)", r"Lab"),
                           ("Discussion and Matters to Consider", r"Discussion and Matters to Consider")):
            m = re.search(rf"(?ms)^\s*(\d+)\.\s+{pat}\s*$(.*?)(?=^\s*\d+\.\s+[A-Z][a-z]|\Z)", gtext)
            if m:
                body = re.sub(r"\n{3,}", "\n\n", m.group(2)).rstrip()
                parts.append(f"## guidebook {m.group(1)}. {label}\n\n```\n{body}\n```\n")
        keep = [ln.strip() for ln in stext.splitlines()
                if re.search(r"(?i)goal|only|must|include|answer|deadline|submit|checklist|measure|don.t have to|\d\.\d|\b[0-9]\.[a-g]\b|\b\d[a-g]\b", ln)]
        if keep:
            parts.append("## 슬라이드에서 뽑은 지시 (범위·마감·필수 항목)\n\n```\n" + "\n".join(keep) + "\n```\n")
        parts.append("## 보고서 대응표 (Claude가 채움)\n\n| 요구 항목 | 보고서 위치 | 상태 |\n|:--|:--|:--|\n")
        req_p.write_text("\n".join(parts), encoding="utf-8")
        print("  + requirements.md 초안")


# ───────────────────────── main ─────────────────────────
LAB_COURSES_SKIP = {"seminar"}   # Lab 번호로 분류하지 않는 과목


def process(root: Path, course: str, files: list[Path], from_inbox: bool, forced: str | None, dry: bool):
    croot = root / "courses" / course
    inbox = root / "inbox" / course
    if course not in known_courses(root):
        sys.exit(f"✗ 과목 '{course}'을 모름 — 가능한 과목: {', '.join(known_courses(root))}")
    if not dry:
        croot.mkdir(parents=True, exist_ok=True)
    reg_p = croot / ".ingest.json"
    reg = json.loads(reg_p.read_text(encoding="utf-8")) if reg_p.exists() else {}
    touched_labs = set()
    seen = {}
    print(f"[{course}]")
    for f in files:
        h = sha(f)
        lab, sub, name = classify(f, forced)
        if h in seen:
            print(f"= 중복 건너뜀: {f.name} (같은 내용: {seen[h]})")
            if from_inbox and not dry:
                f.unlink()
            continue
        seen[h] = f.name
        if h in reg:
            print(f"= 중복 건너뜀: {f.name} (이미 {reg[h]['path']})")
            if from_inbox and not dry:
                f.unlink()
            continue
        if lab is None:
            print(f"? Lab 번호 인식 실패: {f.name} → inbox/{course}/_unsorted (--lab NN 으로 다시 실행)")
            if not dry:
                (inbox / "_unsorted").mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), inbox / "_unsorted" / f.name) if from_inbox else shutil.copy2(f, inbox / "_unsorted" / f.name)
            continue
        d = dest_dir(croot, lab, sub)
        target = d / name
        if target.exists() and sha(target) != h:  # 같은 이름 다른 내용 → 버전 보존
            target = d / f"{target.stem}_{dt.date.today():%y%m%d}{target.suffix}"
        print(f"→ {f.name}  ⇒  {target.relative_to(root)}")
        if dry:
            continue
        d.mkdir(parents=True, exist_ok=True)
        (shutil.move if from_inbox else shutil.copy2)(str(f), target)
        pdf_text(target)
        reg[h] = {"path": str(target.relative_to(root)), "original": f.name, "at": dt.datetime.now().isoformat(timespec="seconds")}
        if lab != "00":
            touched_labs.add(lab)

    if dry:
        return
    reg_p.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")

    for lab in sorted(touched_labs):
        ld = croot / f"lab{lab}"
        for sub in ("prelab/figs", "report/figs", "report/photos", "report/scope", "report/raw", "submitted"):
            (ld / sub).mkdir(parents=True, exist_ok=True)
        print(f"  [lab{lab}]")
        draft_meta_and_requirements(ld, lab)

    # 자료 목록
    for idx_dir in [croot / "materials", *sorted(croot.glob("lab*/materials"))]:
        if idx_dir.exists():
            rows = [f"| {p.name} | {p.stat().st_size // 1024} KB |" for p in sorted(idx_dir.iterdir())
                    if p.is_file() and p.suffix != ".txt" and p.name != "INDEX.md"]
            (idx_dir / "INDEX.md").write_text("| 파일 | 크기 |\n|:--|--:|\n" + "\n".join(rows) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--course", help="과목 폴더 이름 (logic, circuit …). 생략하면 inbox/의 모든 과목")
    ap.add_argument("--lab", help="Lab 번호 강제 지정 (예: 01)")
    ap.add_argument("--root", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root = (a.root or find_root(Path.cwd())).resolve()
    remember_engine(find_workspace(root))
    if (root / "profile.yaml").exists():
        PROFILE.update(yaml.safe_load((root / "profile.yaml").read_text(encoding="utf-8")) or {})
    forced = f"{int(a.lab):02d}" if a.lab else None

    if a.files:
        if not a.course:
            sys.exit("✗ 파일을 직접 줄 때는 --course를 같이 준다 (예: --course logic)")
        process(root, a.course, a.files, False, forced, a.dry_run)
        return

    inbox_root = root / "inbox"
    courses = [a.course] if a.course else sorted(d.name for d in inbox_root.iterdir()
                                                if d.is_dir() and d.name not in LAB_COURSES_SKIP) if inbox_root.exists() else []
    done = False
    for c in courses:
        inbox = root / "inbox" / c
        files = sorted(p for p in inbox.glob("*") if p.is_file() and not p.name.startswith("."))
        if files:
            process(root, c, files, True, forced, a.dry_run)
            done = True
    if not done:
        print("처리할 파일 없음 (inbox/<과목>/)")


if __name__ == "__main__":
    sys.exit(main())
