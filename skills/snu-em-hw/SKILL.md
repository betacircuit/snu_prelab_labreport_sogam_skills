---
name: snu-em-hw
description: 서울대 전기정보공학부 「기초전자기학 및 연습」(기전연) 실습 자료의 MATLAB 과제(Homework) 결과 보고서를 만들고, 제출용 zip(HW1_이름_학번.zip = 보고서 PDF + HW1.m)까지 묶는다. 사용자가 준 MATLAB 코드·결과 캡처(컬러)를 그대로 넣는다. "기전연", "기초전자기학", "전자기학 실습", "실습1 과제", "HW1 MATLAB" 요청에 사용. 실험 보고서(prelab·lab report)가 아니다.
---

# 기초전자기학 및 연습(기전연) — MATLAB 과제 (HW)

실험 보고서가 아니라 **과제**다. prelab·lab report 절차(evidence.yaml, 실험 방법, 토론)는 쓰지 않는다.
내는 것은 `HW1.m`(MATLAB 코드)과 결과 보고서 PDF를 묶은 zip 하나다. 규칙은 `references/course.md`.

- **공통 엔진을 읽는다: `../snu-report-core/SKILL.md`** (저장소에서는 `skills/snu-report-core/SKILL.md`). 서식·문체·오탈자 검사·빌드는 엔진 것을 쓰고, `$E`는 엔진 `scripts/` 절대 경로다.
- 작업 폴더의 `courses/em/hwNN/`에 쌓이고, 실습 자료 PDF·skeleton·`HW1.m`·MATLAB 캡처는 `inbox/em/`에 넣는다. **실습 N 자료의 Homework = HW N** (파일명·내용의 `실습1`, `HW1`, `과제 1`로 분류).
- 과제는 실습 자료 PDF 끝의 **Homework** 절(문제 1., 2., 3.)과 **eTL 제출** 쪽, 마감은 앞쪽 "제출 기한"에 있다.
- 쓰기 전에 `references/mistakes.md`(MATLAB·전자기 실수)와 엔진의 공통 `references/mistakes.md`를 읽는다.

## 이 과목에서 엔진 규칙과 다른 것 (사용자 지정)
1. **사용자가 준 사진이 1순위다.** MATLAB 코드 화면 캡처, 결과 그림 캡처를 받았으면 그대로 넣는다. 다시 그리거나 다시 치지 않는다.
2. **컬러 그대로.** 엔진의 "흑백만" 규칙은 이 과목에 쓰지 않는다. 캡처를 흑백으로 바꾸지 않고, 직접 그림을 만들 때도 MATLAB 기본 색을 쓴다 (코드에 회색 지정을 넣지 않는다).
3. **사용자 코드와 주석을 고치지 않는다.** `HW1.m`은 사용자가 쓴 그대로 낸다. `mcode.py check`에 걸리는 것(첫 줄, 영어 주석, 금지 함수)이 있으면 고친 안을 사용자에게 보여 주고, 동의를 받고 고친다.
4. **수식은 짧게, 긴 식은 줄을 바꿔서** (아래 "수식"). 빌드가 단위·함수 이름을 세움꼴로 바꾸고 크기를 맞추지만, 줄 배치는 원고에서 정한다.

## 폴더
```
courses/em/hw01/
├── meta.yaml          hw: 1, title: 과제 주제, due: 제출 기한
├── requirements.md    문제·제약 목록과 대응표
├── materials/         실습 자료 PDF (+ .txt), skeleton
├── code/HW1.m         제출 코드 (사용자 것 그대로, run.log = 실행 출력)
├── figs/              사용자 캡처 (p1_code.png, p1_result.png …) 또는 mcode.py run이 만든 fig1.png …
├── hw.md              보고서 원고
└── build/             HW1_이름_학번.docx / .pdf / .zip
```

## 작업 순서
0. `python $E/setup_profile.py --check --course em` — 빠진 것(이름, 학번)만 묻는다. 조는 묻지 않는다.
1. `python $E/ingest.py` → `courses/em/hw01/`. Homework의 문제·제약·제출 기한이 `requirements.md`와 `meta.yaml`에 초안으로 들어가고, 사진은 `figs/`, `.m`은 `code/`로 간다.
   - PDF 원문과 대조해 문제를 빠짐없이 옮기고, **문제마다 제약**(예: "내장 sinc 사용 금지", "subplot 사용하지 않고", "5개 이상의 그래프", "30x30 행렬")을 한 줄씩 적는다. `meta.yaml`의 `title`을 채운다.
2. **사진 정리**: `figs/`의 사진을 하나씩 열어 보고 문제별로 이름을 바꾼다 — `p1_code.png`(코드 화면), `p1_result.png`(결과 그림), 여러 장이면 `p1_code_2.png`. 무엇인지 모르겠으면 사용자에게 한 번 묻는다.
3. **코드**
   - 사용자가 `HW1.m`을 줬으면 그대로 둔다 (위 3번 규칙). 안 줬는데 코드 캡처만 있으면 캡처에서 옮겨 적은 `HW1.m`을 만들고, 사용자에게 원본 파일을 달라고 한 줄 알린다 (제출은 원본으로).
   - 코드를 내가 써야 하는 경우만: 첫 줄 `clc; clear;`, 문제마다 `%% Problem 1` 절과 **영어 주석**, 그림은 `figure(1)`처럼 번호, 축 이름·단위·제목, 한글 금지. skeleton이 있으면 구조와 변수 이름을 살린다.
4. **검사와 실행**
   - `python $E/mcode.py check courses/em/hw01/code/HW1.m --problems 1 2 3 --forbid "1:sinc,subplot"` — 이름, 첫 줄, 영어 주석, 문제 절, **과제가 금지한 함수**.
   - 결과 캡처가 없을 때만 `python $E/mcode.py run courses/em/hw01/code/HW1.m`으로 `figs/figN.png`와 `code/run.log`를 만든다 (MATLAB, 없으면 Octave). Octave로만 돌렸으면 전달할 때 한 줄 알린다.
   - 수치는 사용자 캡처(명령 창) 또는 `run.log`에서 옮긴다. 지어내지 않는다.
5. **보고서 `hw.md`** (`templates/hw.md` 뼈대). 문제마다 절 하나 `# Problem 1) …`:
   1. 풀이 방법 — 쓰는 식 (아래 "수식")
   2. 코드 — **코드 캡처가 있으면 그 사진**: `![Problem 1 코드](figs/p1_code.png){#fig:p1code width=100%}`. 캡처가 없으면 `{{code: Problem 1}}` (빌드할 때 `HW1.m`의 그 절이 글자로 들어간다)
   3. 코드 동작 원리 — 과제 요구 항목. 줄마다 읽어 주지 말고 계산 순서와 이유(왜 이 격자·이 조건·이 함수)를. 사용자 주석이 설명하는 것과 어긋나지 않게
   4. 결과 — 결과 캡처 `![…](figs/p1_result.png){#fig:p1 width=85%}`와 해석, 문제가 요구한 서술(예: 간격이 좁을 때와 넓을 때의 장단점)
   - 학번·이름은 제목 블록에 자동으로 들어간다.
6. `python $E/build.py courses/em/hw01 hw --pdf`
   - 문체·오탈자·수식 배치·코드 검사를 같이 돌린다. `[수식]` 경고는 전부 고친다.
   - PDF 변환이 되면 `build/`와 `out/em/`에 `HW1_이름_학번.pdf`와 제출용 `HW1_이름_학번.zip`(PDF + `HW1.m`)이 생긴다.
   - 변환이 안 되면 docx와 `HW1.m`을 보내고, 사용자가 Word에서 PDF로 저장한 뒤 `python $E/mcode.py pack courses/em/hw01 --pdf <PDF>`로 zip을 만든다.
7. 미리보기 PDF 전 페이지를 **직접 보고** (PDF 변환이 안 되는 환경이면 사용자에게 Word에서 한 번 봐 달라고 한 줄 알린다) 아래 "보기 전에 확인"을 하나씩 대조한 뒤 전달한다: zip(있으면), docx, HW1.m.

## 수식
문장 속 수식은 기호와 짧은 식만. 분수·괄호 나눗셈·긴 식은 문장을 끝내고 다음 줄에 `$$…$$`로 뺀다. 따로 뺀 줄에는 식 하나(많아야 둘).
```
정규화 sinc 함수는 다음과 같다.

$$\operatorname{sinc}(t) = \frac{\sin(\pi t)}{\pi t} \quad (t \neq 0), \qquad \operatorname{sinc}(0) = 1$$

표본 수가 $N$이면 간격은 다음과 같다.

$$\Delta t = \frac{4\pi}{N - 1}$$
```
- 여러 성분 식(`E_x`, `E_y`, `r`, `k`)은 한 줄에 몰지 않고 두 줄 이상으로 나눈다.
- 단위는 `\ \mathrm{V/m}`처럼 세움꼴 (빠뜨려도 빌드가 숫자 뒤 단위를 세운다). 함수는 `\sin`, `\sinh`, `\operatorname{sinc}`.
- 수치 결과는 수식보다 글로: "전기장 크기는 $8.99 \times 10^{9}\ \mathrm{V/m}$였다" 정도로 짧게.

## 보기 전에 확인
- [ ] 사용자 사진을 전부 썼다 (다시 그린 그림, 흑백으로 바꾼 사진 없음). 코드 캡처가 있으면 코드는 캡처로 들어갔다
- [ ] `HW1.m`이 사용자 원본 그대로다 (고쳤다면 사용자 동의가 있다). `mcode.py check --forbid …` 통과
- [ ] 문제마다 요구한 것을 다 했다 (예: 그래프 5개 이상, 간격이 좁을 때와 넓을 때의 장단점 서술, 3x1 subplot)
- [ ] 문장 속에 분수·긴 식이 없고, 수식 한 줄에 식이 셋 이상 몰려 있지 않다 (`[수식]` 경고 0건)
- [ ] 단위·함수 이름이 기울지 않았고, 수식 글자가 본문보다 커 보이지 않는다 (미리보기로 확인)
- [ ] 보고서 수치가 캡처·`run.log`와 같고 단위가 있다
- [ ] 파일 이름: `HW1_이름_학번.zip` 안에 `HW1_이름_학번.pdf`와 `HW1.m`
