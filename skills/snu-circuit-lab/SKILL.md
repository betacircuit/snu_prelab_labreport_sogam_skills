---
name: snu-circuit-lab
description: 서울대 전기정보공학부 「회로이론 및 실험」의 prelab(예비보고서)과 lab report(결과보고서)를 Word(.docx)로 작성한다. "회로이론", "회로실험", "회로이론 및 실험"과 prelab·예비보고서·결과보고서·lab report 요청에 사용. 논리설계 및 실험은 snu-logic-lab.
---

# 회로이론 및 실험 — Prelab / Lab Report

- **공통 엔진부터 읽는다: 이 폴더 옆의 `../snu-report-core/SKILL.md`** (저장소에서는 `skills/snu-report-core/SKILL.md`). 절차·서식·문체·도구는 그대로 따르고, 명령의 `$E`는 그 엔진의 `scripts/` 절대 경로로 바꿔 실행한다.
- **양식은 논설실과 같다.** 작업 폴더의 `courses/circuit/`에 쌓이고, 자료는 `inbox/circuit/`에 넣는다. 과목명·파일명 규칙 기본값은 이 폴더의 `course.yaml`.

## 처음 쓸 때
1. `python $E/setup_profile.py --check --course circuit` — 설치·작업 폴더는 알아서 준비하고, 빠진 정보(이름, 학번, 조)만 한 번에 묻는다 (엔진 `references/setup.md`).
2. 과목 공통 규칙(Lab00, 보고서 가이드라인) 자료가 들어오면 `references/course.md`를 만든다: 마감, 파일명, 필수 항목, 문항 범위.
   그 전까지는 파일명을 논설실과 같이 `prelab{NN}_학번_이름` / `lab{NN}_학번_이름`으로 쓰고, 마감과 범위는 각 Lab 슬라이드를 따른다.
3. 시뮬레이션이 있는 Lab이면 `references/ltspice.md`를 읽는다. LTspice MCP 도구가 없으면 그 문서의 설치 안내를 사용자에게 보내고, 설치를 기다리는 동안 넷리스트 작성과 ngspice 검증을 먼저 한다.

## 회로이론 실험에서 쓸 도구
| 할 일 | 방법 |
|---|---|
| 회로도 | `circuit_kit.Circuit`에 schemdraw 소자(`Resistor`, `Capacitor`, `Inductor`, `SourceV`, `SourceSin`, `Ground`, `Opamp`)를 `add`로 그린다. 흑백, 노드 이름은 점 옆 (figures.md) |
| 이론값 | 노드·메시 해석, 테브난·노턴 등가, RC·RL·RLC 과도 응답, 주파수 응답은 sympy·numpy 스크립트로 풀고 결과만 수식으로 옮긴다 (기호식 → 대입 → 결과) |
| LTspice 시뮬레이션 | `references/ltspice.md`: 넷리스트 → `spice.py lint`·`run`(ngspice로 검증) → LTspice 실행·캡처(MCP 또는 사용자). 보고서에 넣는 시뮬레이션 그림은 LTspice 캡처 |
| 파형·주파수 그래프 | matplotlib 흑백 (figures.md). 보드 선도는 로그 축 |
| 측정값 | 멀티미터, 오실로스코프, 함수 발생기 값은 `report/evidence.yaml`에 기록하고, 이론값과의 차이·오차율은 `derived`로 계산한다 |
| 자주 하는 실수 | 엔진 `references/mistakes.md`의 공통·회로이론 절 — 쓰기 전에 확인 (ω/f 혼동, RMS·Vpp, 50 Ω 출력, 프로브 접지, SPICE `M`·`F` 접두사 …) |
| 부품값 | 공칭값과 실측값을 구분한다 (예: 공칭 1 kΩ, 실측 0.987 kΩ). 실측값으로 계산했다면 실험 방법에 밝힌다 |
