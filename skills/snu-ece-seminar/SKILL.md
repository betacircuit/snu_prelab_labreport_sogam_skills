---
name: snu-ece-seminar
description: 서울대 전기정보공학부 전정세(세미나) 주차별 강연 소감문을 Word(.docx)로 작성한다. 강연 슬라이드·메모·녹취 요약에서 내용을 뽑고, 교수 DB로 연사의 연구 배경을 확인한다. "전정세", "세미나 소감", "소감문", "강연 소감" 요청에 사용.
---

# 전정세 강연 소감문

- **공통 엔진부터 읽는다: 이 폴더 옆의 `../snu-report-core/SKILL.md`** (저장소에서는 `skills/snu-report-core/SKILL.md`). 절차·서식·문체·도구는 그대로 따르고, 명령의 `$E`는 그 엔진의 `scripts/` 절대 경로로 바꿔 실행한다. 소감문만의 규칙은 이 폴더의 `references/sogam.md`.
- 작업 폴더의 `courses/seminar/weekNN/`에 쌓이고, 자료(강연 슬라이드, 내 메모, 녹취 요약, 사진)는 `inbox/seminar/`에 넣는다. 과목명·분량·파일명 기본값은 이 폴더의 `course.yaml`.
- 교수 DB: 이 폴더의 `data/professors.yaml` (전기정보공학부 전임교수 전체, 학부 홈페이지 공개 정보)

## 반드시 지킬 것
1. **강연 내용은 사용자가 준 자료에 있는 것만 쓴다.** 슬라이드, 메모, 녹취, 사진이 근거다. 교수 DB와 웹 정보는 연사 소개와 배경에만 쓰고, 강연에서 한 말처럼 쓰지 않는다.
2. **느낀 점은 사용자의 것이다.** 메모에 느낀 점이 없으면 초안 전에 한 번만 묻는다: "제일 기억에 남은 것 하나, 궁금했던 것 하나". 답이 없으면 강연 내용과 사용자 관심사(`profile.yaml`의 `track`, 듣는 수업)를 이은 초안을 쓰고, 전달할 때 "느낀 점은 초안이니 네 생각으로 바꿔 줘"라고 한 줄 알린다.
3. **분량은 과목 설정의 `length`.** 기본 A4 1쪽.
4. **결과는 `.docx`, 파일명은 과목 설정의 `filename.sogam` 규칙.**

## 작업 순서
0. 준비 확인: `python $E/setup_profile.py --check --course seminar`. 설치·작업 폴더는 알아서 준비하고, 빠진 것(이름, 학번)만 묻는다 (엔진 `references/setup.md`).
1. (작업 폴더가 git 저장소면 `git pull`) `inbox/seminar/`의 파일을 `courses/seminar/weekNN/materials/`로 옮긴다. 파일명에 주차가 없으면 사용자가 말한 주차를 쓴다.
2. `weekNN/meta.yaml`을 채운다 (`templates/meta.yaml` 참고): `week`, `lab_date`(강연일), `title`(강연 제목), `speaker`(이름·소속), `speaker_id`(교수 DB id, 외부 연사면 비움).
3. 연사 확인: 이 폴더의 `data/professors.yaml`에서 이름으로 찾는다. 외부 연사면 슬라이드의 소개만 쓴다.
4. 강연 정리: 자료에서 핵심 주장, 예시, 수치를 뽑아 `weekNN/notes.md`에 근거(슬라이드 쪽수, 메모 줄)와 함께 적는다. PDF는 `pdftotext`, 이미지는 직접 보고 읽는다.
5. 원고 `weekNN/sogam.md`를 `references/sogam.md` 구성대로 쓴다 (`templates/sogam.md` 뼈대).
6. `python $E/style_check.py courses/seminar/weekNN/sogam.md`로 반복을 고친다.
7. `python $E/build.py courses/seminar/weekNN sogam --pdf` → 미리보기 확인 → docx 전달.

## 마무리 확인
- [ ] 강연 내용 문장마다 notes.md에 근거가 있다
- [ ] 연사 소개가 교수 DB 또는 슬라이드와 맞는다
- [ ] 상투 표현이 없다 (`references/sogam.md` 목록, style_check)
- [ ] 분량이 `length`에 맞는다
