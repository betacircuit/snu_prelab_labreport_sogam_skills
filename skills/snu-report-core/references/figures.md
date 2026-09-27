# 그림 그리기

모든 그림은 `courses/<과목>/labNN/{prelab,report}/figs/make_figs.py` 하나에서 만든다 (다시 돌리면 같은 그림).
흑백만 쓴다. 그림 글자는 본문과 맞춰 고딕: `circuit_kit.TEXT_FAMILY` (맑은 고딕 → Noto Sans CJK KR → DejaVu Sans), 수식 기호는 `dejavusans`.

## 회로도 — `scripts/circuit_kit.py`
가이드라인은 손 그림이나 온라인 도구(circuitlab 등)를 허용한다. 이 skill은 schemdraw + `circuit_kit`으로 그린다:
벡터 품질, 흑백, 수정·재현이 쉽다. 사용자가 circuitlab 파일을 따로 주면 그걸 쓴다.

규칙 (사용자 지정)
- 게이트 이름(N1, N2 …)은 게이트 몸체의 **정중앙** — `Circuit.gate(..., name=)`이 계산해서 찍는다
- 노드 이름($Y_1$ …)은 그 노드의 **점 바로 옆** — `Circuit.node(pt, name, where="ne")`
- 점은 분기점(T자)과 이름 붙인 노드에만. 출력 버블에 붙이지 말고 버블에서 0.5 정도 떨어진 선 위에
- 입력 이름은 선 왼쪽 끝, 출력 이름은 오른쪽 끝 (`Circuit.text`)
- 글자는 schemdraw 라벨이 아니라 matplotlib text로 찍는다 (schemdraw 라벨은 세로 정렬이 어긋남)
- 실제로 연결한 것은 다 그린다: 신호 처리부뿐 아니라 출력부(LED, 저항, $V_{CC}$)까지
  ```python
  jy = (n4.out[0] + 0.9, 0); c.add(elm.Line().at(n4.out).to(jy)); c.node(jy, "Y", "se")
  top = (jy[0], 4.2); c.add(elm.Vdd().at(top)); c.text((top[0], top[1] + 0.55), "$V_{CC} = 5$ V", va="bottom")
  r = c.add(elm.Resistor().at(top).down(1.8)); c.text((top[0] - 0.45, top[1] - 0.9), "R = 330 Ω", ha="right")
  led = c.add(elm.LED().at(r.end).down(1.6)); c.text((top[0] - 0.45, r.end[1] - 0.8), "LED", ha="right")
  c.add(elm.Line().at(led.end).to(jy))
  ```
- lab report에는 **prelab 그림을 가져오지 않고 새로 그린다**

예시 — NAND 4개 XOR:
```python
import schemdraw.elements as elm
from circuit_kit import Circuit
c = Circuit()
n1 = c.gate("Nand", (4, 0), "N1")
n2 = c.gate("Nand", (8, 1.6), "N2")
n3 = c.gate("Nand", (8, -1.6), "N3")
n4 = c.gate("Nand", (11.5, 0), "N4")
ya, yb = n2.in1[1], n3.in2[1]
c.add(elm.Line().at((0, ya)).to(n2.in1)); c.text((-0.15, ya), "A", ha="right")
c.add(elm.Line().at((0, yb)).to(n3.in2)); c.text((-0.15, yb), "B", ha="right")
ja, jb = (1.2, ya), (1.8, yb)
c.node(ja); c.node(jb)
c.add(elm.Wire("|-").at(ja).to(n1.in1)); c.add(elm.Wire("|-").at(jb).to(n1.in2))
jn = (n1.out[0] + 0.6, n1.out[1])
c.add(elm.Line().at(n1.out).to(jn)); c.node(jn, "$Y_1$", "ne")
c.add(elm.Wire("|-").at(jn).to(n2.in2)); c.add(elm.Wire("|-").at(jn).to(n3.in1))
c.add(elm.Wire("-|", k=0.6).at(n2.out).to(n4.in1)); c.add(elm.Wire("-|", k=0.6).at(n3.out).to(n4.in2))
c.node((n2.out[0] + 0.55, n2.out[1]), "$Y_2$", "n")
c.node((n3.out[0] + 0.55, n3.out[1]), "$Y_3$", "s")
c.add(elm.Line().at(n4.out).right(1.0)); c.text((n4.out[0] + 1.15, n4.out[1]), "Y", ha="left")
c.save("figs/nand_xor_circuit.png")
```
게이트 종류: `And`, `Or`, `Nand`, `Nor`, `Xor`, `Not` (inputs=2/3). `Not`은 앞뒤 선 없이 몸체만 그려진다.

입력이 넷 이상이면 왼쪽에 세로 입력선(A, B, C, D)을 두고 가로로 분기한다. 교차는 점 없이, 분기(T자)에만 점. 마지막 분기는 꺾임이라 점을 찍지 않는다. 선은 직각으로만 꺾는다 (`Wire("z")`는 대각선이 생기므로 쓰지 않는다). 작업 폴더에 지난 Lab의 `make_figs.py`가 있으면 그 배치를 따른다.

K-map: `logic.kmap_png(..., groups=[{"cells": [6, 7], "label": r"$\overline{A}BC$"}])` — 흑백, 묶음마다 선 모양을 바꾼다.

## 그래프 (matplotlib)
- 계열 순서대로 `circuit_kit.BAR_STYLES[0]`(빈 막대) → `[1]`(검은 막대) → `[2]`(빗금)
- 측정값에는 반복 측정 min–max 오차 막대 (검은색)
- 격자 `#cccccc` 0.5pt, 위·오른쪽 축선 제거, 범례 테두리 없음
- 값은 `evidence.yaml`에서 `evidence.analyze()`로 읽는다 (손으로 옮기지 않기)
- 축 이름에 단위: `지연 시간 [ns]`
