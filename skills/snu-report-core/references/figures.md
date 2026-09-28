# 그림 그리기

모든 그림은 `courses/<과목>/labNN/{prelab,report}/figs/make_figs.py` 하나에서 만든다 (다시 돌리면 같은 그림).
흑백만 쓴다. 그림 글자는 본문과 맞춰 고딕: `circuit_kit.TEXT_FAMILY` (맑은 고딕 → Noto Sans CJK KR → DejaVu Sans), 수식 기호는 `dejavusans`.

## 회로도 — `scripts/circuit_kit.py`
가이드라인은 손 그림이나 온라인 도구(circuitlab 등)를 허용한다. 이 skill은 schemdraw + `circuit_kit`으로 그린다:
벡터 품질, 흑백, 수정·재현이 쉽다. 사용자가 circuitlab 파일을 따로 주면 그걸 쓴다.

규칙 (사용자 지정)
- **선은 겹치거나 붙어 가지 않는다.** 나란한 선은 0.3 이상 띄우고, 선은 게이트·소자 몸체를 지나지 않으며, 게이트에는 핀에서만 닿는다.
  분기는 기존 선 위에 점을 찍고 T자로 뺀다 (다른 게이트 몸체 쪽에서 새 선을 끌어오지 않는다). `c.save()`가 검사해서 어기면 멈춘다
- 게이트 이름(N1, N2 …)은 게이트 몸체의 **정중앙** — `Circuit.gate(..., name=)`이 계산해서 찍는다
- 노드 이름($Y_1$ …)은 그 노드의 **점 바로 옆** — `Circuit.node(pt, name, where="ne")`
- 점은 분기점(T자)과 이름 붙인 노드에만. 출력 버블에 붙이지 말고 버블에서 0.5 정도 떨어진 선 위에
- 입력 이름은 선 왼쪽 끝 `c.pin(pt, "A")`, 출력 이름은 오른쪽 끝 `c.pin(pt, "Y", side="out")` — 회로 검증의 입력·출력이 된다
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
c.add(elm.Line().at((0, ya)).to(n2.in1)); c.pin((0, ya), "A")
c.add(elm.Line().at((0, yb)).to(n3.in2)); c.pin((0, yb), "B")
ja, jb = (1.2, ya), (1.8, yb)
c.node(ja); c.node(jb)
c.add(elm.Wire("|-").at(ja).to(n1.in1)); c.add(elm.Wire("|-").at(jb).to(n1.in2))
jn = (n1.out[0] + 0.6, n1.out[1])
c.add(elm.Line().at(n1.out).to(jn)); c.node(jn, "$Y_1$", "ne")
c.add(elm.Wire("|-").at(jn).to(n2.in2)); c.add(elm.Wire("|-").at(jn).to(n3.in1))
c.add(elm.Wire("-|", k=0.6).at(n2.out).to(n4.in1)); c.add(elm.Wire("-|", k=0.6).at(n3.out).to(n4.in2))
c.node((n2.out[0] + 0.55, n2.out[1]), "$Y_2$", "n")
c.node((n3.out[0] + 0.55, n3.out[1]), "$Y_3$", "s")
c.add(elm.Line().at(n4.out).right(1.0)); c.pin((n4.out[0] + 1.0, n4.out[1]), "Y", side="out")
c.save("figs/nand_xor_circuit.png")                      # 그림 검사 (겹침·관통·점)
c.verify({"Y": "A ^ B"}, kinds={"N1": "NAND", "N2": "NAND", "N3": "NAND", "N4": "NAND"})   # 회로 검증
```
게이트 종류: `AND`, `OR`, `NAND`, `NOR`, `XOR`, `XNOR`, `NOT` (대소문자 무관, inputs=2/3). `NOT`은 앞뒤 선 없이 몸체만 그려진다.
앞에서 `down()` 등으로 방향을 바꿨어도 게이트는 항상 오른쪽을 본다.

### 헷갈리는 게이트 — NOR와 XOR
둘 다 방패 몸체라 가장 자주 바뀐다. 가이드북 그림을 옮길 때, 본문에 게이트 이름을 쓸 때 아래 표로 하나씩 대조한다.

| 게이트 | 모양 | 칩 | (0,0) (0,1) (1,0) (1,1) |
|---|---|---|---|
| NOR | 방패, 입력 쪽 곡선 **한 줄**, 출력 **버블 있음** | 7402 (출력 핀이 먼저) | 1 0 0 0 |
| XOR | 방패, 입력 쪽 곡선 **두 줄**, 버블 **없음** | 7486 | 0 1 1 0 |
| XNOR | 방패, 곡선 두 줄, 버블 있음 | 74266 | 1 0 0 1 |
| OR | 방패, 곡선 한 줄, 버블 없음 | 7432 | 0 1 1 1 |
| NAND | D자, 버블 있음 | 7400 | 1 1 1 0 |
| AND | D자, 버블 없음 | 7408 | 0 0 0 1 |

- 그림 코드의 종류, 본문의 이름, 칩 번호, 진리표 네 가지가 모두 같은 게이트를 가리켜야 한다.
- `c.verify(kinds={"N2": "NOR"})`로 본문에 쓴 종류와 그림을 맞추고, 진리표 비교가 NOR/XOR를 바꿔 그린 것을 잡는다.
- 원고의 `7402(XOR)`처럼 칩 번호와 게이트 이름이 어긋나면 `proof.py`가 잡는다.

### 회로 검증 순서 (모든 회로도에 한다)
1. **식 확정**: 문항의 식을 `logic.py truth`로 진리표로 만든다. 가이드북 그림에서 옮긴 회로는 게이트 종류(위 표)·입력 수·연결을 게이트마다 적고, 다른 에이전트에게 따로 읽혀 같은지 본다 (prelab.md).
2. **그리기**: `make_figs.py`에서 `Circuit`으로 그린다. 입력·출력은 `c.pin`, 중간 노드는 `c.node(pt, "$Y_1$")`.
3. **그림 검사** (`c.save()` 자동): 선 겹침, 나란한 선 간격 < 0.3, 게이트·소자 관통, 핀 아닌 곳에 닿음, 대각선, T자 분기에 점 없음, 교차점에 점, 글자와 선 겹침. 걸리면 `CircuitError`로 멈춘다 (그림은 저장되니 열어서 본다).
   겹침은 선을 옮겨서 푼다: 분기점을 다른 x로, 되돌아가는 선은 게이트 아래·위로 0.5 이상 돌린다, 게이트를 세로로 더 벌린다.
4. **회로 검증** (`c.verify(기대 식, kinds=…)`): 그림의 연결에서 넷리스트를 뽑아 모든 입력 조합의 출력을 기대 식과 비교한다. 게이트 종류가 본문과 다르거나 핀을 잘못 이으면 틀린 행을 보여 주며 멈춘다.
   되먹임이 있는 순차 회로(latch, flip-flop)는 진리표 비교를 건너뛴다고 알려 준다 → `timing.py` 타이밍도와 특성표로 확인한다.
   회로이론 회로(R, C, 전원)는 3번 그림 검사만 하고, 연결은 `spice.py nodes` 연결표와 대조한다.
5. **핀 배선과 대조** (브레드보드 배선을 쓸 때): `c.netlist()`의 게이트 종류·입력 수가 `pinmap.py`에 넣은 넷리스트와 같은지 본다.
6. **눈으로 확인**: PNG를 열어 본다 — 게이트 모양이 위 표와 맞는지, 이름이 몸체 가운데 있는지, 점이 분기에만 있는지, 선끼리 붙어 보이는 곳이 없는지. 미리보기 PDF에서 한 번 더.

입력이 넷 이상이면 왼쪽에 세로 입력선(A, B, C, D)을 두고 가로로 분기한다. 교차는 점 없이, 분기(T자)에만 점. 마지막 분기는 꺾임이라 점을 찍지 않는다. 선은 직각으로만 꺾는다 (`Wire("z")`는 대각선이 생기므로 쓰지 않는다). 작업 폴더에 지난 Lab의 `make_figs.py`가 있으면 그 배치를 따른다.

K-map: `logic.kmap_png(..., groups=[{"cells": [6, 7], "label": r"$\overline{A}BC$"}])` — 흑백, 묶음마다 선 모양을 바꾼다.

## 그래프 (matplotlib)
- 계열 순서대로 `circuit_kit.BAR_STYLES[0]`(빈 막대) → `[1]`(검은 막대) → `[2]`(빗금)
- 측정값에는 반복 측정 min–max 오차 막대 (검은색)
- 격자 `#cccccc` 0.5pt, 위·오른쪽 축선 제거, 범례 테두리 없음
- 값은 `evidence.yaml`에서 `evidence.analyze()`로 읽는다 (손으로 옮기지 않기)
- 축 이름에 단위: `지연 시간 [ns]`
