# SNU 전기정보공학부 과제 스킬

서울대 전기정보공학부 과제를 Word(.docx)로 써 주는 AI 스킬.

- 논설실(논리설계 및 실험) prelab·결과보고서
- 회로이론 및 실험 prelab·결과보고서
- 전정세 강연 소감문 (전기정보공학부 교수 DB 포함)

처음 쓸 때 이름, 학번, 조만 입력할 것. 그다음부터는 "논설실/회이실/전정세 Lab03 prelab/*/소감문 써줘"라고 프롬포트.

## 설치

**Claude Code**
```
/plugin marketplace add betacircuit/snu_prelab_labreport_sogam_skills
/plugin install snu-reports@snu-ece-skills
```

**Codex, Cursor 의 타 에이전트**
```
npx skills add betacircuit/snu_prelab_labreport_sogam_skills -g -s "*"
```

**설치 없이 (저장소를 열 수 있는 AI면 아무거나)** — 새 대화에 붙여 넣고 마지막 줄에 요청을 적을 것.
```
https://github.com/betacircuit/snu_prelab_labreport_sogam_skills 저장소의 스킬로 과제를 해 줘.
저장소를 clone하고 AGENTS.md를 읽은 다음, 요청에 맞는 skills/<과목>/SKILL.md와 skills/snu-report-core/SKILL.md를 그대로 따라.
측정값, 관찰 결과, 강연 내용은 지어내지 말고, 저장소를 못 열면 추측하지 말고 그렇다고 말해.
요청:
```

## 쓰는 법

과제용 폴더를 하나 정해서 거기서 요청해요. 자료는 채팅에 첨부하거나 그 폴더의 `inbox/<과목>/`에 넣으면 된다.

- `논설실 Lab03 prelab 써줘` + 가이드북, 슬라이드
- `회로이론 Lab02 결과보고서 써줘` + 측정 엑셀, 스코프 사진
- `전정세 4주차 소감 써줘` + 강연 메모나 슬라이드(세미나 소감문 요약 작성, 클로바 노트, 강의 화면 사진 등 포함)

첫 요청 때 AI가 필요한 프로그램(pandoc, 파이썬 패키지)을 설치 후, 그 폴더에 작업 공간을 만든다.

```
과제 폴더/
├── profile.yaml     이름, 학번 (처음 한 번 물어보고 저장)
├── inbox/<과목>/     자료 넣는 곳 (logic, circuit, seminar)
├── courses/<과목>/   Lab별 원고, 그림, 근거 자료
└── out/<과목>/       완성된 .docx
```

## 알아 둘 것

- 측정값, 관찰 결과, 강연 내용은 지어내지 않는다. 자료 raw data를 포함할 것.
- 결과물은 수정할 수 있는 `.docx`이다. PDF 변환과 eTL 제출은 개인이 직접 해야한다.
