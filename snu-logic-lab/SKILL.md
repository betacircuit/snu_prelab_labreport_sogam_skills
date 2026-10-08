---
name: snu-logic-lab
description: 서울대 전기정보공학부 「논리설계 및 실험」(논설실)의 prelab(예비보고서)과 lab report(결과보고서)를 Word(.docx)로 작성한다. "논설실", "논리설계", "논리설계 및 실험"과 prelab·예비보고서·결과보고서·lab report 요청에 사용. 회로이론 및 실험은 snu-circuit-lab.
---

# 논리설계 및 실험 — Prelab / Lab Report

공통 엔진 `../snu-report-core/SKILL.md`를 먼저 읽는다. 절차·서식·문체·도구는 엔진 것이고, 아래는 이 과목에서 다른 점이다. 작업은 `courses/logic/`, 자료는 `inbox/logic/`.

## 이 과목만의 것
| 항목 | 내용 |
|---|---|
| 실수 | `references/mistakes.md` (NOR/XOR, 7402 핀, 전원 핀, K-map 순서, 지연 기준점 …) |
| 수업 규칙 (Lab00) | `references/course.md` — 마감, 파일명, lab report 필수 항목(목표·요약·토론) |
| 부품 | 74xx TTL (7400, 7402, 7404, 7408, 7411, 7432, 7486). 핀 배치 엔진의 `references/ic-pinouts.yaml`, 배선표 `pinmap.py` |
| 측정 | 오실로스코프 전파 지연 (입력·출력 50% 교차), 전이 방향은 출력 기준 $t_{PLH}$ / $t_{PHL}$ |
| 도구 | `logic.py`(진리표, 간소화, K-map), `pinmap.py`, `circuit_kit.py`, `timing.py`, `scope.py` |
| MUX·decoder·latch·flip-flop | `c.block("MUX4" / "DEC3" / "DFF" …)`, 순차 회로는 `c.verify_seq`·`state_table`·`timing` (figures.md "블록과 순차 회로") |
| 지난 작업 | 작업 폴더의 `courses/logic/lab*/` 중 이미 낸 보고서 — 있으면 구성과 문체의 기준 |
| 사용자 본인 문체 | `profile.yaml`의 `style_samples` |
