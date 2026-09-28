# LTspice — 넷리스트, 검증, 캡처

회로이론 prelab·보고서에는 **LTspice 화면 캡처**를 넣는다 (사용자 확인).
캡처는 LTspice에서 나온 화면이어야 한다. ngspice 그래프를 LTspice 캡처라고 넣지 않는다.
`$E`는 엔진 `scripts/` 폴더다.

## 순서
1. **첫 메시지 (한 번에)**
   - `setup_profile.py --check`의 빠진 정보를 묻는다.
   - 가이드북이나 슬라이드가 없으면 달라고 한다.
   - LTspice MCP가 없을 때:
     - 사용자 PC에서 도는 에이전트(Claude Code, Codex. 셸이 Windows나 macOS)면 묻지 말고 `python $E/bootstrap.py --yes`를 직접 실행한다. LTspice, uv, ltspice-mcp를 설치하고 Claude Code·Codex·Claude 앱에 등록한다.
     - 끝나면 "새 세션에서 MCP가 보인다"고 한 줄 알린다. 이번 세션은 `spice.py run`(LTspice 배치 실행)으로 계속한다.
     - 클라우드 세션이면 아래 "설치 안내"를 붙인다.
   - 답을 기다리지 않고 2–3단계를 먼저 한다.
2. **넷리스트**: 분석마다 파일을 하나씩 쓴다 (`labNN/prelab/sim/<이름>_tran.cir`, `<이름>_ac.cir`, 보고서는 `report/sim/`).
   - 아래 "공통 문법"을 지킨다.
   - 입력 진폭과 주파수는 가이드북 값을 쓴다. 가이드북에 없으면 정해서 메시지에 한 줄 밝힌다.
3. **검증**
   - `python $E/spice.py lint <파일>` → `python $E/spice.py run <파일>`로 돌린다. LTspice가 깔려 있으면 LTspice 배치 실행, 없으면 ngspice로 돈다 (`--sim`으로 고를 수 있음).
   - 이론값은 같은 폴더의 `theory.py`(sympy)로 계산해 맞춰 본다.
     - 과도 응답은 `.meas tran`으로 확인한다.
     - AC는 `python $E/spice.py value <raw> -t "v(out)" --at 1k`로 크기(dB)와 위상을 읽는다. `.meas ac`는 LTspice와 ngspice의 결과 형식이 달라 쓰지 않는다.
   - 어긋나면 넷리스트나 계산을 고친다. 둘이 맞아야 다음으로 넘어간다.
4. **LTspice 실행과 캡처.** 되는 방법 중 위에 있는 것을 쓴다.
   - LTspice MCP가 있으면 같은 넷리스트를 LTspice로 돌려 3의 값과 같은지 본다. 회로도까지 캡처해야 하면 MCP의 회로도 편집 도구로 `.asc`를 만든다.
   - 사용자 PC 화면 제어 도구와 연결된 폴더가 있으면, 넷리스트(와 `.asc`)를 그 폴더에 쓰고 LTspice를 열어 직접 캡처한다. MCP가 없어도 된다.
   - 둘 다 없으면 "캡처 부탁"을 두 번째 메시지로 보내고, `.cir` 파일을 같이 보낸다. 채팅 파일 전송을 쓰고, 안 되면 작업 폴더 git으로 보낸다.
5. **그림 넣기**
   - 받은 캡처는 `prelab/figs/`(보고서는 `report/figs/`)에 두고, 캡션에 `LTspice 시뮬레이션`이라고 쓴다.
   - 측정값과 겹쳐 그리는 보고서 그래프는 LTspice raw를 `spice.py plot`으로 그려도 된다. ngspice raw로 그렸으면 캡션에 `ngspice`라고 밝힌다.

캡처 부탁 (파일 이름, 띄울 신호, 기대값을 채워서 보낸다):
```
LTspice에서 lab03_rc_tran.cir를 열고(File → Open, 파일 형식 Netlists) ▶ Run을 눌러 줘.
파형 창에서 V(in), V(out)을 띄우고(오른쪽 클릭 → Add Traces), Win + Shift + S로 창을 캡처해서
inbox/circuit/에 "[Lab 03] ltspice_rc_tran.png"로 올려 줘. t = 1 ms에서 V(out)이 약 3.16 V면 맞아.
```
회로도를 직접 그려야 하면 `python $E/spice.py nodes <파일>`의 소자·노드 연결표를 같이 준다.

## MCP 확인
도구 목록에 `ltspice` 서버의 도구가 있으면 쓴다. 도구 이름은 버전마다 다르니 서버 이름으로 찾는다.
클라우드 세션에서는 사용자 PC의 로컬 MCP가 기기 연결 도구를 거쳐 보인다. 이 경우 그 PC에서 데스크톱 앱이 켜져 있고 대화가 PC에 연결돼 있어야 한다.

## 설치 안내 (클라우드 세션에서 MCP가 없을 때 첫 메시지에 붙인다)
가장 쉬운 방법은 사용자 PC의 Claude Code나 Codex에 README의 "PC에 한 번에 설치" 프롬프트를 붙여 넣는 것이다. 그러면 `bootstrap.py`가 아래를 전부 한다.
직접 설치하려는 사용자에게는 OS와 쓰는 앱에 맞는 것만 보낸다.

**Windows (PowerShell)**
```
winget install AnalogDevices.LTspice
winget install --id=astral-sh.uv -e
```
PowerShell을 새로 연 뒤:
```
uv tool install ltspice-mcp
uv tool dir --bin
```
마지막 줄이 보여 준 폴더 끝에 `\ltspice-mcp.exe`를 붙인 것이 실행 파일 경로다 (예: `C:\Users\<이름>\.local\bin\ltspice-mcp.exe`).

**macOS**: LTspice는 analog.com LTspice 페이지에서 받는다. `brew install uv` → `uv tool install ltspice-mcp` → `uv tool dir --bin`.

**앱에 등록 (쓰는 앱 하나만)**
- Claude 앱(데스크톱, 또는 PC에 연결한 클라우드 대화)
  1. 설정 → 개발자 → 구성 편집으로 `claude_desktop_config.json`을 연다.
  2. 파일이 비어 있거나 `mcpServers`가 없으면 아래 전체를 넣는다. 이미 `mcpServers`가 있으면 그 안에 `"ltspice": {…}` 한 항목만 추가한다.
  3. 경로는 `\` 대신 `/`로 쓴다.
  4. 트레이에서 앱을 완전히 종료하고 다시 연다.
  ```json
  { "mcpServers": { "ltspice": { "command": "C:/Users/<이름>/.local/bin/ltspice-mcp.exe", "args": [] } } }
  ```
- Claude Code (터미널): `claude mcp add --scope user ltspice -- ltspice-mcp`
- Codex: `codex mcp add ltspice -- ltspice-mcp`

**알려 줄 것 (한 줄씩)**
- `ltspice-mcp`는 Analog Devices 공식이 아니라 개인이 만든 오픈소스다 (GPL-3.0, https://github.com/cognitohazard/ltspice-mcp).
- `run_code` 도구는 PC에서 파이썬을 실행한다. 쓸 때마다 허락하고 "항상 허용"은 누르지 않는다.
- 설치가 끝나면 알려 달라고 한다. 도구가 보이면 4단계를 MCP로 다시 한다.

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
