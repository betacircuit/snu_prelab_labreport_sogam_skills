# SNU 전기정보공학부 과제 스킬

서울대 전기정보공학부 과제를 Word(.docx)로 써 주는 AI 스킬.

- 논설실(논리설계 및 실험) prelab·결과보고서
- 회로이론 및 실험 prelab·결과보고서
- 기전연(기초전자기학 및 연습) 실습 MATLAB 과제 (HW1.m + 결과 보고서, 제출용 zip)

처음 쓸 때 이름, 학번, 조만 입력할 것. 그다음부터는 "논설실/회이실 Lab03 prelab 써줘", "기전연 실습1 과제 해줘"라고 프롬포트.

## 설치

**PC에 한 번에 설치** — 아래는 Codex용이다. Claude에서 실행할 때는 `--agent codex`를 `--agent claude`로 바꾼다. 스킬, 파이썬 패키지, pandoc, LTspice, LTspice MCP까지 AI가 알아서 설치하고 등록한다.
```
아래 저장소의 과제 스킬을 이 컴퓨터에 설치하고, 필요한 프로그램도 전부 설치해 줘. 설치 명령은 네가 직접 실행해.
1. git clone --depth 1 https://github.com/betacircuit/snu_prelab_labreport_sogam_skills ~/.snu-skills
   (이미 있으면 git -C ~/.snu-skills pull)
2. python ~/.snu-skills/snu-report-core/scripts/bootstrap.py --agent codex --yes
   - python이 안 되면 py -3로. 둘 다 없으면 Python부터 설치해 (Windows: winget install -e --id Python.Python.3.12, macOS: brew install python).
   - 관리자 권한 창이 뜨면 나한테 "예"를 누르라고 말해.
   - ✗가 나온 단계는 출력을 보고 원인을 고친 뒤 다시 돌려. 같은 이유로 두 번 실패하면 멈추고 알려 줘.
3. python ~/.snu-skills/snu-report-core/scripts/bootstrap.py --agent codex --check 결과가 ok인지 확인해.
4. 검증: python ~/.snu-skills/snu-report-core/scripts/spice.py run ~/.snu-skills/snu-circuit-lab/examples/rc_step.cir
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
저장소를 clone하고 AGENTS.md를 읽은 다음, 요청에 맞는 <과목 스킬 폴더>/SKILL.md와 snu-report-core/SKILL.md를 그대로 따라.
측정값, 관찰 결과, 강연 내용은 지어내지 말고, 저장소를 못 열면 추측하지 말고 그렇다고 말해.
요청:
```


## Claude와 Codex 흐름

공통 서식·내용 규칙은 하나이며 실행 경로만 나눈다. Codex는 `runtime-codex.md`, Claude는 `runtime-claude.md`를 읽는다. 머신에 두 앱이 있어도 현재 AI의 스킬·MCP만 설치한다. 두 앱 모두를 요청하면 `--agent all`을 쓴다. 자동 판단이 불가능하면 대상 플래그를 지정한다.

| 구분 | Codex | Claude |
|---|---|---|
| 저장소 진입점 | `AGENTS.md`, `.agents/skills/` | `CLAUDE.md`, `.claude/skills/` |
| 실행 지침 | `runtime-codex.md` | `runtime-claude.md` |
| 설치 대상 | `--agent codex`, `~/.agents/skills` | `--agent claude`, Claude 플러그인 |

두 호스트는 루트의 `snu-*` 공통 생성 코드를 공유한다. 서식 수정은 공유하되 상대 AI의 설정·설치는 변경하지 않는다. 경로 분기 테스트와 설치 대상 테스트를 함께 실행한다.

스킬만 갱신할 때:
```
python ~/.snu-skills/snu-report-core/scripts/bootstrap.py --agent codex --skills-only --yes
```
Codex는 `~/.agents/skills`에 공통 엔진과 과목 스킬을 함께 복사하며, 설치된 파일이 원본과 다르면 갱신한다. 다른 목적의 사용자 파일은 삭제하지 않는다. `--skill-root`로 설치 폴더를 정할 수 있다.

## 보고서 검증

`build.py` 결과는 우선 `out/drafts/<과목>/`의 초안이다. 원문 문항 대응(`requirements.yaml`), 수치·출처 확인, 실제 DOCX 렌더링과 전 쪽 검토를 거친 뒤 `quality.py deliver`가 `out/<과목>/`에 최종본을 만든다. 큰 누락 사진 칸 대신 작은 초안 표시를 쓰고, 회이실은 교재 문항 번호를 보존한다.

```
python $E/build.py courses/circuit/lab01 report --final
python $E/quality.py render <DOCX> --renderer <호스트의 render_docx.py>
# 모든 쪽 PNG를 실제로 확인한 뒤, 전체 쪽 번호로 기록한다.
python $E/quality.py review <DOCX> --pages 1,2,3
python $E/quality.py deliver <DOCX> --lab-dir courses/circuit/lab01 --kind report
```
`$E`는 실제 엔진 경로다. Word가 설치된 Windows에서는 `quality.py render <DOCX> --word`로 실제 Word 렌더링을 기록할 수 있다. 로컬 Claude 환경은 `--soffice <명시한 실행파일>`도 사용할 수 있다. 생성 엔진·원고·근거가 바뀌면 재빌드·렌더링·검토해야 최종본으로 전달할 수 있다. 기존 출력 수정은 비교본뿐 아니라 `out/<과목>/`의 실제 전달 파일까지 갱신한다. 자동 검사만으로 답의 정확성이나 페이지 가독성을 보증하지 않는다.

공개 테스트에는 가상 자료만 넣는다. 테스트: `python -m unittest discover -s tests -v`.

Codex 스킬 구조·탐색 방식: [OpenAI 공식 스킬 문서](https://learn.chatgpt.com/docs/build-skills).

## 쓰는 법

과제용 폴더를 하나 정해서 거기서 요청해요. 자료는 채팅에 첨부하거나 그 폴더의 `inbox/<과목>/`에 넣으면 된다.
파일 이름에 `Lab 03`이 없어도 된다 (`실험 3`, `Experiment 3`, 내용 속 번호, 실험 날짜로 알아서 분류한다).

- `논설실 Lab03 prelab 써줘` + 가이드북, 슬라이드
- `회로이론 Lab02 결과보고서 써줘` + 측정 엑셀, 스코프 사진
- `기전연 실습1 과제 해줘` + 실습 PDF, HW1.m, 문제마다 MATLAB 코드 화면·실행 결과 캡처 (컬러 그대로 들어간다. 코드는 대신 쓰지 않는다)

첫 요청 때 AI가 필요한 프로그램(pandoc, 파이썬 패키지)을 설치 후, 그 폴더에 작업 공간을 만든다.

```
과제 폴더/
├── profile.yaml     이름, 학번 (처음 한 번 물어보고 저장)
├── inbox/<과목>/     자료 넣는 곳 (logic, circuit, em)
├── courses/<과목>/   Lab별(과제는 HW별) 원고, 그림, 근거 자료
└── out/<과목>/       완성된 .docx
```

## 알아 둘 것

- 측정값, 관찰 결과, 강연 내용은 지어내지 않는다. 자료 raw data를 포함할 것.
- 결과물은 수정할 수 있는 `.docx`이다. PDF 변환과 eTL 제출은 개인이 직접 해야한다.
  기초전자기학 HW는 `.docx`와 `HW1.m`을 주고, PDF 변환이 되는 PC면 `HW1_이름_학번.zip`까지 만든다.

## 저장소 구조 (스킬을 고칠 때)

```
snu-logic-lab/      논설실 — SKILL.md(작업 순서) + course.yaml(과목명·파일명) + references/(course.md 규칙, mistakes.md 실수)
snu-circuit-lab/    회이실 — 같은 구성 + references/ltspice.md
snu-lab-photo/      오실로스코프 사진 — 원근·반사광·대비·선명도 보정, 원본 대조
snu-em-hw/          기전연 — 같은 구성 + templates/hw.md
snu-report-core/    공통 엔진: 세 과목이 같이 쓰는 서식·문체·검사·빌드
├── SKILL.md        작업 순서와 "문서와 고칠 곳"
├── references/     format, writing, figures, proofreading, mistakes …
├── scripts/        build.py, proof.py, circuit_kit.py, mcode.py …
└── templates/      style.yaml (서식은 여기 한 곳), 원고 뼈대, reference.docx
AGENTS.md           공통 안내와 Codex 분기 (CLAUDE.md는 Claude 분기를 추가)
```
과목 것은 그 과목 폴더를 열면 바로 있다. 세 과목 공통(서식, 문체, 검사)만 `snu-report-core/`에 있다.
`.claude/skills`, `.agents/skills`는 호스트별 진입 문서다. Windows에서 symlink가 텍스트 파일로 내려오는 문제를 피하도록 실제 폴더를 쓴다.
