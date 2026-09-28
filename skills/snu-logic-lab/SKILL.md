---
name: snu-logic-lab
description: 서울대 전기정보공학부 「논리설계 및 실험」(논설실)의 prelab(예비보고서)과 lab report(결과보고서)를 Word(.docx)로 작성한다. "논설실", "논리설계", "논리설계 및 실험"과 prelab·예비보고서·결과보고서·lab report 요청에 사용. 회로이론 및 실험은 snu-circuit-lab.
---

# 논리설계 및 실험 — Prelab / Lab Report

- **공통 엔진부터 읽는다: 이 폴더 옆의 `../snu-report-core/SKILL.md`** (저장소에서는 `skills/snu-report-core/SKILL.md`). 절차·서식·문체·도구는 그대로 따르고, 명령의 `$E`는 그 엔진의 `scripts/` 절대 경로로 바꿔 실행한다.
- 맨 처음: `python $E/setup_profile.py --check --course logic` — 설치·작업 폴더는 알아서 준비하고, 빠진 정보(이름, 학번, 조)만 한 번에 묻는다.
- 작업 폴더(`profile.yaml`이 있는 곳)의 `courses/logic/`에 쌓이고, 자료는 `inbox/logic/`에 넣는다. 과목명·파일명 규칙 기본값은 이 폴더의 `course.yaml`.

## 이 과목만의 것
| 항목 | 내용 |
|---|---|
| 자주 하는 실수 | 엔진 `references/mistakes.md`의 공통·논리설계 절 — 쓰기 전에 이번 Lab 주제 항목을 확인 (NOR/XOR, 7402 핀, 전원 핀, K-map 순서, 지연 기준점 …) |
| 공통 규칙 (Lab00) | `references/course.md` — 마감(prelab은 실험 전 일요일, report는 실험 후 일요일 23:59), 파일명, 필수 항목 |
| 부품 | 74xx TTL (7400, 7402, 7404, 7408, 7411, 7432, 7486). 핀 배치 엔진의 `references/ic-pinouts.yaml`, 배선표 `pinmap.py` |
| 측정 | 오실로스코프 전파 지연 (입력·출력 50% 교차), 전이 방향은 출력 기준 $t_{PLH}$ / $t_{PHL}$ |
| 도구 | `logic.py` (진리표, 간소화, K-map), `pinmap.py`, `circuit_kit.py` (게이트 회로도), `timing.py`, `scope.py` |
| 지난 작업 | 작업 폴더의 `courses/logic/lab*/` 중 이미 낸 보고서 — 있으면 구성과 문체의 기준 |
| 사용자 본인 문체 | `profile.yaml`의 `style_samples` |
