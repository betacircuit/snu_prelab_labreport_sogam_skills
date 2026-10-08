# Prelab 절차

## 1. 문항 확정
- `courses/<과목>/labNN/requirements.md`의 가이드북 Prelab 절과 슬라이드 지시(예: "Experiment guide book 4.a ~ 4.f")로 문항 목록을 정한다.
- 원고와 `requirements.yaml` 문항 대응표에는 가이드북 원문 번호를 그대로 쓴다 (7.2.1, 4.a, 4.f)a …).
- 그림이 딸린 문항(예: "Figure 2의 회로")은 가이드북 해당 페이지를 이미지로 보고 회로를 옮긴다 (`pdftoppm -f N -l N -png`).

## 2. 문항 유형별 도구
| 문항 | 도구 | 원고에 넣을 것 |
|---|---|---|
| 진리표 | `logic.py truth --vars … --eq … --json prelab/expected.json` | 표, minterm |
| 식 간소화 | `logic.py minimize …` | 적용한 법칙과 과정, 최소 SOP/POS |
| 드모르간 변환 | 손 전개 + `logic.py truth`로 원식과 같은지 확인 | 전개 과정, 확인 표 |
| K-map | `make_figs.py`에서 `logic.kmap_png(vars, values, out, groups=[{"cells": […], "label": …}])` (흑백, 묶음 표시) | 그림, 묶은 칸 설명 |
| 회로도 | `circuit_kit.Circuit` → `save()` 그림 검사 → `verify()` 회로 검증 (figures.md) | 흑백 회로도 |
| NAND/NOR만 쓰기 | `logic.py netlist` → `pinmap.py --nand-only` | 변환 과정, 게이트 수 |
| 브레드보드 배선 | `pinmap.py prelab/netlist.yaml` | 칩 목록, 핀 할당 |
| critical path | 입력별 경로와 단 수를 표로 | 경로, 단 수, 예상 지연 |
| 예상 파형 | `timing.py prelab/timing.yaml` | 타이밍도 |

"as simple as possible" 문항은 게이트 수와 단 수를 표로 비교한다.

## 3. 원고 `prelab/prelab.md`
- 맨 앞에 이번 prelab이 답하는 문항 범위를 한두 문장. 그다음 문항마다 절 하나 (`# 4.a) …` — 번호 처리는 format.md "절 번호"). 풀이 → 결과 → 확인.
- **"실험 준비" 절은 만들지 않는다.** Lab00의 prelab 필수 항목은 Prelab 문항뿐이다. critical path 표·핀 배선표·브레드보드 배치는 그 문항이 있을 때만 해당 절 안에 쓰고, 문항이 없는데 쓸모 있으면 채팅으로 따로 준다.
- "as simple as possible"처럼 답이 여럿이면 조원과 같은 회로를 만들어야 하니 한 번 묻는다. 이번 실험의 비교 의도(예: 5.f와 5.g의 단 수 차이)가 드러나는 답을 기본으로, 더 줄인 대안은 한 문장만.
- 가이드북 그림에서 회로를 읽어 식을 세우면 다른 에이전트에게 따로 읽혀 같은지 본다.
- 이론 배경은 풀이에 필요한 만큼만.

빌드·검사·전달은 엔진 SKILL.md 작업 순서 4–5와 proofreading.md.
