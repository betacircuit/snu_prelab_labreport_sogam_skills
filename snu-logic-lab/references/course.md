# 수업 공통 규칙 (Lab00 자료 기준, 2026-2학기)

출처: `courses/logic/materials/` — Lab00 Introduction, Prelab & Lab report Guideline, Experimental Tools (2026-09-08).
이 파일이 모든 Lab에 공통으로 적용된다. 각 Lab 슬라이드의 지시가 이 파일과 다르면 **슬라이드가 우선**이고, 차이를 `courses/<과목>/labNN/requirements.md`에 적는다.

## 제출
- 파일명 (틀리면 감점): `prelab01_학번_이름.pdf`, `lab01_학번_이름.pdf` (예: `prelab01_2025-12345_홍길동.pdf`) — 소문자, 두 자리 번호
  (이 skill은 같은 이름의 .docx를 주고, 사용자가 Word에서 PDF로 바꿔 제출한다)
- 제출처: eTL 과제 게시판, **PDF**
- 마감: 일요일 23:59
  - Prelab NN: 실험(화요일) **전** 일요일
  - Lab report NN: 실험 **후** 일요일
  - 슬라이드 날짜가 이 규칙과 어긋나면 규칙 날짜를 따르고 사용자에게 한 줄로 알린다 (예: Lab02 슬라이드 "September 4" → 10/4)
- 지각: 하루 -10%, 7일 지나면 0점. 실험 지각(다음 주 화요일)은 -50%

## 형식
- 형식 자유 ("any format, as long as it is easy to read"), 길게 쓸 필요 없음
- 한국어/영어 모두 가능
- 회로도는 손 그림 가능하나 선명해야 함, 온라인 도구(circuitlab 등) 허용

## Prelab 필수
- 가이드북을 꼼꼼히 읽을 것
- 가이드북 **Prelab 파트의 모든 문항**에 답할 것 (슬라이드가 범위를 지정하면 그 범위)

## Lab report 필수
1. 실험 목표 (Goal of each lab)
2. 수행한 내용 요약 (Summarize what you've done)
3. 토론 및 고찰 (Discussion and Matters to Consider) — **슬라이드가 지정한 문항 번호를 전부** 답한다
   - 예: Lab01 → 9.2.2~9.2.4, 9.3.1 (9.1은 제외), Lab02 → 6.b~6.c (6.a 제외)
4. 측정 결과 (슬라이드가 요구하면, 보통 delay time)

## 실험 환경 (Lab00 Experimental Tools, Lab01 슬라이드)
- 브레드보드: 빨간 줄 5 V, 파란 줄 GND. 파워서플라이 (-) 단자 두 개 GND, -5 V 사용 안 함
- 전류 제한(CC) 다이얼을 작게 → 단락 시 보드 보호
- 오실로스코프: 프로브 10x, DC coupling, 프로브 보정 후 5 V 구형파 확인. Tektronix TDS3000B 계열 (가이드북 참고문헌)
- 지연 측정: CH1 입력, CH2 출력. 스코프 measure(Delay) 또는 커서 사용
- 칩: 7400(NAND), 7402(NOR), 7404(NOT), 7408(AND), 7411(3-AND), 7432(OR), 7486(XOR). 불량 칩이 있으니 회로가 맞는데 안 되면 칩 교체
- 칩 계열(74LS/74HC 등)은 실제 칩 표면 인쇄를 확인해야 함 → 모르면 datasheet 값을 확정적으로 쓰지 않는다

## 일정 (슬라이드 기준, 변동 가능)
| Lab | 실험일 | 주제 |
|:-:|:-:|:--|
| 01 | 9/22 | Understanding Logic Gates |
| 02 | 9/29 | Boolean Algebra & Simplification |
| 03 | 10/6? | K-map & Multi-level, Multi-output logic |
| 04 | | Steering Logic |
| 05 | | Latch/Flip-Flop |
| 06 | | Memory 조합논리 & 7-segment |
| 07 | | Counter & Register |
| 08 | | FSM & Verilog |
| 09 | | FPGA 신호등 컨트롤러 (프로젝트) |
Introduction 원본 일정은 Lab01=9/15였으나 실제 1주 밀림. 날짜는 각 Lab 슬라이드로 확정한다.

## 확인 안 된 것
- 조 번호 `[확인 필요]`
- 분량 제한: 없음 ("You don't need to write a lengthy report")
- AI 사용 규정: 공지 없음 `[확인 필요]`

## 채점 피드백 누적
(채점 결과를 받으면 여기에 추가 → 다음 보고서부터 반영)
