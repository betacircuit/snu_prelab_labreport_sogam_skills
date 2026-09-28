#!/usr/bin/env python3
"""원고 문체 검사 — AI 티가 나는 반복을 찾는다 (writing.md 규칙)

  python style_check.py courses/logic/lab01/report/report.md
  python style_check.py report.md --strict     # 경고가 있으면 종료 코드 1

찾는 것
  1. 같은 어미가 3문장 이상 연속           (~였다. ~였다. ~였다.)
  2. 같은 말로 시작하는 문장이 한 문단에 2번 이상 / 문서 전체에 4번 이상
  3. 접속어·지시어 남용                    (따라서, 또한, 즉, 이는 … 문서 전체 2번 초과)
  4. 쓰지 않는 표현                         (writing.md 목록)
  5. 추측 표현이 한 문단에 2번 이상         (가능성, ~로 보인다)
  6. 3어절 이상 같은 구절이 3번 이상 반복
  7. 너무 짧은 문장이 연속 (15자 이하 3개 연속)
  8. 문장 길이가 너무 고른 문단 (문장 4개 이상, 길이 편차가 작음) — 기계적인 리듬
  9. 본문·목록의 굵은 글씨 (굵게는 제목과 절 제목에만)
 10. '기타'(9.3.x) 절이 세 문장을 넘음
 11. 같은 서술어(쓰다, 넣다, 길다, 확인하다 …)가 문서 전체에서 잦음 (4번 이상이면서 1000자당 2번 이상)
 12. 같은 서술어가 한 문단에 3번 이상
     뜻이 바뀌어 바꿀 수 없는 말(LED가 켜지다 등)은 원고에 <!-- 어휘 허용: 켜다, 따르다 --> 로 적어 둔다.
     형태소 분석은 kiwipiepy. 없으면 ~하다/~되다 서술어만 본다.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

CONNECTIVES = ["따라서", "또한", "즉", "한편", "그러므로", "이는", "이때", "그리고", "하지만", "그러나", "다만"]
BANNED = ["에 대해 알아보", "라고 할 수 있", "매우 ", "다양한", "성공적으로", "효과적으로", "중요한 역할",
          "본 절에서는", "본 실험에서는", "를 통해", "을 통해", "에 있어서", "것을 알 수 있었다",
          "첫째,", "둘째,", "셋째,", "가지이다", "가지다.",
          # 소감문 상투 표현 (skills/snu-ece-seminar/references/sogam.md)
          "감명을 받았", "깊이 깨달", "뜻깊은 시간", "유익한 시간", "더욱 노력하", "열정이 느껴"]
HEDGES = ["가능성", "보인다", "추정된다"]

# ───────── 어휘 반복 (서술어) ─────────
LIGHT_PRED = {"하다", "되다", "있다", "없다", "않다", "이다", "아니다", "같다", "대하다", "위하다", "통하다", "관하다",
              "흐르다", "켜다", "끄다", "꺼지다"}   # 끝줄: 바꿀 말이 없는 물리 현상 (전류가 흐르다, LED가 켜지다)
PRED_ALT = {   # 뜻에 따라 바꿀 말 (용어·기호는 바꾸지 않는다)
    "쓰다": "법칙은 적용하다, 식은 '~은 다음과 같다', 게이트·소자는 필요하다·들다, 도구는 '~로 ~하다'",
    "넣다": "신호는 인가하다·가하다, 입력 핀은 연결하다·물리다",
    "묶다": "입력은 함께 연결하다·합치다, K-map은 한 묶음으로 덮다·잡다",
    "길다": "늦다, N ns 더 걸리다, 차이가 N ns다, N배, 늘다 — 또는 짧은 쪽을 주어로",
    "짧다": "빠르다, N ns 덜 걸리다, 줄다 — 또는 긴 쪽을 주어로",
    "따르다": "~마다, ~별, '~이 0일 때와 1일 때', '~을 바꾸면'",
    "확인하다": "읽다, 보다, 맞다, 드러나다 — 또는 수치를 바로 말한다",
    "나타나다": "주어+서술어로 바로 ('지연이 14 ns였다')",
    "보이다": "주어+서술어로 바로, 또는 '~로 읽힌다', '~에 가깝다'",
    "측정하다": "재다, 읽다, 기록하다",
    "증가하다": "늘다, 커지다, 올라가다, 길어지다",
    "감소하다": "줄다, 작아지다, 내려가다, 짧아지다",
    "일치하다": "맞다, 같다, 차이가 N 안이다",
    "발생하다": "생기다, 나다",
    "사용하다": "쓰다, 두다, 또는 구체 동사(연결하다, 재다)",
    "연결하다": "물리다, 잇다, 꽂다, (프로브를) 대다",
    "두다": "고정하다, 놓다, 맞추다, (값을) 주다",
    "만들다": "구성하다, 꾸미다, 얻다, 나오다",
}
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


_HADA = re.compile(r"(?<![가-힣])([가-힣]{2,4}?)(하였|했|한다|하면|하여|해서|하고|하는|하지|한|할|해|되었|됐|된다|되면|되어|돼|되고|되는|되지|된|될)(?![가-힣]{3})")


def predicates(text: str) -> list[str]:
    """서술어 원형 목록 (쓰다, 확인하다 …). 가벼운 서술어(하다, 되다, 있다 …)는 뺀다."""
    k = _kiwi()
    out = []
    if k:
        toks = k.tokenize(text)
        for i, t in enumerate(toks):
            if t.tag in ("XSV", "XSA") and i and toks[i - 1].tag in ("NNG", "XR"):
                out.append(toks[i - 1].form + ("되다" if t.form.startswith("되") else "하다"))
            elif t.tag in ("VV", "VA") or t.tag.startswith(("VV-", "VA-")):
                out.append(t.form + "다")
    else:   # 형태소 분석기가 없으면 ~하다/~되다만
        for m in _HADA.finditer(text):
            out.append(m.group(1) + ("되다" if m.group(2)[0] in "되됐돼된될" else "하다"))
    return [w for w in out if w not in LIGHT_PRED]


def allowed_words(md: str) -> set[str]:
    words = set()
    for m in re.finditer(r"<!--\s*어휘\s*허용\s*:(.*?)-->", md, flags=re.S):
        words |= {w.strip() if w.strip().endswith("다") else w.strip() + "다" for w in m.group(1).split(",") if w.strip()}
    return words


def lexical_warnings(md: str, paras: list[str]) -> list[str]:
    allow = allowed_words(md)
    warns = []
    per_para = [predicates(p) for p in paras]
    total = Counter(w for ps in per_para for w in ps)
    chars = sum(len(re.sub(r"\s", "", p)) for p in paras) or 1
    for w, n in total.most_common():
        rate = n * 1000 / chars
        if n >= 4 and rate >= 2.0 and w not in allow:
            hint = PRED_ALT.get(w, "뜻에 맞는 구체적인 동사로 바꾸거나, 문장 틀(비교·원인·수치 먼저)을 바꾼다")
            warns.append(f"[어휘 반복] '{w}' {n}번 (1000자당 {rate:.1f}) → {hint}")
    for pi, ps in enumerate(per_para, 1):
        for w, n in Counter(ps).items():
            if n >= 3 and w not in allow:
                warns.append(f"[어휘 반복] 문단 {pi}: '{w}' {n}번 → 두 번째부터 다른 말로")
    if not _kiwi():
        warns.append("[참고] kiwipiepy가 없어 ~하다/~되다 서술어만 검사함 (pip install kiwipiepy)")
    return warns


def strip_md(text: str) -> str:
    text = re.sub(r"(?s)```.*?```", "", text)
    text = re.sub(r"(?s)\$\$.*?\$\$", " ", text)
    text = re.sub(r"\$[^$\n]+\$", "X", text)             # 인라인 수식은 한 단어로
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", "", text)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.M)      # 표
    text = re.sub(r"^Table:.*$", "", text, flags=re.M)
    text = re.sub(r"^#+ .*$", "", text, flags=re.M)       # 제목
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"@(fig|tbl):[A-Za-z0-9_-]+", "Fig", text)
    return text


def paragraphs(text: str) -> list[str]:
    paras = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(ln.strip() for ln in block.splitlines()).strip()
        block = re.sub(r"^(\d+\.|-|i+\\?\))\s*", "", block)
        if len(block) > 15:
            paras.append(block)
    return paras


def sentences(para: str) -> list[str]:
    parts = re.split(r"(?<=[다요음임함])\.(?=\s|$)", para)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def ending(s: str) -> str:
    s = re.sub(r"[\s\)\]]+$", "", s)
    return s[-2:] if len(s) >= 2 else s


def opener(s: str) -> str:
    w = s.split()
    return w[0] if w else ""


def check(md: str) -> list[str]:
    text = strip_md(md)
    paras = paragraphs(text)
    warns = []
    all_sents = []
    open_count = Counter()

    for pi, p in enumerate(paras, 1):
        ss = sentences(p)
        all_sents += ss
        # 1. 어미 연속
        run = 1
        for a, b in zip(ss, ss[1:]):
            run = run + 1 if ending(a) == ending(b) else 1
            if run == 3:
                warns.append(f"[어미 반복] 문단 {pi}: '~{ending(b)}.'가 3문장 연속 → \"{b[:30]}…\"")
        # 2. 문단 안 같은 시작
        c = Counter(opener(s) for s in ss)
        for w, n in c.items():
            if n >= 2 and len(w) > 1:
                warns.append(f"[시작 반복] 문단 {pi}: '{w}'로 시작하는 문장 {n}개")
        open_count.update(opener(s) for s in ss)
        # 5. 추측 표현
        h = sum(p.count(x) for x in HEDGES)
        if h >= 2:
            warns.append(f"[추측 반복] 문단 {pi}: 추측 표현 {h}번 → 한 번만")
        # 7. 짧은 문장 연속
        short = 0
        for s in ss:
            short = short + 1 if len(s) <= 15 else 0
            if short == 3:
                warns.append(f"[짧은 문장] 문단 {pi}: 15자 이하 문장 3개 연속")
        # 8. 고른 리듬
        if len(ss) >= 4:
            lens = [len(s) for s in ss]
            if statistics.pstdev(lens) < 0.18 * statistics.mean(lens):
                warns.append(f"[리듬] 문단 {pi}: 문장 길이가 너무 고름 (평균 {statistics.mean(lens):.0f}자) → 짧은 문장·긴 문장 섞기")

    for w, n in open_count.items():
        if n >= 4 and len(w) > 1:
            warns.append(f"[시작 반복] 문서 전체: '{w}'로 시작하는 문장 {n}개")
    # 3. 접속어
    for cword in CONNECTIVES:
        n = sum(1 for s in all_sents if s.startswith(cword))
        if n > 2:
            warns.append(f"[접속어] '{cword}'로 시작하는 문장 {n}개 → 2개 이하")
    # 4. 금지 표현
    for b in BANNED:
        if b in text:
            warns.append(f"[쓰지 않는 표현] '{b.strip()}'")
    # 6. 반복 구절
    words = [w for w in re.findall(r"[가-힣A-Za-z0-9.–\-]+", text) if w not in ("-", "X")]
    grams = Counter(" ".join(words[i:i + 3]) for i in range(len(words) - 2))
    for g, n in grams.most_common(15):
        if n >= 3 and not re.fullmatch(r"[\dX.\s–\-ns]+", g):
            warns.append(f"[구절 반복] '{g}' {n}번")
    # 9. 굵은 글씨
    nb = sum(ln.count("**") // 2 for ln in md.splitlines() if not ln.lstrip().startswith("#"))
    if nb:
        warns.append(f"[굵게] 본문·목록에 굵은 글씨 {nb}곳 → 굵게는 제목과 절 제목에만 (목록 이름표도 보통 굵기)")
    # 10. 기타 절 분량
    for m in re.finditer(r"(?m)^#+ ([^\n]*(?:기타|9\.3\.)[^\n]*)\n(.*?)(?=^#|\Z)", md, flags=re.S):
        body = strip_md(m.group(2))
        n = sum(len(sentences(pp)) for pp in paragraphs(body))
        if n > 3:
            warns.append(f"[분량] '{m.group(1).strip()}' {n}문장 → 기타 절은 두세 문장")
    # 11–12. 어휘 반복
    warns += lexical_warnings(md, paras)
    # 문서 전체 어미 분포
    ends = Counter(ending(s) for s in all_sents)
    if all_sents:
        top, cnt = ends.most_common(1)[0]
        if cnt / len(all_sents) > 0.45 and len(all_sents) >= 10:
            warns.append(f"[어미 분포] '~{top}.'가 전체 문장의 {cnt / len(all_sents):.0%} → 다른 어미로 바꾸기")
    return warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md", type=Path)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    warns = check(a.md.read_text(encoding="utf-8"))
    if not warns:
        print("✓ 문체 검사 통과")
        return 0
    print(f"문체 검사: {len(warns)}건")
    for w in warns:
        print("  ⚠", w)
    return 1 if a.strict else 0


if __name__ == "__main__":
    sys.exit(main())
