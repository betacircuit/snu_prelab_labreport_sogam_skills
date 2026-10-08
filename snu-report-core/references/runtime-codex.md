# Codex 실행 흐름

Codex에서만 읽는다. 작업 순서와 완료 기준은 엔진 SKILL.md다. 여기는 Codex에서 다른 점만 적는다.

## 기능과 양식은 그대로
엔진 스크립트(`ingest`, `evidence`, `circuit_kit`, `spice`·`bode`, `proof`·`style_check`, `build`, `quality`)를 그대로 호출한다. 채팅 답변이나 새 문서 생성기로 대신하지 않는다. Codex documents 스킬은 렌더링·검증 도구로만 쓰고, 그 디자인 기본값으로 양식(format.md, `style.yaml`)을 바꾸지 않는다.

## Codex에서 다른 점
1. **엔진 경로**: 설치된 스킬의 실제 `SKILL.md` 경로에서 찾는다 (바로가기는 대상 해석). `/mnt/skills`, `~/.claude`를 가정하지 않는다.
2. **의존성**: documents 스킬이 있으면 읽고, `load_workspace_dependencies`가 있으면 Python·문서 도구 경로를 확인한다. 없으면 `bootstrap.py --agent codex --check`.
3. **설치**: `bootstrap.py --agent codex --yes`, 스킬만 `--skills-only`. Claude 플러그인·앱 설정은 건드리지 않는다.
4. **Windows 명령**: 절대 경로로 넘기고 PowerShell에서는 `& 'Python 경로' '스크립트 경로' ...`처럼 인자를 나눈다.
5. **렌더링**: documents 스킬의 `render_docx.py`를 `quality.py render --renderer <경로>`에 넘긴다. Word가 있으면 `--word`도 된다. 도구가 모두 없으면 OOXML 검사까지 하고 렌더링 미검증을 알린다.
6. **쪽 확인**: 최신 DOCX의 모든 쪽을 `view_image` 등으로 연다. 접촉 시트는 탐색용이고, 작은 글자·수식·장비 숫자는 쪽 이미지나 확대로 본다.
7. **전달**: 최종 파일은 절대 경로 링크로 준다.
8. **LTspice 화면**: 설치된 computer-use 스킬로 ([ltspice-computer-use.md](../../snu-circuit-lab/references/ltspice-computer-use.md) "Codex / Windows").
