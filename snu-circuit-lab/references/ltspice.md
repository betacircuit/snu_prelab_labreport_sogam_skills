# LTspice — 검증, computer-use, 깨끗한 그림

회로이론 prelab·보고서의 시뮬레이션 그림은 실제 LTspice 출력으로 만든다. `$E`는 공통 엔진의 `scripts/` 폴더다. 측정 사진과 시뮬레이션 그림을 구분한다.

## 작업 흐름
1. 현재 과제의 문항·입력·부품·실소자 모델·분석 조건을 먼저 확인한다. 이미 받은 프로필이나 자료를 다시 요구하지 않는다. 스킬 개선 요청에서는 프로필 초기화와 과제 자료 요청을 하지 않는다.
2. 분석마다 `.cir` 또는 `.asc` 파일을 만든다. 과제 `prelab/sim/` 또는 `report/sim/`에 두고 원문 조건을 기록한다. 이론 모델만으로 실소자 시뮬레이션을 완료했다고 말하지 않는다.
3. `spice.py lint <파일>`과 `spice.py run <파일>`로 수치를 확인한다. LTspice 배치 실행을 우선하고, ngspice는 호환 가능한 보조 검증에만 쓴다. 과도 응답은 `.meas tran`, AC는 `spice.py value <raw> -t "v(out)" --at 1k`로 읽는다. 이론값과 다른 경우 모델·설정·측정 위치 차이를 설명하거나 수정한다.
4. **[computer-use 화면 절차](ltspice-computer-use.md)를 읽고 LTspice GUI를 직접 조작한다.** 회로 연결·노드·Run 결과·신호 이름·축 범위를 확인하고 앱 자체 이미지 출력으로 저장한다. MCP가 없다는 이유만으로 새 세션이나 MCP 설치부터 요구하지 않는다. 제공된 Windows computer-use 스킬도 확인하기 전에는 GUI 작업이 불가능하다고 판단하지 않는다.
5. `.asc`·`.cir`·모델·`.raw`·`.log`와 최종 그림을 함께 보관한다. 보고서용 PNG를 열어 포인터·후광·메뉴·잘린 축이 없고, 채널이 색 또는 선 모양으로 구분되는지 확인한다. 파형과 측정 수치를 `spice.py`로 읽은 값에 대조한다.
6. 검토한 그림만 `prelab/figs/` 또는 `report/figs/`에 넣고 캡션에 `LTspice 시뮬레이션`이라고 쓴다. 측정값과 비교한 별도 raw 데이터 그래프라면 실제 생성 방식과 시뮬레이터를 밝힌다.

## 호스트와 도구 선택
- **Codex**: 설치된 computer-use 스킬과 현재 API를 따른다. Windows에서는 `node_repl` + `@oai/sky`로 앱을 조작한다. [Codex 실행 흐름](../../snu-report-core/references/runtime-codex.md)을 따른다.
- **Claude**: 해당 환경의 computer-use를 사용한다. Codex 패키지나 경로를 가정하지 않는다.
- **LTspice MCP**: 사용 가능하면 파일 생성·모델 확인·배치 실행의 보조 수단으로 쓴다. 사용자가 MCP 방식을 명시하면 그 선택을 따른다. GUI와 연결 도구가 모두 없을 때만 필요한 회로/파형 캡처를 묶어 요청하고, 작성 가능한 초안은 진행한다.
- **설치**: LTspice 자체가 없을 때 현재 호스트·권한 범위에서 설치한다. MCP 추가가 필요한 요청에만 `bootstrap.py --agent codex|claude --yes`를 사용한다. 다른 AI의 설정은 변경하지 않는다.

## 공통 문법 (LTspice와 ngspice 모두에서 돌아가는 넷리스트)
`spice.py lint`가 아래를 검사한다.

| 규칙 | 안 지키면 |
|---|---|
| 1행은 `* 제목` | 1행은 제목으로 무시되어 그 줄의 소자가 사라진다 |
| 넷리스트는 영어(ASCII)로, 주석도 영어 | LTspice 버전에 따라 글자가 깨진다 |
| 메가는 `Meg`, `M`은 밀리 | `1M` 저항은 1 mΩ이 된다 |
| `.tran 1u 10m`처럼 Tstep > 0 | LTspice는 `.tran 0 10m`을 받지만 ngspice는 에러 |
| `.meas tran 이름 …`처럼 분석 종류를 쓴다. AC는 `.meas` 대신 `spice.py value` | ngspice 에러. AC `.meas`는 ngspice가 실수부를, LTspice가 복소수를 돌려준다 |
| 다이오드·트랜지스터·op-amp 모델은 파일 안에 `.model`·`.subckt`로 | LTspice 기본 라이브러리(1N4148, 2N3904, UniversalOpamp2 …)는 ngspice에 없다 |
| 이상적 op-amp는 VCVS: `E1 out 0 <+입력> <−입력> 1e6` | 실제 op-amp 특성이 필요하면 datasheet의 SPICE 모델을 `.subckt`로 넣는다 |
| `.step`은 LTspice에 줄 파일에만. ngspice 검증은 값마다 파일을 나눈다 | ngspice는 `.step`을 모른다 |
| 분석은 파일마다 하나 (`.tran` 파일, `.ac` 파일) | raw에 첫 분석만 남고 나머지는 말없이 빠진다 |
| 접지 노드는 `0`, 마지막 줄은 `.end` | 기준 노드 없음 에러 |
| 값은 붙여 쓴다: `4.7k`, `100n`, `1Meg` | 공백이 있으면 다음 필드로 읽힌다 |

예 (RC 저역 통과, τ = 1 ms):
```
* RC low-pass step response, R=1k C=1u
V1 in 0 PULSE(0 5 0 1u 1u 5m 10m)
R1 in out 1k
C1 out 0 1u
.tran 1u 10m
.meas tran v1ms find v(out) at=1m
.end
```
