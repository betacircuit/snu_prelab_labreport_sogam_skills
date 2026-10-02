---
name: snu-circuit-lab
description: 서울대 전기정보공학부 「회로이론 및 실험」의 prelab(예비보고서)과 lab report(결과보고서)를 Word(.docx)로 작성한다. "회로이론", "회로실험", "회로이론 및 실험"과 prelab·예비보고서·결과보고서·lab report 요청에 사용. 논리설계 및 실험은 snu-logic-lab.
---

# 회로이론 및 실험 — Prelab / Lab Report

- **공통 엔진부터 읽는다: 이 폴더 옆의 `../snu-report-core/SKILL.md`** (저장소에서는 `snu-report-core/SKILL.md`). 절차·서식·문체·도구는 그대로 따르고, 명령의 `$E`는 그 엔진의 `scripts/` 절대 경로로 바꿔 실행한다.
- **서식(글꼴, 표·그림 틀, 번호)은 논설실과 같고, 구성은 교재 문항 답변만** (course.md). 작업 폴더의 `courses/circuit/`에 쌓이고, 자료는 `inbox/circuit/`에 넣는다. 과목명·파일명 규칙 기본값은 이 폴더의 `course.yaml`.

공통 엔진의 **실행 호스트 분기**를 먼저 적용한다. Codex는 runtime-codex.md, Claude는 runtime-claude.md만 읽는다.
Codex에서도 Claude 원본의 기능과 양식을 유지하되 사용자 수정 지시를 우선한다. 절 번호는 `1.` → `1.1)` → `1.1.1)`을 제목마다 한 번만 쓴다 (`2.3) 120 nF`, 중복된 `3)` 금지). 원문 번호는 원고·문항 대응표에 보존하고 원문에 없는 `가)·나)·다)` 소제목은 만들지 않는다. 독립 수식은 가운데, 사진·캡션 뒤에는 실제 빈 문단(Enter) 하나를 둔다. 생성 후 이 항목을 실제 DOCX에서 확인한다.

## 처음 쓸 때
1. `python $E/setup_profile.py --check --course circuit` — 설치·작업 폴더는 알아서 준비하고, 빠진 정보(이름, 학번, 조)만 한 번에 묻는다 (엔진 `references/setup.md`).
2. `references/course.md`를 읽는다. **양식은 자유이고, prelab은 교재의 "모의 실험 보고서" 문항, lab report는 교재의 "실험 보고서" 문항에 답하는 것이 전부다** (조교 답변). 논설실의 실험 목표·요약·토론 틀을 쓰지 않는다.
   Lab00·가이드라인 자료가 들어오면 course.md의 `[확인 필요]` 항목(마감, 파일명, 제출처)을 채운다. 그 전까지 파일명은 `prelab{NN}_학번_이름` / `lab{NN}_학번_이름`.
3. 시뮬레이션이 있는 Lab이면 [references/ltspice.md](references/ltspice.md)를 읽는다. LTspice 화면 작업에는 **computer-use를 우선 사용**한다. 수치 검증은 배치 실행으로 병행하며 MCP 부재만으로 설치나 사용자 캡처 요청부터 하지 않는다. 포인터·클릭 후광이 없는 실제 회로도/파형 이미지까지 확인한다.
4. 반사·기울기·흐림이 있는 오실로스코프 사진은 [사진 보정 스킬](../snu-lab-photo/SKILL.md)을 읽는다. 원본과 보정본을 함께 보관하고 수치·파형의 판독 근거는 원본에 둔다.

## 회로이론 실험에서 쓸 도구
| 할 일 | 방법 |
|---|---|
| 회로도 | `circuit_kit.Circuit`에 schemdraw 소자(`Resistor`, `Capacitor`, `Inductor`, `SourceV`, `SourceSin`, `Ground`, `Opamp`)를 `add`로 그린다. 흑백, 노드 이름은 점 옆 (figures.md) |
| 이론값 | 노드·메시 해석, 테브난·노턴 등가, RC·RL·RLC 과도 응답, 주파수 응답은 sympy·numpy 스크립트로 풀고 결과만 수식으로 옮긴다 (기호식 → 대입 → 결과) |
| LTspice 시뮬레이션 | `references/ltspice.md`: 넷리스트·모델 검증 → LTspice 배치 수치 확인 → computer-use로 회로·Run·파형·축 확인 → 포인터 없는 이미지 저장. MCP는 보조 도구 |
| 파형·주파수 그래프 | matplotlib 흑백 (figures.md). 보드 선도는 로그 축 |
| 측정값 | 멀티미터, 오실로스코프, 함수 발생기 값은 `report/evidence.yaml`에 기록하고, 이론값과의 차이·오차율은 `derived`로 계산한다 |
| 자주 하는 실수 | 이 폴더의 `references/mistakes.md` + 엔진의 공통 `references/mistakes.md` — 쓰기 전에 확인 (ω/f 혼동, RMS·Vpp, 50 Ω 출력, 프로브 접지, SPICE `M`·`F` 접두사 …) |
| 부품값 | 공칭값과 실측값을 구분한다 (예: 공칭 1 kΩ, 실측 0.987 kΩ). 실측값으로 계산했다면 실험 방법에 밝힌다 |
