# Codex 실행 흐름

현재 호스트가 Codex일 때만 읽는다. Claude 실행 문서는 함께 읽지 않는다.

1. 설치된 스킬 목록의 실제 `SKILL.md` 경로를 기준으로 공통 엔진을 찾는다. 경로가 바로가기이면 대상을 먼저 해석한다. 저장소에서는 `snu-report-core/scripts`, 사용자 설치에서는 과목 스킬과 같은 부모의 `snu-report-core/scripts`가 엔진이다. `/mnt/skills`, `~/.claude`를 가정하지 않는다.
2. 문서 작업에 제공된 documents 스킬이 있으면 읽고, `load_workspace_dependencies` 도구가 있으면 Python·문서 도구의 실제 경로를 확인한다. 도구가 없는 CLI에서는 현재 Python과 `bootstrap.py --agent codex --check`로 확인한다. 필요한 의존성만 작업 환경에 준비한다. 스킬 수정·검토 요청에는 학생 프로필 초기화가 필요 없다.
3. 설치 요청은 `bootstrap.py --agent codex --yes`로 처리한다. 스킬만 갱신할 때는 `--skills-only`. Codex만 요청했으면 Claude 플러그인이나 Claude 앱 설정을 변경하지 않는다. 네트워크·설치 권한은 현재 세션의 권한 규칙을 따른다.
4. 자료 읽기 → 원문 문항·근거 대응 → 계산 → 원고 → 빌드 → 렌더링 → 모든 쪽 이미지 확인 순서다. 내용 기준은 [report-quality.md](report-quality.md). 원고·문항표·수치가 일치하기 전에는 꾸미기에 시간을 쓰지 않는다.
5. 빌드할 때 경로는 절대 경로로 전달하고 PowerShell에서는 `& 'Python 경로' '스크립트 경로' ...`처럼 인자를 나눈다. 엔진과 과제 폴더를 구분하고 Linux의 `:` 리소스 경로를 Windows에 그대로 쓰지 않는다.
6. Codex 문서 스킬의 렌더러가 제공되면 그 `render_docx.py` 절대 경로를 `quality.py render --renderer <경로>`에 전달한다. 번들 렌더링 도구를 우선한다. 제공되지 않거나 실행이 불가능하면 가능한 내용·OOXML 검사를 진행하고 렌더링 미검증 사실을 알린다. 프로그램이 없다는 이유로 문서 작업 전체를 중단하거나 검증 완료를 주장하지 않는다.
7. `quality.py render`가 만든 **최신 DOCX의 모든 쪽**을 `view_image` 등 실제 이미지 읽기 도구로 확인한다. 접촉 시트는 탐색용이며 작은 글자·수식·장비 숫자는 각 쪽/확대 이미지로 확인한다. 이미지를 열지 않고 검토 완료를 기록하지 않는다.
8. 전체 확인 후 `quality.py review 파일.docx --pages 1,2,...`로 기록하고 `quality.py deliver 파일.docx --lab-dir <과제 폴더> --kind <prelab|report|hw>`로 최종 전달 사본을 만든다. 파일이 바뀌면 검토 기록은 무효가 된다. 최종 파일은 실제 절대 경로 링크로 전달하고, 초안이면 빠진 자료를 함께 명시한다.

호스트 선택은 현재 대화가 알려 준 실행 환경이 기준이다. 머신에 Claude·Codex가 둘 다 설치됐다는 사실이나 모델 이름으로 선택하지 않는다. `--agent`는 설치 대상 선택이며 보고서 품질·출처 규칙을 바꾸지 않는다.
