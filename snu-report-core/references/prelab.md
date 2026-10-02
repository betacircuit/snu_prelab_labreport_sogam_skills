# Prelab 절차

## 1. 문항 확정
- `courses/<과목>/labNN/requirements.md`의 가이드북 Prelab 절과 슬라이드 지시(예: "Experiment guide book 4.a ~ 4.f")로 문항 목록을 정한다.
- 가이드북 원문 번호를 그대로 쓴다 (7.2.1, 4.a, 4.f)a …).
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

"as simple as possible" 문항은 게이트 수와 단 수를 표로 비교해 근거를 보인다.

## 3. 원고 `prelab/prelab.md`
1. 범위 — 이번 prelab이 답하는 문항 목록 (한두 문장)
2. 문항별 절 — `# 4.a) …`처럼 가이드북 문항 번호에 `)`를 붙인다 (빠뜨려도 build.py가 붙인다). 절 번호는 Claude 원본과 같은 `1.` → `1.1)` → `1.1.1)`이며 빌드가 붙인다. 원문에 없는 `가)·나)·다)`를 소제목에 만들지 않는다. 설명을 나눌 때는 `## 회로와 전달함수`처럼 제목만 쓴다. 원문에 실제 하위 문항 번호가 있을 때만 그 번호를 함께 보존한다. 풀이 → 결과 → 확인. 진리표는 `logic.py truth`로 원식과 대조

**"실험 준비" 절은 만들지 않는다.** Lab00 규칙의 prelab 필수 항목은 "가이드북 Prelab 파트의 모든 문항"뿐이고, 실험 준비는 요구 항목이 아니다.
- critical path 표, 핀 배선표, 브레드보드 배치는 **가이드북이나 슬라이드가 그 문항을 낼 때만** 해당 문항 절 안에 쓴다.
- 요구하지 않았는데 실험 때 쓸모가 있으면(핀 배선표 등) 보고서에 넣지 않고 채팅으로 짧게 따로 준다.

"as simple as possible"처럼 답이 여럿인 문항은 사용자에게 한 번 묻는다 (조원과 같은 회로를 만들어야 하므로). 이번 실험의 비교 의도(예: 5.f와 5.g의 단 수 차이)가 드러나는 답을 기본으로 하고, 더 줄인 대안은 한 문장으로만 적는다.
가이드북 그림에서 회로를 읽어 식을 세울 때는 다른 에이전트에게 따로 읽혀 식이 같은지 확인한다.

이론 배경은 문항 풀이에 필요한 만큼만 쓴다. 문체와 서식은 writing.md, format.md를 따른다.

## 4. 빌드와 확인
```
python $E/build.py courses/<과목>/labNN prelab --pdf
```
- `python $E/proof.py build/prelabNN_학번_이름.docx --strict`가 통과할 때까지 고치고, proofreading.md의 "눈으로 볼 것"을 확인한다.
- 미리보기 PDF를 전 페이지 이미지로 확인하고, 대응표의 모든 문항에 답했는지 본다.
- 최종 전달은 엔진 SKILL.md의 quality.py render → 전 쪽 확인 → review → deliver 순서를 완료한 사본이다.
