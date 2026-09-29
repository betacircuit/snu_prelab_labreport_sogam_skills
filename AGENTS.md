# snu_prelab_labreport_skills

서울대 전기정보공학부 과제(실험 보고서, MATLAB 과제) 스킬 저장소. 요청에 맞는 과목 스킬의 SKILL.md를 먼저 읽고 그대로 따른다.
(이 파일이 원본이다. CLAUDE.md는 이 파일을 불러오기만 한다 — 여기만 고친다.)

| 요청 | 스킬 (저장소 맨 위 폴더) |
|---|---|
| 논설실(논리설계 및 실험) prelab·결과보고서 | `snu-logic-lab/SKILL.md` |
| 회이실(회로이론 및 실험) prelab·결과보고서 | `snu-circuit-lab/SKILL.md` |
| 기전연(기초전자기학 및 연습) 실습 과제 — MATLAB HW | `snu-em-hw/SKILL.md` — 실험 보고서가 아니다 |

모든 스킬이 공통 엔진 `snu-report-core/SKILL.md`를 쓴다. 이 저장소 안에서 쓰면 엔진 `$E` = `snu-report-core/scripts`.
`.claude/skills`, `.agents/skills`는 위 폴더를 가리키는 바로가기다 (Claude Code·Codex가 스킬을 찾는 자리). 고칠 곳은 맨 위 `snu-*` 폴더뿐이다.

## 시작할 때
`python snu-report-core/scripts/setup_profile.py --check --course <logic|circuit|em>`
- `need:` 줄은 묻지 않고 처리한다 (`bootstrap.py --yes --deps-only`로 설치, `--init`으로 작업 폴더 만들기).
- 사용자 PC에서 처음 설치할 때는 `python snu-report-core/scripts/bootstrap.py --yes` (스킬·LTspice MCP 등록까지).
- `missing:` 줄(이름, 학번, 조)만 사용자에게 한 번에 묻고 저장한다.

## 지킬 것
- **공개 저장소다.** `profile.yaml`, `courses/`, `inbox/`, `out/`(개인 정보, 수업 자료, 작업물)은 `.gitignore`로 막혀 있다. 강제로 커밋하지 않는다.
- 결과물은 `.docx`로 채팅에 보낸다. 기전연 HW는 `.docx`와 `HW1.m`, 사진이 다 오고 PDF로 바꿀 수 있으면 제출용 `.zip`까지.
- 측정값, 관찰 결과, 코드 실행 결과는 지어내지 않는다. 본인이 찍어야 하는 사진이 아직 없으면 노란 '사진 넣을 곳' 칸으로 두고 보고서를 먼저 완성한다.
- 회로도는 `circuit_kit`의 그림 검사(`save`)와 회로 검증(`verify`)을, 보고서는 `proof.py` 오탈자 검증을, MATLAB 코드는 `mcode.py check`를 통과해야 보낸다.
- 작업 브랜치는 `featurejwon` 하나다. 새 브랜치를 만들지 않는다. 끝나면 `main`에도 올린다.
