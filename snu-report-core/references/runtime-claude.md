# Claude 실행 흐름

Claude Code·Claude에서만 읽는다. 작업 순서와 완료 기준은 엔진 SKILL.md다. 여기는 Claude에서 다른 점만 적는다.

- **엔진 경로**: Claude가 알려 준 스킬 base directory 옆의 `snu-report-core/scripts` (저장소 작업이면 루트의 것).
- **설치**: `bootstrap.py --agent claude --yes`, 스킬만 `--skills-only`, 확인 `--check`. Claude 앱 MCP는 LTspice 등록을 요청받았을 때만. Codex 설정은 건드리지 않는다.
- **docx 도구**: Claude의 docx 스킬·렌더러가 실제로 있으면 그 지침을 따른다. `/mnt/skills/public/docx`는 있는지 확인하고 쓴다.
- **렌더링**: `quality.py render <DOCX> --renderer <render_docx.py 절대 경로>`, 로컬 LibreOffice는 `--soffice <경로>`. 변환 실패를 검증 성공으로 치지 않는다.
- **전달**: 현재 환경의 파일 첨부로 보낸다. 사진이 아직 없으면 초안과 빠진 사진 목록을 함께 보낸다.
