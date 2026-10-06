# 자주 하는 실수 — 논리설계 및 실험

공통 실수는 엔진 `snu-report-core/references/mistakes.md`. 쓰기 전에 둘 다 읽고 이번 Lab 주제에 걸리는 항목을 확인한다.
문항이 그 실수를 묻거나 결과로 드러났을 때만 보고서에 쓴다.

## 게이트와 칩
| 실수 | 막는 법 |
|---|---|
| **NOR ↔ XOR** 기호 혼동. 둘 다 방패 몸체라 헷갈린다 | NOR = 곡선 한 줄 + 출력 버블 (7402). XOR = 입력 쪽 곡선 두 줄, 버블 없음 (7486). 도구: `Circuit.verify(kinds=…)`, proof.py `[칩·게이트]` |
| NAND ↔ AND, XNOR ↔ NOR 혼동 | 버블 유무로 가린다. 진리표 (0,0) 행: NOR·NAND·XNOR = 1, OR·AND·XOR = 0 |
| 7402 핀 배치를 7400과 같다고 생각 | 7402는 **출력 핀이 먼저** (1번 출력, 2·3번 입력). `pinmap.py`가 `ic-pinouts.yaml`로 배치 |
| 칩 번호와 게이트 종류 혼동 (7486을 NOR로) | 7400 NAND, 7402 NOR, 7404 NOT, 7408 AND, 7410 3-NAND, 7411 3-AND, 7432 OR, 7486 XOR. 도구: proof.py |
| 전원 핀 빠뜨림 | 14핀 칩은 14번 $V_{CC}$, 7번 GND. 16핀 칩(74138, 74151, 7447 등)은 16번, 8번. 핀 배선표에 전원 행을 넣는다 |
| 칩을 거꾸로 꽂음 | 홈(notch)·점이 1번 핀 쪽. 배선도에 1번 핀 위치를 표시 |
| 쓰지 않는 입력을 비워 둠 | TTL은 떠 있으면 HIGH처럼 동작하지만 잡음에 약하다. CMOS(74HC)는 반드시 $V_{CC}$나 GND에 묶는다. AND·NAND 남는 입력은 HIGH, OR·NOR는 LOW |
| 74LS와 74HC 섞어 씀 | 74LS 출력 $V_{OH}$ 최소 2.7 V는 74HC 입력 $V_{IH}$(3.5 V)에 못 미칠 수 있다. 칩 표면 인쇄로 계열을 확인하고, 모르면 datasheet 값을 확정적으로 쓰지 않는다 |

## 브레드보드와 출력부
| 실수 | 막는 법 |
|---|---|
| 전원 레일이 보드 가운데에서 끊긴 것을 모름 | 레일 양쪽을 점퍼로 잇는다. 동작이 안 되면 먼저 레일 전압을 잰다 |
| LED 전류 제한 저항 빠뜨림, LED 극성 반대 | 긴 다리가 anode. 저항값은 $I_{LED} = \frac{V_{CC} - V_F - V_{OL}}{R}$로 계산 (writing.md 예) |
| LED가 켜질 때 출력을 반대로 해석 | LED를 $V_{CC}$ 쪽에 달면(TTL은 sink 전류가 커서 흔한 방식) **출력 0일 때 켜진다**. 회로도의 LED 방향과 해석을 맞춘다 |
| 스위치 입력에 pull-up·pull-down 저항이 없음 | 스위치를 열면 입력이 떠 있다. pull-up 저항 + 스위치를 GND로 (열림 = 1, 닫힘 = 0) |
| 스위치 채터링으로 counter·flip-flop이 여러 번 넘어감 | clock은 함수 발생기나 debounce 회로(SR latch)로. 결과에 이상한 건너뜀이 있으면 원인 후보로 쓴다 |
| 7-segment 공통 anode/cathode와 decoder 짝이 틀림 | 7447 = active-low 출력, 공통 anode용. 7448 = 공통 cathode용 |
| 전원 decoupling 커패시터 생략 | 칩 전원 핀 가까이 0.1 µF. glitch가 많으면 원인 후보 |

## 측정 (오실로스코프·함수 발생기)
| 실수 | 막는 법 |
|---|---|
| 프로브 스위치(10x)와 스코프 채널 설정(1x)이 다름 | 진폭이 10배 틀린다. 프로브 보정 후 5 V 구형파로 확인 (course.md) |
| AC coupling으로 디지털 신호를 봄 | DC coupling. 기준선이 움직이면 AC로 된 것 |
| 지연 기준점 혼동 | 전파 지연은 입력 50% → 출력 50%. 10–90%는 상승·하강 시간이다 |
| $t_{PLH}$, $t_{PHL}$을 입력 기준으로 적음 | **출력** 기준: 출력 L→H = $t_{PLH}$. 반전 게이트는 입력 상승 ↔ 출력 하강 (labreport.md) |
| 시간축이 너무 넓어 ns 지연을 못 읽음 | 수 ns 지연은 5–10 ns/div. 판독 분해능을 실험 방법에 적는다 |
| 함수 발생기 출력 설정 (50 Ω vs High-Z) | 50 Ω로 두고 고임피던스에 물리면 실제 진폭이 표시의 2배. TTL 입력은 0–5 V (offset 2.5 V, 5 Vpp), 음전압 금지 |
| 긴 접지선으로 ringing | 접지 클립을 짧게, 가까운 GND에 |

## 설계와 이론
| 실수 | 막는 법 |
|---|---|
| 드모르간·bubble pushing 부호 실수 | 변환 후 `logic.py truth`로 원식과 대조. NAND-NAND = SOP, NOR-NOR = POS |
| NAND-only 변환 뒤 이중 반전을 안 지워 게이트 수가 많음 | `pinmap.py --nand-only` 결과와 게이트 수를 비교 |
| K-map 칸 순서를 이진수로 (00 01 10 11) | Gray code 순서 00 01 11 10. `logic.kmap_png`만 쓴다 |
| K-map 가장자리 wrap-around 누락, 묶음이 2의 거듭제곱이 아님 | `logic.py minimize` 결과와 묶음이 같은지 확인 |
| don't care를 전부 1로 취급 | 묶음을 키울 때만 쓴다. 최소식의 출력에서 don't care 칸 값을 따로 적는다 |
| minterm 번호와 변수 순서 불일치 | `--vars` 순서 = 번호의 비트 순서 (첫 변수 MSB) |
| hazard 원인을 "게이트가 느려서"로만 씀 | 경로마다 단 수가 달라 같은 입력 변화가 다른 시각에 도착한다. static-1 hazard는 consensus 항을 더해 없앤다 (`- $B = 1$일 때: …` 경우 나누기) |
| MUX select 순서 (S1이 MSB), enable이 active-low인 것을 모름 | 74151 strobe $\overline{G}$ = 0이어야 동작, 출력 Y와 W = $\overline{Y}$. 74153도 enable active-low |
| 74138 enable 미연결로 출력이 전부 1 | G1 = 1, $\overline{G2A}$ = $\overline{G2B}$ = 0. 출력은 active-low |
| latch와 flip-flop 혼동 | latch는 레벨, flip-flop은 에지. 타이밍도에서 출력이 바뀌는 시점을 맞춘다. 도구: `c.verify_seq` → `c.timing` (그린 회로에서 파형을 계산) |
| 타이밍도에서 Q가 clock 에지가 아닌 곳에서 바뀜, 에지 직후 값을 받음 | flip-flop은 에지 **바로 앞**의 D를 받는다. 손으로 그린 예상 파형은 `c.timing` 결과와 겹쳐 본다 |
| 상태표·타이밍도의 비트 순서(Q1Q0 / Q0Q1)가 표마다 다름 | 한 순서로 통일하고 표 머리에 적는다. `c.state_table`과 대조 |
| JK의 J = K = 1(반전)·T flip-flop을 빼먹고 상태표를 씀 | 특성표 4행을 먼저 적고 상태표를 채운다 |
| SR latch 금지 입력 | NOR latch는 S = R = 1, NAND latch는 $\overline{S} = \overline{R} = 0$ |
| 74LS74 PRE·CLR을 비워 둠 | active-low라 1에 묶는다. 74LS74는 상승 에지, 74LS76/74LS112 JK는 하강 에지 |
| 카운터 리셋 핀 처리 | 74LS90·74LS93은 R0(1), R0(2)가 둘 다 1일 때 리셋. 동작시킬 때는 0에 묶는다 |
| ripple counter 출력의 순간 glitch를 오동작으로 해석 | 단마다 지연이 쌓여 순간 중간값이 생긴다. 동기식과 비교해 설명 |
| setup·hold 시간 위반 | 입력은 clock 에지 전 $t_{su}$ 동안 유지. datasheet 값과 함께 쓴다 |
| FSM Moore/Mealy 출력 시점 혼동, 안 쓰는 상태 처리 누락 | 상태도에 출력 위치(상태 안/화살표 위)를 표시. 안 쓰는 상태가 초기 상태로 돌아오는지 적는다 |
| Verilog: 순차 블록에 `=`, 조합 블록에 빠진 경우 (latch 생성) | 순차 `always @(posedge clk)`는 `<=`, 조합 `always @(*)`는 `=`와 default·else를 다 쓴다 |
| Verilog: 비트 폭 불일치, reset 극성, 보드 스위치·LED의 active 극성 | 포트 폭을 선언과 맞추고, 보드 문서로 극성을 확인한다. 핀 할당(constraints)을 보고서에 표로 |
