#!/usr/bin/env python3
"""오탈자·표기 검사 — 원고(.md)나 빌드한 보고서(.docx)를 읽는다 (references/proofreading.md)

  python proof.py courses/logic/lab02/prelab/prelab.md
  python proof.py courses/logic/lab02/build/prelab02_2025-12345_홍길동.docx    # 빌드 결과 최종 확인
  python proof.py 원고.md --strict                                            # 걸린 것이 있으면 종료 코드 1

찾는 것
  1. 조사 받침 불일치            (조건를, 회로을, 저항와, 출력로)
  2. 같은 낱말 연속               (의 의, 게이트 게이트)
  3. 게이트 이름 오타·혼동        (NAD, XNR, NXOR / 7402(XOR), 7486(NOR) — 칩 번호와 게이트 종류가 다름)
  4. 게이트 나열에 쉼표 빠짐      (NOT AND OR → NOT, AND, OR)
  5. 자주 틀리는 맞춤법·띄어쓰기  (되요, 몇일, 할수 있, 할때, 역활, 갯수 …)
  6. 률/율                        (모음·ㄴ 받침 뒤 '율', 그 밖 '률': 오차율, 확률)
  7. 숫자와 단위 붙여 씀          (5V → 5 V, 퍼센트만 붙임)
  8. 같은 기호를 수식과 일반 글자로 섞어 씀 ($F_0$와 F0)
  9. 괄호 짝, 겹친 문장부호       ((…, .., ,,)
 10. 제목의 가이드북 문항 번호에 ')' 빠짐 (4.2 → 4.2), 가 → 가))
 11. (.docx) 풀리지 않은 참조 ??fig, 남은 [TODO] 표시, 빈 절

build.py가 원고를 빌드할 때 자동으로 돌린다. 걸린 곳은 원고에서 고친다.
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import re
import sys
from pathlib import Path

# ───────────────────────── 제목 번호 ─────────────────────────
KO_ENUM = "가나다라마바사아자차카타파하"
# 가이드북 문항 번호: 4.2 / 9.2.2 / 4.a / 5.f / 6b / 4.f)a  (점이 하나 이상이거나 숫자+영문 한 글자)
GUIDE_NUM = r"\d+(?:\.\d+)+(?:\.?[a-z])?|\d+\.[a-z]|\d+[a-z](?![a-z])"
HEAD_LABEL_RE = re.compile(rf"^(?P<num>{GUIDE_NUM})(?P<tail>\)[a-z]\)?|\)|\.)?(?=\s)\s+(?P<rest>.*)$")
KO_LABEL_RE = re.compile(rf"^(?P<ko>[{KO_ENUM}])(?:\)|\.|(?=\s))\s*(?P<rest>.+)$")


def fix_heading(text: str, parent: str | None) -> tuple[str, str | None]:
    """제목 글자 → (고친 글자, 이 제목의 문항 번호). 문항 번호에 ')'를 붙이고,
    상위 절과 같은 번호가 되풀이되면 뺀다: '4.2 가 설계' (상위 4.2) → '가) 설계'."""
    m = HEAD_LABEL_RE.match(text)
    num = None
    rest = text
    if m:
        num = m["num"]
        tail = m["tail"] or ""
        rest = m["rest"]
        if tail.startswith(")") and len(tail) > 1:        # 4.f)a 같은 가이드북 원래 표기
            num = num + tail.rstrip(")")
    k = KO_LABEL_RE.match(rest)
    if k and (num or len(k["rest"]) > 1):
        ko = k["ko"] + ")"
        if num and parent and num == parent:
            return f"{ko} {k['rest']}", num
        if num:
            return f"{num}) {ko} {k['rest']}", num
        return f"{ko} {k['rest']}", None
    if num:
        return f"{num}) {rest}", num
    return text, None


HEAD_MD_RE = re.compile(r"^(?P<hash>#{1,3})\s+(?P<text>.+?)(?P<attr>\s*\{[^}]*\})?\s*$")


def normalize_headings(md: str) -> tuple[str, list[str]]:
    """원고의 # 제목에서 가이드북 문항 번호를 '4.2)' 꼴로 맞춘다. → (새 원고, 바꾼 목록)"""
    out, changes = [], []
    labels: list[str | None] = [None, None, None]
    in_code = False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        m = None if in_code else HEAD_MD_RE.match(line)
        if not m:
            out.append(line)
            continue
        lvl = len(m["hash"])
        parent = next((labels[i] for i in range(lvl - 2, -1, -1) if labels[i]), None)
        new, num = fix_heading(m["text"].strip(), parent)
        labels[lvl - 1] = num
        for i in range(lvl, 3):
            labels[i] = None
        if new != m["text"].strip():
            changes.append(f"'{m['text'].strip()}' → '{new}'")
        out.append(f"{m['hash']} {new}{m['attr'] or ''}")
    return "\n".join(out) + ("\n" if md.endswith("\n") else ""), changes


# ───────────────────────── 본문 추출 ─────────────────────────
def plain(md: str) -> str:
    """수식은 ⟨M⟩, 코드·그림·HTML 주석은 지운다 (줄 구조는 남긴다)"""
    t = re.sub(r"(?s)```.*?```", "", md)
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    t = re.sub(r"`[^`\n]*`", "⟨C⟩", t)          # 인라인 코드
    t = re.sub(r"(?s)\$\$.*?\$\$", " ⟨M⟩ ", t)
    t = re.sub(r"\$[^$\n]+\$", "⟨M⟩", t)
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)(\{[^}]*\})?", r"\1", t)
    t = re.sub(r"\{#(?:fig|tbl):[^}]*\}", "", t)
    t = re.sub(r"@(fig|tbl):[A-Za-z0-9_-]+", "Fig.1", t)
    return t


def docx_text(path: Path) -> str:
    from docx import Document
    doc = Document(path)
    lines = []
    body = doc.element.body
    for el in body.iter():
        if el.tag.endswith("}p"):
            style = el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
            sid = style.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "") if style is not None else ""
            if "Code" in sid or "Source" in sid:   # 코드 블록은 글이 아니다
                continue
            txt = "".join(t.text or "" for t in el.iter() if t.tag.endswith("}t"))
            # Word 수식(m:t)은 기호 검사에서 수식으로 본다
            has_math = any(t.tag.endswith("}oMath") for t in el.iter())
            lines.append(txt + (" ⟨M⟩" if has_math else ""))
    return "\n\n".join(lines)   # 문단마다 빈 줄 (원고와 같게)


# ───────────────────────── 검사 ─────────────────────────
def _batchim(ch: str) -> int | None:
    o = ord(ch) - 0xAC00
    return o % 28 if 0 <= o < 11172 else None


PARTICLES = {"이": True, "은": True, "을": True, "과": True, "가": False, "는": False, "를": False, "와": False}
_KIWI = None


def _kiwi():
    global _KIWI
    if _KIWI is None:
        try:
            from kiwipiepy import Kiwi
            _KIWI = Kiwi()
        except Exception:
            _KIWI = False
    return _KIWI


def particle_warnings(text: str) -> list[str]:
    """명사 + 조사 받침 불일치 (조건를, 출력로). 형태소 분석(kiwipiepy)으로
    바른 꼴(조건을)이 '명사 + 조사'로 훨씬 자연스럽게 읽힐 때만 잡는다 (증가, 재평가 같은 낱말은 통과)."""
    k = _kiwi()
    if not k:
        return []
    out, seen = [], set()
    swap = {"이": "가", "가": "이", "은": "는", "는": "은", "을": "를", "를": "을", "과": "와", "와": "과"}
    for m in re.finditer(r"(?<![가-힣])([가-힣]{1,8}?)(으로|로|이|가|은|는|을|를|과|와)(?=[\s.,)·:;]|$)", text):
        stem, pa = m.group(1), m.group(2)
        word = stem + pa
        b = _batchim(stem[-1])
        if b is None or word in seen:
            continue
        if pa in ("으로", "로"):
            good = "로" if b in (0, 8) else "으로"
        else:
            if PARTICLES[pa] == (b != 0):
                continue
            good = swap[pa]
        if good == pa:
            continue
        seen.add(word)
        fixed = stem + good
        r_bad = k.analyze(word, top_n=1)[0]
        r_good = k.analyze(fixed, top_n=1)[0]
        toks = r_good[0]
        if not toks or not toks[-1].tag.startswith("J") or toks[-1].form != good:
            continue
        if not any(t.tag.startswith(("NN", "XR", "NR")) for t in toks[:-1]):
            continue
        if r_good[1] - r_bad[1] > 1.5:   # 바른 꼴이 더 자연스러울 때만 (실제 낱말은 음수)
            out.append(f"[조사] '{word}' → '{fixed}'")
    return out


GATES = ("AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR")
CHIP_FUNC = {"7400": "NAND", "7402": "NOR", "7404": "NOT", "7408": "AND", "7410": "NAND", "7411": "AND",
             "7420": "NAND", "7427": "NOR", "7432": "OR", "7486": "XOR", "74266": "XNOR", "7421": "AND"}
NOT_GATE_WORDS = {"GND", "VDD", "VCC", "ADD", "END", "AID", "OUT", "NET", "SET", "NPN", "PNP", "LED", "CLK", "NOW", "ORG",
                  "DC", "AC", "ON", "OK", "IN", "OF", "IR", "NMOS", "PMOS", "CMOS", "TTL", "ROM", "RAM", "SOP", "POS",
                  "NA", "ND", "NO", "OX", "XO", "OSC", "DOR", "MOR", "ANY", "AD", "AN"}


def _near(a: str, b: str) -> bool:
    """편집 거리 1 또는 이웃 글자 자리바꿈"""
    if a == b:
        return False
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    s, l_ = (a, b) if len(a) < len(b) else (b, a)
    return any(l_[:i] + l_[i + 1:] == s for i in range(len(l_)))


COMMON = [  # (틀린 꼴 정규식, 바른 꼴)
    (r"되요", "돼요"), (r"됬", "됐"), (r"몇일", "며칠"), (r"않되", "안 되"), (r"(?<![가-힣])안되", "안 되"),
    (r"할수(?= ?있| ?없)", "할 수"), (r"(?<=[을를])수있", "수 있"), (r"(?<![가-힣])수있", "수 있"),
    (r"(?<=[할될볼잴쓸줄갈올일])때(?![문])", " 때 (띄어 씀)"), (r"것같", "것 같"),
    (r"것이였", "것이었"), (r"(?<=[가-힣])이였다", "이었다"), (r"왠만", "웬만"), (r"금새", "금세"), (r"역활", "역할"),
    (r"일일히", "일일이"), (r"갯수", "개수"), (r"촛점", "초점"), (r"싯점", "시점"), (r"댓가", "대가"),
    (r"설겆이", "설거지"), (r"어떻해", "어떡해"),
    (r"뿐만아니라", "뿐만 아니라"), (r"에서 부터", "에서부터"), (r"(?<![가-힣])할 지(?= )", "할지"),
    (r"측정 치", "측정치"), (r"계산 값", "계산값"), (r"측정 값", "측정값"),
    (r"이론 값", "이론값"), (r"오실로 스코프", "오실로스코프"), (r"브레드 보드", "브레드보드"),
]
UNITS = r"(?:ns|us|µs|μs|ms|mV|V|mA|µA|μA|kΩ|MΩ|Ω|Hz|kHz|MHz|pF|nF|µF|μF|uF|mH|µH|dB)"


def _top_level_split(expr: str) -> list[str]:
    """중괄호·괄호 밖의 ',', '\\quad', '\\qquad'로 나눈다."""
    parts, depth, cur, i = [], 0, "", 0
    while i < len(expr):
        c = expr[i]
        if c in "{([":
            depth += 1
        elif c in "})]":
            depth -= 1
        if depth == 0 and (c == "," or expr.startswith("\\qquad", i) or expr.startswith("\\quad", i)):
            parts.append(cur)
            cur = ""
            i += 6 if expr.startswith("\\qquad", i) else (5 if c == "\\" else 1)
            continue
        cur += c
        i += 1
    parts.append(cur)
    return [x for x in parts if x.strip()]


def math_layout_warnings(md: str) -> list[str]:
    """문장 속 수식은 짧게(기호, 짧은 등식), 분수·긴 식은 따로 한 줄. 따로 뺀 줄에는 식 하나(많아야 둘)."""
    w = []
    body = re.sub(r"(?s)```.*?```", "", md)
    for m in re.finditer(r"(?s)\$\$(.+?)\$\$", body):
        eqs = [x for x in _top_level_split(m.group(1)) if "=" in x]
        if len(eqs) >= 3:
            w.append(f"[수식] 한 줄에 식 {len(eqs)}개 — 한 줄에 하나(많아야 둘)씩 $$로 나눈다: \"{m.group(1).strip()[:50]}…\"")
    inline = re.sub(r"(?s)\$\$.+?\$\$", "", body)
    for m in re.finditer(r"(?<![\\$])\$([^$\n]+)\$", inline):
        e = m.group(1)
        core = re.sub(r"\\(?:text|mathrm|operatorname)\{[^}]*\}|\\[A-Za-z]+|[\s{}]", "x", e)
        why = None
        if "\\frac" in e or "\\sum" in e or "\\int" in e:
            why = "분수·합·적분"
        elif "/" in e and "(" in e:
            why = "괄호 나눗셈"
        elif len(core) > 28:
            why = "길이"
        if why:
            w.append(f"[수식] 문장 속 수식이 길다({why}): ${e[:40]}$ — 문장을 끝내고 다음 줄에 $$…$$로 뺀다")
    return w


META_TALK = [   # (정규식, 이유) — 보고서가 본인이 쓴 글로 읽히게
    (r"사용자(?!\s*정의)", "'사용자'라고 쓰지 않는다. 본인이 한 일은 주어 없이 '~했다'"),
    (r"(?<![A-Za-z])AI(?![A-Za-z])|인공지능|ChatGPT|Claude|GPT", "AI를 언급하지 않는다"),
    (r"제공(?:된|한|받은|해 준)", "받은 자료처럼 쓰지 않는다 (skeleton은 '실습 자료의 skeleton')"),
    (r"(?:촬영|캡처|캡쳐)(?:한|된|했|해)", "화면 캡처라고 쓰지 않는다. 그림은 그냥 'Fig.1 - Problem 1 코드'"),
    (r"수정\s*(?:전|후|한\s*제출용)|원본\s*(?:MATLAB|코드)", "코드를 누가 고쳤는지 드러내지 않는다"),
    (r"(?:작성|생성)해\s*(?:주|드리)|요청(?:에 따라|하신|한 대로)", "대화체·작업 과정을 쓰지 않는다"),
]


def check_text(text: str, is_docx: bool = False) -> list[str]:
    w = []
    body = plain(text) if not is_docx else text
    lines = body.splitlines()
    prose = "\n".join(ln for ln in lines if not re.match(r"\s*\|", ln))   # 표 줄 제외 (표는 따로)

    # 1. 조사
    w += particle_warnings(prose)

    # 2. 같은 낱말 연속
    for m in re.finditer(r"(?<![\w가-힣])([가-힣A-Za-z]{1,12})\s+\1(?![\w가-힣])", prose):
        if m.group(1) not in ("각", "하나", "때때"):
            w.append(f"[반복] '{m.group(0)}'")

    # 3. 게이트 이름 오타, 칩 번호와 게이트 종류
    for m in re.finditer(r"(?<![A-Za-z])([A-Z]{3,5})(?![A-Za-z])", body):
        tok = m.group(1)
        if tok in GATES or tok in NOT_GATE_WORDS:
            continue
        near = [g for g in GATES if _near(tok, g)] if tok != "NXOR" else []
        if near:
            w.append(f"[게이트 이름] '{tok}' — {' / '.join(near)}의 오타인지 확인")
    for m in re.finditer(r"(?<!\d)(74(?:LS|HC|HCT|F|S|ALS)?)(\d{2,3})(?!\d)", body):
        chip = "74" + m.group(2)
        func = CHIP_FUNC.get(chip)
        if not func:
            continue
        ctx = body[max(0, m.start() - 14): m.end() + 14]
        words = set(re.findall(r"(?<![A-Za-z])(X?N?(?:AND|OR|NOT)|XOR|XNOR|NAND|NOR)(?![A-Za-z])", ctx))
        wrong = {x for x in words if x != func}
        if wrong and func not in words:
            w.append(f"[칩·게이트] '{' '.join(ctx.split())}' — {chip}는 {func} 칩인데 {', '.join(sorted(wrong))}와 같이 씀")
    if re.search(r"(?<![A-Za-z])NXOR(?![A-Za-z])", body):
        w.append("[게이트 이름] 'NXOR' → 'XNOR'")

    # 4. 게이트 나열 쉼표
    for m in re.finditer(r"(?<![A-Za-z-])((?:" + "|".join(GATES) + r")(?:\s+(?:" + "|".join(GATES) + r")){1,})(?![A-Za-z-])", prose):
        if len(m.group(1).split()) >= 2:
            w.append(f"[쉼표] '{m.group(1)}' → '{', '.join(m.group(1).split())}'")

    # 5. 자주 틀리는 말
    for pat, good in COMMON:
        for m in re.finditer(pat, prose):
            ctx = prose[max(0, m.start() - 6): m.end() + 6].replace("\n", " ")
            w.append(f"[맞춤법] '…{ctx}…' → {good}")

    # 6. 률/율
    for m in re.finditer(r"([가-힣])(률|율)", prose):
        b = _batchim(m.group(1))
        if b is None:
            continue
        good = "율" if b in (0, 4) else "률"
        if m.group(2) != good:
            w.append(f"[맞춤법] '{m.group(0)}' → '{m.group(1)}{good}' (모음·ㄴ 받침 뒤 '율', 그 밖 '률')")

    # 7. 숫자·단위 붙여 씀
    for m in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?(" + UNITS + r")(?![A-Za-z])", prose):
        w.append(f"[단위] '{m.group(0)}' → 숫자와 단위 사이를 띄운다")

    # 8. 수식 기호와 일반 글자 섞임 (원고에서만: $F_0$와 F0)
    if not is_docx:
        subs = set(re.findall(r"\$[^$]*?\b([A-Za-z])_\{?([0-9A-Za-z]{1,3})\}?", text))
        for base, sub in subs:
            if re.search(rf"(?<![\w$\\{{_]){base}{sub}(?![\w])", prose) or re.search(rf"(?<![\w$\\]){base}_{sub}(?![\w])", prose):
                w.append(f"[기호] '{base}{sub}'를 일반 글자로 쓴 곳이 있음 — 수식 ${base}_{{{sub}}}$로 통일")

    # 9. 괄호 짝, 겹친 문장부호
    for i, para in enumerate(re.split(r"\n\s*\n", prose), 1):
        p = re.sub(r"\d+\.[a-z]\)[a-z]", "", para)     # 가이드북 표기 4.f)a
        p = re.sub(rf"(?:^|(?<=\s))(?:{GUIDE_NUM}|\d{{1,2}}|[a-z]|[{KO_ENUM}])\)(?=\s)", "", p, flags=re.M)   # 1) 가) 4.2) 같은 번호는 뺀다
        if p.count("(") != p.count(")"):
            w.append(f"[괄호] 문단 {i}: '(' {p.count('(')}개, ')' {p.count(')')}개 — \"{para.strip()[:40]}…\"")
    for m in re.finditer(r"(?<!\.)\.\.(?!\.)|,,|\s[.,](?=\s)|\.\s+\.(?!\.)", prose):
        ctx = prose[max(0, m.start() - 8): m.end() + 8].replace("\n", " ")
        w.append(f"[문장부호] '…{ctx}…'")

    # 10. 제목 번호
    if is_docx:
        for ln in lines:
            m = re.match(rf"^\s*(\d+\.(?:\d+\))*)\s+({GUIDE_NUM})(?![\d)])\s", ln)
            if m and len(ln) < 120:
                w.append(f"[제목 번호] '{ln.strip()[:40]}' — 문항 번호 {m.group(2)} 뒤에 ')'")
    else:
        _, ch = normalize_headings(text)
        for c in ch:
            w.append(f"[제목 번호] {c} (build.py가 자동으로 고침)")

    # 13. 본인 글: 보고서는 학생 본인이 쓴 글이다. AI·작업 과정이 드러나는 말을 쓰지 않는다
    for pat, why in META_TALK:
        for m in re.finditer(pat, prose):
            ctx = prose[max(0, m.start() - 10): m.end() + 10].replace("\n", " ")
            w.append(f"[본인 글] '…{ctx}…' — {why}")

    # 12. 수식 배치 (원고에서만): 문장 속 긴 수식·분수, 한 줄에 식 여러 개
    if not is_docx:
        w += math_layout_warnings(text)

    # 11. 빌드 결과 전용
    if is_docx:
        for m in re.finditer(r"\?\?(?:fig|tbl):\S+", body):
            w.append(f"[참조] 풀리지 않은 참조 {m.group(0)}")
        for m in re.finditer(r"\[(TODO|미제공|확인 필요|판독 불가)[^\]]*\]", body):
            w.append(f"[표시] 남은 상태 표시 {m.group(0)[:30]}")
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    if a.file.suffix.lower() == ".docx":
        warns = check_text(docx_text(a.file), is_docx=True)
    else:
        warns = check_text(a.file.read_text(encoding="utf-8"))
    if not _kiwi():
        print("  (kiwipiepy가 없어 조사 검사를 건너뜀: pip install kiwipiepy)")
    if not warns:
        print("✓ 오탈자 검사 통과")
        return 0
    print(f"오탈자 검사: {len(warns)}건")
    for x in warns:
        print("  ⚠", x)
    return 1 if a.strict else 0


if __name__ == "__main__":
    sys.exit(main())
