# 자주 하는 실수 — 기초전자기학 및 연습 (MATLAB 과제)

공통 실수는 엔진 `snu-report-core/references/mistakes.md`. 쓰기 전에 둘 다 읽는다.

## 제출
| 실수 | 막는 법 |
|---|---|
| 사용자가 준 MATLAB 캡처를 무시하고 그림을 다시 그림, 흑백으로 바꿈, 코드를 다시 쳐 넣음 | 사용자 사진이 1순위, 컬러 그대로. 코드 캡처가 있으면 코드는 사진으로 (SKILL.md) |
| 사용자 코드·주석을 마음대로 고침 | `HW1.m`은 원본 그대로. 고칠 것이 있으면 안을 보여 주고 동의를 받는다 |
| 문장 속에 `sin(πt)/(πt)` 같은 긴 식, 한 줄에 식 네 개 | 문장을 끝내고 `$$`로 한 줄에 식 하나. 빌드의 `[수식]` 경고 0건 |
| zip·PDF 이름 순서를 다른 과목처럼 학번_이름으로 | 이 과목은 **HW번호_이름_학번** (course.yaml `filename.hw`). 도구: build.py가 검사 |
| m-file 첫 줄에 `clc; clear;`가 없음, 파일 이름이 `hw1.m`·`HW1_final.m` | 도구: `mcode.py check` |
| 한글 주석 | 주석과 출력 문자열은 영어. 도구: `mcode.py check` (비ASCII 문자) |
| 코드와 보고서의 코드가 다름 | 보고서 코드는 `{{code: Problem N}}`으로 m-file에서 바로 가져온다 (SKILL.md) |
| 문제의 제약을 어김 (내장 함수 금지, subplot 금지, 그래프 개수) | `requirements.md`에 제약을 적고 `mcode.py check --forbid "1:sinc,subplot"`. 개수 조건은 보고서 그림에서 센다 |
| $t = 0$ 같은 특이점을 따로 처리하지 않음 (sinc의 0/0) | 조건식으로 정의대로 값(sinc(0) = 1)을 넣고, 그렇게 했다고 동작 원리에 쓴다 |
| 제출한 코드가 처음부터 돌리면 에러 | `clear` 뒤 처음부터 `mcode.py run`으로 돌려 본다. 다른 파일·작업 공간 변수에 기대지 않는다 |

## 물리량과 단위
| 실수 | 막는 법 |
|---|---|
| 상수 값·지수 오타 | $\varepsilon_0 = 8.854 \times 10^{-12}$ F/m, $\mu_0 \approx 4\pi \times 10^{-7}$ H/m, $k = 1/(4\pi\varepsilon_0) \approx 8.988 \times 10^{9}$ N·m²/C². 코드 맨 위에 이름 붙여 한 번만 정의 |
| cm·mm를 m로 안 바꿈, nC·μC 접두사 누락 | 입력값을 SI로 바꾼 줄에 단위 주석 (`% 5 cm -> m`) |
| 결과에 단위가 없음, 자릿수가 들쭉날쭉 | `fprintf('E = %.3e V/m\n', E)`처럼 단위를 붙여 출력, 보고서 표도 같게 |
| 원천 위치에서 필드를 계산해 Inf·NaN | 원천점을 격자에서 빼거나 거리 하한을 둔다. 그렇게 했다고 보고서에 쓴다 |

## MATLAB 문법
| 실수 | 막는 법 |
|---|---|
| 원소별 연산에 `*`, `/`, `^` | 격자 계산은 `.*`, `./`, `.^` |
| `i`, `j`를 반복 변수로 써서 허수 단위가 바뀜 | 반복 변수는 `k`, `n`, `ii`, 허수는 `1i` |
| `sin(30)`에 도를 넣음 | 라디안 `sin(pi/6)` 또는 `sind(30)` |
| `atan(y/x)`로 각도 (사분면 틀림) | `atan2(y, x)` |
| `cart2sph`의 각도를 물리의 $\theta$로 씀 | MATLAB `cart2sph`는 **고도각(elevation)**, 물리 구면좌표 $\theta$는 z축에서 잰 **극각** → $\theta = \pi/2 - \text{elev}$ |
| `meshgrid`의 행·열 순서 혼동 | `[X, Y] = meshgrid(x, y)`면 `X`는 열마다 x가 바뀐다. `surf(X, Y, Z)`와 크기를 맞춘다 |
| `gradient`, `divergence`, `curl`에 격자 간격을 안 줌 | `gradient(V, dx, dy)` — 빼면 간격 1로 계산돼 단위가 틀린다. 전기장은 $\mathbf{E} = -\nabla V$ (부호) |
| 적분 격자가 거칠어 값이 수렴하지 않음 | 격자를 두 배로 줄여 값이 바뀌는지 본다. 가능하면 해석해와 비교 |
| `quiver` 자동 크기 조정으로 크기 비교가 안 됨 | 방향만 보일 때는 정규화했다고 쓰고, 크기는 `contour`·색으로 따로 |

## 그림
| 실수 | 막는 법 |
|---|---|
| 축 이름·단위, 제목, 범례 없음 | `xlabel('x [m]')`, `ylabel`, `title`, `legend`, `colorbar` 단위 |
| 축 비율이 달라 원·등전위선이 찌그러짐 | `axis equal` |
| 크기 차이가 큰 값을 선형 축에 | `semilogy`, `loglog` |
| 그림 번호와 보고서 번호가 다름 | `figure(1)`처럼 번호를 정하면 `mcode.py run`이 `figs/fig1.png`로 저장한다 |
