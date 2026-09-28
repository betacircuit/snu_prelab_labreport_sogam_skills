---
name: snu-em-hw
description: 서울대 전기정보공학부 「기초전자기학 및 연습」(기전연) 실습 자료의 MATLAB 과제(Homework)를 풀어 m-file(HW1.m)과 결과 보고서를 만들고, 제출용 zip(HW1_이름_학번.zip = 보고서 PDF + HW1.m)까지 묶는다. "기전연", "기초전자기학", "전자기학 실습", "실습1 과제", "HW1 MATLAB" 요청에 사용. 실험 보고서(prelab·lab report)가 아니다.
---

# 기초전자기학 및 연습(기전연) — MATLAB 과제 (HW)

실험 보고서가 아니라 **과제**다. prelab·lab report 절차(evidence.yaml, 실험 방법, 토론)는 쓰지 않는다.
내는 것은 `HW1.m`(MATLAB 코드)과 결과 보고서 PDF를 묶은 zip 하나다. 규칙은 `references/course.md`.

- **공통 엔진을 읽는다: `../snu-report-core/SKILL.md`** (저장소에서는 `skills/snu-report-core/SKILL.md`). 서식·문체·오탈자 검사·빌드는 엔진 것을 쓰고, `$E`는 엔진 `scripts/` 절대 경로다.
- 작업 폴더의 `courses/em/hwNN/`에 쌓이고, 실습 자료 PDF·skeleton 코드는 `inbox/em/`에 넣는다. **실습 N 자료의 Homework = HW N** (파일명·내용의 `실습1`, `HW1`, `과제 1`로 분류).
- 과제는 실습 자료 PDF 끝의 **Homework** 절(문제 1., 2., 3.)과 **eTL 제출** 쪽, 마감은 앞쪽 "제출 기한"에 있다.
- 쓰기 전에 `references/mistakes.md`(MATLAB·전자기 실수)와 엔진의 공통 `references/mistakes.md`를 읽는다.

## 폴더
```
courses/em/hw01/
├── meta.yaml          hw: 1, title: 과제 주제
├── requirements.md    문제 목록과 대응표
├── materials/         과제 PDF (+ .txt)
├── code/HW1.m         제출 코드 (run.log = 실행 출력)
├── figs/              fig1.png … (mcode.py run이 figure 번호대로 저장)
├── hw.md              보고서 원고
└── build/             HW1_이름_학번.docx / .pdf / .zip
```

## 작업 순서
0. `python $E/setup_profile.py --check --course em` — 빠진 것(이름, 학번)만 묻는다. 조는 묻지 않는다.
1. `python $E/ingest.py` → `courses/em/hw01/`. Homework의 문제·제약·제출 기한이 `requirements.md`와 `meta.yaml`에 초안으로 들어간다.
   - PDF 원문과 대조해 문제를 빠짐없이 옮기고, **문제마다 제약**(예: "내장 sinc 사용 금지", "subplot 사용하지 않고", "5개 이상의 그래프", "30x30 행렬")을 한 줄씩 적는다. `meta.yaml`의 `title`을 채운다.
   - skeleton 파일(예: 3번 "% skeleton file 참고")이 있으면 그 구조와 변수 이름을 살려서 쓴다. 없으면 사용자에게 한 번 달라고 하고, 기다리는 동안 다른 문제를 푼다.
2. **코드 `code/HW1.m`**
   - 첫 줄 `clc; clear;`. 상수·입력값은 맨 위에 SI 단위로 한 번 정의한다.
   - 문제마다 `%% Problem 1` 절. 절마다 무엇을 계산하는지 **영어 주석** (식, 단위, 격자·적분 방법).
   - 그림은 `figure(1)`처럼 번호를 정하고, 축 이름·단위·제목을 단다.
   - 한글을 쓰지 않는다 (주석, `fprintf`, 그림 글자 모두 영어).
3. **검사와 실행**
   - `python $E/mcode.py check courses/em/hw01/code/HW1.m --problems 1 2 3 --forbid "1:sinc,subplot"` — 이름, 첫 줄, 영어 주석, 문제 절, **과제가 금지한 함수**.
   - `python $E/mcode.py run courses/em/hw01/code/HW1.m` — MATLAB(없으면 Octave)로 처음부터 돌려 `figs/figN.png`와 `code/run.log`를 만든다.
     둘 다 없으면 사용자에게 코드를 보내 실행을 부탁하고, 그림과 명령 창 출력을 받는다. Octave로만 돌렸으면 전달할 때 한 줄 알린다.
   - 수치는 `run.log`에서 옮긴다. 해석해가 있는 문제는 해석해와 비교해 맞는지 본다.
4. **보고서 `hw.md`** (`templates/hw.md` 뼈대)
   - 문제마다 절 하나: `# Problem 1) …`. 풀이 방법(쓰는 식) → 코드 → 코드 동작 원리 → 결과(수치·그림·해석).
   - 코드는 직접 붙이지 않고 `{{code: Problem 1}}` 한 줄로 둔다. 빌드할 때 `HW1.m`의 그 절이 그대로 들어가서 보고서 코드와 제출 코드가 같다.
   - "동작 원리"는 과제 요구 항목이다. 코드를 줄마다 읽어 주지 말고, 계산 순서와 이유(왜 이 격자·이 적분·이 근사)를 쓴다.
   - 학번·이름은 제목 블록에 자동으로 들어간다.
5. `python $E/build.py courses/em/hw01 hw --pdf`
   - 문체·오탈자·코드 검사를 같이 돌린다.
   - PDF 변환이 되면 `build/`와 `out/em/`에 `HW1_이름_학번.pdf`와 제출용 `HW1_이름_학번.zip`(PDF + `HW1.m`)이 생긴다.
   - 변환이 안 되면 docx와 `HW1.m`을 보내고, 사용자가 Word에서 PDF로 저장한 뒤 `python $E/mcode.py pack courses/em/hw01 --pdf <PDF>`로 zip을 만든다.
6. 엔진 `references/proofreading.md` 순서로 오탈자를 확인하고 전달한다: zip(있으면), docx, HW1.m.

## 마무리 확인
- [ ] `mcode.py check --forbid …` 통과: `HW1.m`, 첫 줄 `clc; clear;`, 문제마다 영어 주석, 한글 없음, 금지 함수 없음
- [ ] 문제마다 요구한 것을 다 했다 (예: 그래프 5개 이상, 간격이 좁을 때와 넓을 때의 장단점 서술, 3x1 subplot)
- [ ] `clear` 뒤 처음부터 실행해 에러가 없다 (`run.log`)
- [ ] 모든 문제에 풀이·코드·동작 원리·결과가 있다 (`requirements.md` 대응표)
- [ ] 보고서 수치가 `run.log`와 같고 단위가 있다. 그림에 축 이름·단위가 있다
- [ ] 파일 이름: `HW1_이름_학번.zip` 안에 `HW1_이름_학번.pdf`와 `HW1.m`
