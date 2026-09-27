# Lab report 절차

## 1. 요구사항 확인
슬라이드의 "Lab Report" 장과 가이드북에서 다음을 뽑아 `courses/<과목>/labNN/requirements.md` 대응표에 적는다.
- 반드시 답할 Discussion 문항과 제외 문항 (예: Lab01 "9.2.2~9.2.4, 9.3.1", "You don't have to discuss about 9.1")
  - "Answers for 9.2 must be included"처럼 상위 번호로 지시하면 하위 문항(9.2.1 포함) 전부 답한다.
- 반드시 넣을 결과 (예: "Experimental results (delay time) should be included")
- 이번 실험 범위 (예: "We will only go through 8.2")
- Lab00 공통 필수: 실험 목표, 수행 내용 요약, 토론 및 고찰

## 2. 입력은 두 가지뿐
- lab report 자료: 이번 Lab 가이드북(Lab, Discussion 절과 부록 datasheet), 슬라이드의 lab report 지시
- 실험 결과: 측정 시트, 스코프 사진·CSV, 관찰 기록, 사용자가 대화로 알려 준 실험 사실

prelab 파일·그림, 다른 사람 보고서, 단톡 원문은 쓰지 않는다.

## 3. 데이터 정리
```
python $E/evidence.py dump courses/<과목>/labNN/report/raw/data.xlsx
# → courses/<과목>/labNN/report/evidence.yaml 작성 (evidence.md)
python $E/evidence.py courses/<과목>/labNN
```
보고서의 모든 수치는 evidence.yaml에서 나온다.

## 4. 그림
`courses/<과목>/labNN/report/figs/make_figs.py` 하나에서 회로도와 그래프를 만든다 (figures.md).

## 5. 원고 `report/report.md`
1. 실험 목표 — 한두 문장. 이번 실험 범위를 밝힌다.
2. 실험 내용 요약
   - 회로 구성: 회로도 + 게이트 출력 식
   - 실험 방법: 번호 목록 + 이름표 (`1. 회로 연결: …`, 굵게 하지 않음). 장비 설정, 연결, 판독 기준, 반복 횟수, 전이 방향 표기
   - 전이 방향은 모든 표에서 출력 기준으로 적는다 (출력 0→1 = $t_{PLH}$, 1→0 = $t_{PHL}$). 시트 표기가 애매하면 계산값의 대소 관계와 맞는 해석을 고르고 실험 방법에 밝힌다
3. 실험 결과 — 가이드북 8.x 항목별 절. 관측값과 계산값만 쓰고 해석은 하지 않는다. 자료가 없는 항목은 절을 만들지 않는다.
4. 토론 및 고찰 — 지정 문항마다 절 하나 (`## 9.2.2 …`).
   - 현상(수치, 수식) → 원인 → 근거 → 확인 방법
   - 측정값과 계산값·datasheet 값이 다르면 오차 분석을 `- 원인: 설명` 목록으로 쓴다
   - 논리 해석(경로 단 수, hazard)은 `- $B = 0$일 때: …` 경우 나누기 목록과 수식으로 보인다
   - 기타(9.3.x)는 슬라이드가 요구하면 두세 문장으로만 쓴다. 요구하지 않으면 절을 만들지 않는다
5. 결론 — 핵심 수치 두세 개와 해석 한 줄.
6. 참고문헌 — 가이드북 외 외부 자료를 인용했을 때만.

문체와 서식은 writing.md, format.md를 따른다. 다 쓰면 `python $E/style_check.py report/report.md`로 반복을 고친다.

## 6. 빌드와 확인
```
python $E/build.py courses/<과목>/labNN report --pdf
```
- `build/preview/`의 PDF를 전 페이지 이미지로 확인한다 (표·그림·캡션, 수식, 쪽 넘김).
- 사용자에게는 `build/labNN_학번_이름.docx`를 보낸다.

## 7. 조원 보고서와 대조 (사용자가 줄 때)
조원 보고서는 원고의 입력이 아니라 검토 자료다. 본문에 인용하거나 문장을 가져오지 않는다.
- 같은 측정값을 같은 표기(전이 방향, B 조건)로 정리했는지
- 계산값: 어떤 평균을 썼는지, 경로 모델이 전이 방향과 맞게 배치됐는지
- 해석: "비슷하다"처럼 데이터와 다른 판단, 크기가 맞지 않는 오차 원인
상충하는 점은 사용자에게 목록으로 알리고, 우리 쪽이 틀린 것만 고친다.
