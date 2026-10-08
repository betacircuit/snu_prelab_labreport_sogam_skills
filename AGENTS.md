# SNU 전기정보공학부 과제 스킬

## 작업 선택
| 요청 | 읽을 스킬 |
|---|---|
| 논설실 prelab·결과보고서 | `snu-logic-lab/SKILL.md` |
| 회이실 prelab·결과보고서 | `snu-circuit-lab/SKILL.md` |
| 기전연 MATLAB 과제 | `snu-em-hw/SKILL.md` (실험 보고서가 아니다) |
| 오실로스코프·계측기 사진 보정 | `snu-lab-photo/SKILL.md` |
| 스킬 개선·코드 검토·설치 수정 | 요청된 스킬과 코드. 학생 프로필 초기화/과제 작성은 하지 않는다 |

과목 스킬이 공통 엔진 `snu-report-core/SKILL.md`로 안내한다. 작업 순서·완료 기준(빌드 → 렌더링 → 전 쪽 확인 → `quality.py deliver`)은 그 문서가 원본이다.

## AI 실행 분기
- **Codex**: `snu-report-core/references/runtime-codex.md`, 설치 `bootstrap.py --agent codex`.
- **Claude**: `CLAUDE.md` → `snu-report-core/references/runtime-claude.md`, 설치 `bootstrap.py --agent claude`.
- 다른 AI의 설정은 건드리지 않는다. 둘 다 설치해 달라고 하면 `--agent all`.

`.agents/skills`, `.claude/skills`는 각 AI의 작은 진입 문서(실제 폴더, symlink 아님)다. 규칙·코드의 원본은 맨 위 `snu-*` 폴더다.

## 공개 저장소
개인정보·교재·측정 사진·보고서를 올리지 않는다. `profile.yaml`, `courses/`, `inbox/`, `out/`는 git 제외다. 공개 테스트에는 가상 자료만 쓴다.

## 저장소 수정
- 작업 브랜치는 `featurejwon`이다. 새 이름의 브랜치를 만들지 않는다.
- 코드 변경은 `python -m unittest discover -s tests -v`, 스킬 frontmatter 검증, 변경 파일 검토를 마친다.
- 이 저장소 변경은 완료 후 `main`에도 반영한다. 원격이 앞서 있거나 다른 변경이 있으면 먼저 확인하며 강제 push하지 않는다.
