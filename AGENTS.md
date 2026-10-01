# SNU 전기정보공학부 과제 스킬

## 작업 선택
| 요청 | 읽을 스킬 |
|---|---|
| 논설실 prelab·결과보고서 | `snu-logic-lab/SKILL.md` |
| 회이실 prelab·결과보고서 | `snu-circuit-lab/SKILL.md` |
| 기전연 MATLAB 과제 | `snu-em-hw/SKILL.md` (실험 보고서가 아니다) |
| 스킬 개선·코드 검토·설치 수정 | 요청된 스킬과 코드. 학생 프로필 초기화/과제 작성은 하지 않는다 |

과목 스킬이 공통 엔진 `snu-report-core/SKILL.md`로 안내한다. 공통 기준과 과목 기준을 읽되 실행 도구는 실제 호스트에 맞춘다.

## AI 실행 분기
- **Codex**: `snu-report-core/references/runtime-codex.md`. 설치·갱신은 `bootstrap.py --agent codex`. Claude 플러그인·Claude 앱 설정을 수정하지 않는다.
- **Claude**: `CLAUDE.md`와 `snu-report-core/references/runtime-claude.md`. 설치·갱신은 `bootstrap.py --agent claude`. Codex 설정을 수정하지 않는다.
- 호스트가 둘 다 설치됐다는 이유로 두 흐름을 실행하지 않는다. 둘 다 설치해 달라는 요청에는 `--agent all`을 쓴다.

`.agents/skills`, `.claude/skills`는 각 AI의 작은 진입 문서다. 실제 규칙·코드는 맨 위 `snu-*` 폴더가 원본이다. 진입 문서는 Windows의 symlink 설정 없이도 탐색할 수 있는 실제 폴더로 유지한다.

## 보고서 완료 기준
- 원문 문항·실험 범위·수치의 근거를 먼저 확인한다. 측정·관찰·실행 결과를 지어내지 않는다.
- 회로도는 그림 검사와 회로 검증을, 원고/결과물은 오탈자 검사를 거친다. 과제 범위가 미확정이거나 자료가 빠졌으면 초안으로 명시한다.
- `build.py` 성공만으로 완료하지 않는다. `requirements.yaml` 대응 검사 → 실제 전달 DOCX 렌더링 → 모든 쪽 이미지 읽기 → `quality.py review` → `quality.py deliver`를 거친다.
- 최종 DOCX는 검토한 파일과 같아야 한다. 수정 후 다시 렌더링한다. 문서 내용/레이아웃 검증이 불가능한 부분은 사용자에게 밝힌다.
- 스킬 공개 저장소에 개인정보·교재·측정 사진·사용자 보고서를 올리지 않는다. `profile.yaml`, `courses/`, `inbox/`, `out/`는 git 제외다.

## 저장소 수정
- 작업 브랜치는 `featurejwon`이다. 새 이름의 브랜치를 만들지 않는다.
- 코드 변경은 `python -m unittest discover -s tests -v`, 스킬 frontmatter 검증, 변경 파일 검토를 마친다.
- 이 저장소 변경은 완료 후 `main`에도 반영한다. 원격이 앞서 있거나 다른 변경이 있으면 먼저 확인하며 강제 push하지 않는다.
- 수업 원자료·첨부 보고서는 로컬 검토에만 쓴다. 공개 테스트에는 가상 자료만 사용한다.
