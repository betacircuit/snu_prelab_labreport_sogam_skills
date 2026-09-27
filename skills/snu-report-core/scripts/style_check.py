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
