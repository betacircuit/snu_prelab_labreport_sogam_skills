# LTspice — 검증, computer-use, 깨끗한 그림

회로이론 prelab·보고서의 시뮬레이션 그림은 실제 LTspice 출력으로 만든다. `$E`는 공통 엔진의 `scripts/` 폴더다. 측정 사진과 시뮬레이션 그림을 구분한다.

## 작업 흐름
1. 문항의 입력·부품·실소자 모델·분석 조건을 확인한다. 이론 모델만으로 실소자 시뮬레이션을 끝냈다고 하지 않는다.
2. 분석마다 `.cir`/`.asc`를 `prelab/sim/` 또는 `report/sim/`에 만든다.
3. `spice.py lint`와 `spice.py run`으로 수치를 확인한다 (LTspice 배치 우선, ngspice는 보조). 과도 응답은 `.meas tran`, AC는 `spice.py value <raw> -t "v(out)" --at 1k`. 이론값과 다르면 모델·설정·측정 위치를 설명하거나 고친다.
4. [computer-use 화면 절차](ltspice-computer-use.md)대로 LTspice GUI에서 연결·Run·신호·축을 확인하고 앱 자체 출력으로 저장한다. MCP가 없다고 설치나 사용자 캡처 요청부터 하지 않는다. LTspice MCP는 있으면 파일 생성·배치 실행의 보조로 쓴다. GUI·MCP가 모두 없을 때만 필요한 캡처를 묶어 요청하고 초안은 계속 쓴다.
5. `.asc`·`.cir`·`.raw`·`.log`와 그림을 함께 보관한다. 그림은 포인터·메뉴·잘린 축이 없고 채널이 구분되는지 열어 보고, `spice.py` 값과 대조한다.
6. 검토한 그림만 `figs/`에 넣고 캡션에 `LTspice 시뮬레이션`.

LTspice가 없으면 현재 호스트 권한으로 설치한다. MCP 등록은 요청받았을 때만 `bootstrap.py --agent <codex|claude> --yes`.

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
