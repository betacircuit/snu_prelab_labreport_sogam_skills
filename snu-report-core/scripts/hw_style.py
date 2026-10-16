"""Scoped HW prose/comment review. Does not detect authorship or rewrite code."""
from __future__ import annotations
import argparse
from pathlib import Path
import re

PROTECTED = re.compile(r"```.*?```|~~~.*?~~~|(?<!\\)\$\$.*?(?<!\\)\$\$|(?<!\\)\$[^$\n]+(?<!\\)\$|`[^`\n]*`|<!--.*?-->|(?<=\]\()[^)]+(?=\))|https?://[^\s)]+|\{[^}]*\}", re.S)
CONTEXT = re.compile(r"original(?:\s+[a-z]+){0,7}\s+colou?rs?|as (?:you )?requested|according to (?:the |your )?prompt|provided screenshot", re.I)


def prose_issues(markdown):
    visible = PROTECTED.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), markdown)
    issues = []
    for n, line in enumerate(visible.splitlines(), 1):
        if any(c in line for c in '−–—‑'):
            issues.append(f'[본문 표기] {n}행: 수식 밖의 마이너스·대시는 ASCII 하이픈(-)으로 쓴다')
        if CONTEXT.search(line):
            issues.append(f'[작업 맥락] {n}행: 코드나 결과와 무관한 작업 지시 표현을 지운다')
    return issues


def comments(code):
    """Locate percent comments without treating quoted format strings as comments."""
    block = False
    for n, line in enumerate(code.splitlines(), 1):
        if line.strip() == '%{':
            block = True
            continue
        if line.strip() == '%}':
            block = False
            continue
        if block:
            yield n, line.strip()
            continue
        quote = None
        i = 0
        while i < len(line):
            c = line[i]
            if quote:
                if c == quote:
                    if i + 1 < len(line) and line[i+1] == quote:
                        i += 2
                        continue
                    quote = None
            elif c == '%':
                yield n, line[i:].lstrip('%').strip()
                break
            elif c == '"':
                quote = c
            elif c == "'":
                # Adjacent identifiers, numbers and closing brackets use transpose.
                prev = line[i-1] if i else ''
                if not prev or not (prev.isalnum() or prev in '_)]}.'):
                    quote = c
            i += 1


def comment_issues(code):
    issues = []
    for n, comment in comments(code):
        if CONTEXT.search(comment):
            issues.append(f'[주석 맥락] {n}행: {comment}')
        if re.search('[가-힣]', comment):
            issues.append(f'[영어 주석] {n}행: 과제 공지에 맞춰 영어 주석을 쓴다')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', type=Path)
    parser.add_argument('--code', type=Path)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    issues = prose_issues(args.markdown.read_text(encoding='utf-8'))
    if args.code:
        issues += comment_issues(args.code.read_text(encoding='utf-8'))
    for issue in issues:
        print(issue)
    if not issues:
        print('HW prose and comment checks passed; review meaning against the assignment and actual results.')
    return int(bool(issues) and args.strict)


if __name__ == '__main__':
    raise SystemExit(main())
