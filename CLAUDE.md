# snu_prelab_labreport_sogam_skills

서울대 전기정보공학부 과제(실험 보고서, 세미나 소감문) 스킬 저장소. 요청에 맞는 과목 스킬의 SKILL.md를 먼저 읽고 그대로 따른다.
(AGENTS.md와 CLAUDE.md는 같은 내용이다. 고칠 때 둘 다 고친다.)

| 요청 | 스킬 |
|---|---|
| 논설실(논리설계 및 실험) prelab·결과보고서 | `skills/snu-logic-lab/SKILL.md` |
| 회로이론 및 실험 prelab·결과보고서 | `skills/snu-circuit-lab/SKILL.md` |
| 전정세 강연 소감문 | `skills/snu-ece-seminar/SKILL.md` |

세 스킬 모두 공통 엔진 `skills/snu-report-core/SKILL.md`를 쓴다. 이 저장소 안에서 쓰면 엔진 `$E` = `skills/snu-report-core/scripts`.

## 시작할 때
`python skills/snu-report-core/scripts/setup_profile.py --check --course <logic|circuit|seminar>`
- `need:` 줄은 묻지 않고 처리한다 (`bootstrap.py --yes --deps-only`로 설치, `--init`으로 작업 폴더 만들기).
- 사용자 PC에서 처음 설치할 때는 `python skills/snu-report-core/scripts/bootstrap.py --yes` (스킬·LTspice MCP 등록까지).
- `missing:` 줄(이름, 학번, 조)만 사용자에게 한 번에 묻고 저장한다.

## 지킬 것
- **공개 저장소다.** `profile.yaml`, `courses/`, `inbox/`, `out/`(개인 정보, 수업 자료, 작업물)은 `.gitignore`로 막혀 있다. 강제로 커밋하지 않는다.
- 결과물은 `.docx`만. 채팅으로 보낸다.
- 측정값, 관찰 결과, 강연 내용은 지어내지 않는다.
- 회로도는 `circuit_kit`의 그림 검사(`save`)와 회로 검증(`verify`)을, 보고서는 `proof.py` 오탈자 검증을 통과해야 보낸다.
