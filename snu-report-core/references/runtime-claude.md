# Claude 실행 흐름

현재 호스트가 Claude Code 또는 Claude일 때만 읽는다. Codex 실행 문서는 함께 읽지 않는다.

1. Claude가 알려 준 스킬 base directory에서 실제 경로를 해석하고, 옆의 `snu-report-core/scripts`를 엔진으로 사용한다. 저장소 작업이면 루트의 `snu-report-core/scripts`이다.
2. Claude Code 설치 요청은 `bootstrap.py --agent claude --yes`. 스킬만 등록할 때는 `--skills-only`. Claude 앱의 MCP 설정은 LTspice 설치·등록이 요청된 경우에만 준비한다. Codex 설정은 변경하지 않는다.
3. Claude의 docx 스킬·렌더러가 실제로 제공되면 그 지침을 따른다. `/mnt/skills/public/docx` 경로는 있는지 확인하고 쓰며 다른 환경의 고정 경로로 대체하지 않는다. 로컬 PC는 `bootstrap.py --agent claude --check`로 확인한다.
4. 자료 → 원문 문항·근거 대응 → 계산 → 원고 → 빌드 → 렌더링 → 모든 쪽 이미지 확인. 공통 내용 기준은 [report-quality.md](report-quality.md)다. 과목별 문항 구조와 실제 데이터가 형식보다 우선한다.
5. 렌더러가 제공되면 `quality.py render 파일.docx --renderer <render_docx.py 절대 경로>`에 전달한다. 로컬 환경의 명시적으로 선택한 LibreOffice는 `--soffice <실행파일 경로>`로 지정할 수 있다. 변환 실패나 미설치를 검증 성공으로 처리하지 않는다.
6. 실제 출력 이미지의 모든 쪽을 읽어 수정한 뒤 `quality.py review 파일.docx --pages 1,2,...`, 이어서 `quality.py deliver 파일.docx --lab-dir <과제 폴더> --kind <prelab|report|hw>`로 전달한다. 사용자가 사진을 아직 준비하지 못했으면 초안으로 제공하고 누락만 묶어 알린다.

채팅 파일 전달은 현재 Claude 환경이 지원하는 첨부 방식으로 한다. Codex의 도구 이름·UI 명령을 요구하지 않는다.
