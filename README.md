# SNU 전기정보공학부 과제 스킬

서울대 전기정보공학부 과제를 Word(.docx)로 써 주는 AI 스킬.

- 논설실(논리설계 및 실험) prelab·결과보고서
- 회로이론 및 실험 prelab·결과보고서
- 전정세 강연 소감문 (전기정보공학부 교수 DB 포함)
- 기초전자기학 및 연습 MATLAB 과제 (HW1.m + 결과 보고서, 제출용 zip)

처음 쓸 때 이름, 학번, 조만 입력할 것. 그다음부터는 "논설실/회이실/전정세 Lab03 prelab/*/소감문 써줘"라고 프롬포트.

## 설치

**PC에 한 번에 설치 (추천)** — Claude Code나 Codex를 열고 아래를 그대로 붙여 넣을 것. 스킬, 파이썬 패키지, pandoc, LTspice, LTspice MCP까지 AI가 알아서 설치하고 등록한다.
```
아래 저장소의 과제 스킬을 이 컴퓨터에 설치하고, 필요한 프로그램도 전부 설치해 줘. 설치 명령은 네가 직접 실행해.
1. git clone --depth 1 https://github.com/betacircuit/snu_prelab_labreport_sogam_skills ~/.snu-skills
   (이미 있으면 git -C ~/.snu-skills pull)
2. python ~/.snu-skills/skills/snu-report-core/scripts/bootstrap.py --yes
   - python이 안 되면 py -3로. 둘 다 없으면 Python부터 설치해 (Windows: winget install -e --id Python.Python.3.12, macOS: brew install python).
   - 관리자 권한 창이 뜨면 나한테 "예"를 누르라고 말해.
   - ✗가 나온 단계는 출력을 보고 원인을 고친 뒤 다시 돌려. 같은 이유로 두 번 실패하면 멈추고 알려 줘.
3. python ~/.snu-skills/skills/snu-report-core/scripts/bootstrap.py --check 결과가 ok인지 확인해.
4. 검증: python ~/.snu-skills/skills/snu-report-core/scripts/spice.py run ~/.snu-skills/skills/snu-circuit-lab/examples/rc_step.cir
   → v1ms가 3.16 V 근처면 성공. LTspice로 돌았는지 ngspice로 돌았는지도 알려 줘.
5. 끝나면 설치된 것, 안 된 것과 이유, 내가 할 일(앱 재시작 등)만 짧게 알려 줘.
```
끝나면 Claude Code·Codex를 새로 시작하고 과제 폴더에서 요청하면 된다.

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
파일 이름에 `Lab 03`이 없어도 된다 (`실험 3`, `Experiment 3`, 내용 속 번호, 실험 날짜로 알아서 분류한다).

- `논설실 Lab03 prelab 써줘` + 가이드북, 슬라이드
- `회로이론 Lab02 결과보고서 써줘` + 측정 엑셀, 스코프 사진
- `전정세 4주차 소감 써줘` + 강연 메모나 슬라이드(세미나 소감문 요약 작성, 클로바 노트, 강의 화면 사진 등 포함)

첫 요청 때 AI가 필요한 프로그램(pandoc, 파이썬 패키지)을 설치 후, 그 폴더에 작업 공간을 만든다.

```
과제 폴더/
├── profile.yaml     이름, 학번 (처음 한 번 물어보고 저장)
├── inbox/<과목>/     자료 넣는 곳 (logic, circuit, seminar, em)
├── courses/<과목>/   Lab별(과제는 HW별) 원고, 그림, 근거 자료
└── out/<과목>/       완성된 .docx
```

## 알아 둘 것

- 측정값, 관찰 결과, 강연 내용은 지어내지 않는다. 자료 raw data를 포함할 것.
- 결과물은 수정할 수 있는 `.docx`이다. PDF 변환과 eTL 제출은 개인이 직접 해야한다.
  기초전자기학 HW는 `.docx`와 `HW1.m`을 주고, PDF 변환이 되는 PC면 `HW1_이름_학번.zip`까지 만든다.

## 저장소 구조 (스킬을 고칠 때)

```
skills/
├── snu-report-core/     공통 엔진: 모든 과목이 쓰는 서식·문체·검사·빌드
│   ├── SKILL.md         작업 순서와 "고칠 곳 지도"
│   ├── references/      규칙 문서 (format, writing, figures, proofreading, mistakes …)
│   ├── scripts/         build.py, proof.py, circuit_kit.py, mcode.py …
│   └── templates/       style.yaml (서식 한 곳), 원고 뼈대, reference.docx
├── snu-logic-lab/       과목마다: SKILL.md + course.yaml + references/(course.md, mistakes.md)
├── snu-circuit-lab/
├── snu-ece-seminar/
└── snu-em-hw/
AGENTS.md                AI가 처음 읽는 안내 (CLAUDE.md는 이 파일을 불러오기만 함)
.claude/skills, .agents/skills   skills/를 가리키는 바로가기 (Claude Code·Codex가 스킬을 찾는 자리, 고칠 필요 없음)
.claude-plugin/          Claude Code 플러그인 목록
```
고칠 곳은 `skills/` 안뿐이다. 무엇을 어디서 바꾸는지는 `skills/snu-report-core/SKILL.md`의 "고칠 곳 지도".
