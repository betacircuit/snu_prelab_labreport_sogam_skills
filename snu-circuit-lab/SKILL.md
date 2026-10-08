---
name: snu-circuit-lab
description: 서울대 전기정보공학부 「회로이론 및 실험」의 prelab(예비보고서)과 lab report(결과보고서)를 Word(.docx)로 작성한다. "회로이론", "회로실험", "회로이론 및 실험"과 prelab·예비보고서·결과보고서·lab report 요청에 사용. 논리설계 및 실험은 snu-logic-lab.
---

# 회로이론 및 실험 — Prelab / Lab Report

공통 엔진 `../snu-report-core/SKILL.md`를 먼저 읽는다. 절차·서식·문체·도구는 엔진 것이고, 아래는 이 과목에서 다른 점이다. 작업은 `courses/circuit/`, 자료는 `inbox/circuit/`.

## 구성
**양식 자유. prelab은 교재의 "모의 실험 보고서", lab report는 "실험 보고서" 문항에 답하는 것이 전부다** (조교 답변, `references/course.md`). 논설실의 목표·요약·토론 틀을 쓰지 않는다. 교재 문항은 `ingest.py`가 쪽 번호와 함께 `requirements.yaml` 초안으로 뽑는다.

## 도구
| 할 일 | 방법 |
|---|---|
| 회로도 | `circuit_kit.Circuit`에 schemdraw 소자(`Resistor`, `Capacitor`, `Inductor`, `SourceV`, `SourceSin`, `Ground`, `Opamp`)를 `add` (figures.md) |
| 이론값 | 노드·메시 해석, 등가 회로, 과도·주파수 응답을 sympy·numpy로 풀고 식은 기호식 → 대입 → 결과로 옮긴다 |
| LTspice | [references/ltspice.md](references/ltspice.md) — 배치 실행으로 수치 확인, computer-use로 화면 확인과 포인터 없는 그림 |
| 파형 그래프 | `spice.py plot` 또는 matplotlib 흑백 |
| 보드 선도 | `python $E/bode.py plot --tf "<전달 함수>" -p R=1k,C=100n --sim out.raw:v(out) --meas data/bode.csv --mark-3db -o figs/bode.png` — 이론(검은 실선)·LTspice(밑의 회색 띠)·측정(빈 원). 표는 `bode.py table --at 100,1k,10k` |
| 페이저도 | `python $E/bode.py phasor "V_s=1∠0" "V_R=0.8∠-37" -o figs/phasor.png` |
| 측정값 | `report/evidence.yaml`, 오차율은 `derived`. 공칭값과 실측값(1 kΩ / 0.987 kΩ)을 구분하고 실측값으로 계산했으면 실험 방법에 밝힌다 |
| 스코프 사진 보정 | [snu-lab-photo](../snu-lab-photo/SKILL.md). 판독 근거는 원본 |
| 표기 | [references/notation.md](references/notation.md) — 페이저, $j$, dB, $V_{pp}$/$V_{rms}$, 위상은 $\tan^{-1}$ + 구간 나눔 (atan2 같은 함수 이름은 빌드가 막는다) |
| 실수 | `references/mistakes.md` (ω/f 혼동, RMS·Vpp, 50 Ω 출력, 프로브 접지, SPICE `M`·`F` 접두사 …) |
