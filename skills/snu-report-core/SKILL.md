---
name: snu-report-core
description: 서울대 전기정보공학부 과제 스킬(snu-logic-lab, snu-circuit-lab, snu-ece-seminar)이 함께 쓰는 공통 엔진 — 서식, 문체, 근거 규칙과 docx 빌드 스크립트. 단독 요청에는 쓰지 않고, 과목 스킬이 읽으라고 할 때 읽는다.
---

# 공통 엔진 — Prelab / Lab Report / 소감문

과목 스킬(`snu-logic-lab`, `snu-circuit-lab`, `snu-ece-seminar`)이 함께 쓰는 규칙과 도구다. 과목 스킬의 SKILL.md가 여기로 안내한다.
원고는 마크다운으로 쓰고, `build.py`가 서식을 입혀 docx로 만든다.

## 경로 두 개
- **엔진 `$E`** = 이 폴더의 `scripts/` 절대 경로. 과목 스킬 폴더에서 보면 `../snu-report-core/scripts`.
  저장소를 clone해서 쓰면 `skills/snu-report-core/scripts`, 플러그인·스킬로 설치했으면 설치된 곳이다 (Claude Code는 스킬을 불러올 때 base directory로 알려 준다).
  이 문서와 과목 스킬의 `python $E/build.py …`는 `$E`를 그 절대 경로로 바꿔 실행한다.
- **작업 폴더 `W`** = `profile.yaml`이 있는 폴더. 사용자 정보와 과목별 작업물(`courses/`, `inbox/`, `out/`)이 쌓인다.
  스크립트는 현재 폴더에서 위로 `profile.yaml`을 찾으므로 `W` 안에서 실행한다. 없으면 아래 "맨 처음"대로 만든다.

## 참고 문서
| 문서 | 내용 |
|---|---|
| `references/setup.md` | 처음 설정: 사용자에게 물을 최소 정보와 저장 방법 |
| `references/format.md` | 서식 규칙 (첫 쪽, 글꼴, 표, 그림, 수식, 번호) |
| `references/writing.md` | 문체 (쓰지 않는 표현, 용어, 수식 배치, 실험 방법·오차 분석 쓰는 법) |
| `references/evidence.md` | 데이터와 근거 (만들지 않을 것, 묻기 전에 판단할 것, 근거표) |
| `references/figures.md` | 회로도와 그래프 그리는 법 |
| `references/prelab.md` | prelab 절차 |
| `references/labreport.md` | lab report 절차 |
| 과목 스킬의 `references/course.md` | 그 과목의 공통 규칙 (마감, 파일명, 필수 항목, 일정) |

## 맨 처음: 준비 확인 — `references/setup.md`
`python $E/setup_profile.py --check --course <과목>`을 돌린다 (과목: `logic`, `circuit`, `seminar`).
- `need:` 줄은 내가 처리한다: 패키지 설치, 작업 폴더 만들기(`--init`).
- `missing:` 줄(이름, 학번, 조 등)만 모아 사용자에게 **한 번에** 묻고 저장한다. 이미 있으면 묻지 않는다.

## 반드시 지킬 것
1. **결과물은 `.docx`로만 준다.** PDF는 수정할 수 없다. PDF 변환과 eTL 제출은 사용자가 한다.
2. **파일명은 과목 설정의 `filename` 규칙대로 (과목 스킬의 `course.yaml`, 작업 폴더 `courses/<과목>/course.yaml`이 덮어씀).** prelab·lab report는 `prelab{NN}_학번_이름`, `lab{NN}_학번_이름` 형식을 `build.py`가 검사한다.
3. **입력 범위를 지킨다.** prelab은 가이드북 Prelab 절과 슬라이드 지시로, lab report는 가이드북 Lab·Discussion 절, 슬라이드 지시, 실험 결과로만 쓴다. lab report에 prelab 그림을 가져오지 않는다.
4. **측정값과 관찰을 만들지 않는다. 대신 자료로 알 수 있는 것은 묻지 않는다.** 표기 해석처럼 판단이 필요한 것은 스스로 정하고 실험 방법에 밝힌다 (evidence.md).
5. **요구 문항을 빠짐없이 답한다.** `courses/<과목>/labNN/requirements.md` 대응표로 대조한다.
6. **계산은 스크립트로 한다.** 진리표, 간소화, 핀 배선, 평균, 계산값을 손으로 구하지 않는다.
7. **서식(format.md)과 문체(writing.md)는 사용자가 정한 것이다.** 바꾸라는 말이 있을 때만 바꾼다.

## 작업 순서 (prelab / lab report)

### 0. 자료 정리 (매번 먼저)
1. 작업 폴더가 git 저장소면 `git pull`로 사용자가 GitHub 웹에서 `inbox/<과목>/`에 올린 파일을 받는다. 채팅 첨부, 연결된 폴더, Google Drive에 있는 자료도 `inbox/<과목>/`에 넣는다.
2. `python $E/ingest.py` — `inbox/<과목>/`의 `[Lab NN]`·`LabNN_` 파일을 `courses/<과목>/labNN/`, Lab00은 `courses/<과목>/materials/`로 분류한다. 중복은 버리고 PDF 텍스트를 뽑는다. 파일명에 Lab 번호가 없으면 `--course <과목> --lab NN 파일`.
3. 새 Lab이면 `meta.yaml`과 `requirements.md` 초안이 생긴다. 한국어 제목을 채우고, 슬라이드 날짜가 과목 규칙(course.md)과 다르면 규칙을 따르고 사용자에게 한 줄로 알린다.
4. 작업 폴더가 git 저장소면 분류 결과를 커밋하고 push한다. 마감을 확인한다.

### A. Prelab — `references/prelab.md`
문항 확정 → 문항별 도구 실행 → `prelab/prelab.md` → `style_check.py`로 반복 고치기 → `python $E/build.py courses/<과목>/labNN prelab --pdf` → 미리보기 확인 → docx 전달

### B. Lab report — `references/labreport.md`
요구사항 확인 → `report/evidence.yaml` → `report/figs/make_figs.py` → `report/report.md` → `style_check.py`로 반복 고치기 → `python $E/build.py courses/<과목>/labNN report --pdf` → 미리보기 확인 → docx 전달

## 폴더
```
작업 폴더 W (setup_profile.py --init이 만든다)
├── profile.yaml              이름, 학번, 학과, 관심 분야, 문체 샘플 (모든 과목 공통)
├── inbox/<과목>/             자료 넣는 곳 (logic, circuit, seminar)
├── courses/<과목>/
│   ├── course.yaml           조, 조원 (과목명·파일명 규칙 기본값은 과목 스킬의 course.yaml)
│   ├── materials/            Lab00 공통 자료
│   └── labNN/ (소감문은 weekNN/)
│       ├── meta.yaml         lab, title, lab_date, prelab_due, report_due, scope
│       ├── requirements.md   요구사항과 대응표
│       ├── materials/        guidebook, slides (+ .txt)
│       ├── prelab/           prelab.md, figs/make_figs.py
│       ├── report/           report.md, evidence.yaml, raw/, figs/make_figs.py
│       └── build/            docx, preview/ (git 제외)
└── out/<과목>/               전달용 docx 사본

스킬 (설치된 곳 또는 저장소의 skills/)
├── snu-report-core/          이 공통 엔진 (scripts/ = $E, templates/, references/, requirements.txt)
├── snu-logic-lab/            논리설계 및 실험 (course.yaml, references/course.md)
├── snu-circuit-lab/          회로이론 및 실험
└── snu-ece-seminar/          전정세 소감문 (data/professors.yaml = 교수 DB)
```

## 스크립트 (`$E/`)
| 스크립트 | 하는 일 |
|---|---|
| `setup_profile.py` | 준비 확인(`--check`: 패키지, 작업 폴더, 빠진 정보), 작업 폴더 만들기(`--init`), 사용자 정보 저장 |
| `ingest.py` | 자료 자동 분류 (`inbox/<과목>/` → `courses/<과목>/`), 중복 제거, 텍스트 추출, meta·requirements 초안 |
| `evidence.py` | 근거표 검사, 평균·계산값, xlsx 셀 덤프 |
| `build.py` | 원고 → docx (제목 블록, 절 번호, 표·그림 틀, 수식 공백, 파일명). `prelab`, `report`, `sogam`. `--pdf`로 미리보기 |
| `style_check.py` | 문체 검사: 어미·문장 시작·구절 반복, 같은 서술어 반복(어휘), 접속어·추측 남용, 본문 굵은 글씨, 기타 절 분량 (build.py가 자동 실행) |
| `docx_post.py` | 표 캡션 행, 그림 틀, 열 너비, 문단 앞 공백, `-` 목록, 한글-영문 자동 간격 끄기, Word 호환 모드 해제 (build.py가 호출) |
| `ooxml_order.py` | 저장 직전 OOXML 스키마 순서 정리 — Word 호환성 검사 경고·"읽을 수 없는 내용" 방지 |
| `circuit_kit.py` | 회로도(게이트 이름 중앙, 노드 이름 점 옆), 그래프 막대 스타일 |
| `logic.py` | 진리표, SOP/POS 최소화, K-map, 넷리스트 |
| `pinmap.py` | 넷리스트 → 74xx 칩·핀 배선표 (`--nand-only`) |
| `timing.py`, `scope.py`, `compare.py` | 예상 파형, 스코프 CSV 측정, 진리표 비교 |
| `spice.py` | SPICE 넷리스트 공통 문법 검사(`lint`), ngspice 실행·`.meas`(`run`), 파형·보드 선도(`plot`), 값 읽기(`value`), 연결표(`nodes`). LTspice raw도 읽는다 |
| `make_template.py` | style.yaml → reference.docx |

그림 스크립트(`make_figs.py`)는 맨 위에서 작업 폴더를 찾고 엔진을 import한다. 엔진 경로는 `setup_profile.py`와 `build.py`가 `W/.snu-engine`에 적어 둔다:
```python
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "profile.yaml").exists())   # 작업 폴더
_eng = ROOT / ".snu-engine"   # 엔진 경로 (setup_profile.py·build.py가 적어 둠)
ENGINE = next(e for e in (ROOT / "skills/snu-report-core/scripts",
                          Path(_eng.read_text(encoding="utf-8").strip()) if _eng.exists() else None)
              if e and (e / "circuit_kit.py").exists())
sys.path.insert(0, str(ENGINE))
```

설치: `pip install -r <이 폴더>/requirements.txt`, `pandoc`. 선택: LibreOffice(미리보기 PDF, `libreoffice-math` 포함), `pdftotext`. `setup_profile.py --check`가 빠진 것을 알려 준다.

## 원고 문법
| 쓰는 법 | 결과 |
|---|---|
| `# 제목`, `## 소제목` | `1. 제목`, `1.1) 소제목` |
| `# 제목 {-}` | 번호 없는 제목 |
| `![캡션](figs/a.png){#fig:x width=80%}` | 그림 틀과 `Fig.1 - 캡션` |
| 표 위에 `Table: 캡션 (단위: ns) {#tbl:x}` | 표 맨 아래 캡션 행 `Table.1 - 캡션` |
| `@fig:x과`, `@tbl:x의` | `Fig.1과`, `Table.1의` |
| `$Y_1 = \overline{AB}$`, `$$…$$` | Word 수식 (연산자 공백 자동) |
| `- $B = 0$일 때: …` | 이름표 붙은 목록 (경우 나누기, 오차 원인). 이름표는 굵게 하지 않는다 |
| `1. 회로 연결: …` | 이름표 붙은 번호 목록 (실험 방법) |

## 마무리 확인
- [ ] 전달 파일이 `.docx`이고 이름이 규칙대로다
- [ ] 대응표의 모든 문항에 답했다
- [ ] 모든 수치가 evidence.yaml 또는 스크립트 결과에서 왔다
- [ ] lab report에 prelab 그림, 비공식 자료, 작업용 표시(`[TODO]` 등)가 없다
- [ ] `style_check.py` 통과 (어휘 반복 포함), 수식 뒤에서 문장이 이어지지 않는다
- [ ] 굵은 글씨는 맨 위 제목과 절 제목에만 있다
- [ ] 미리보기 PDF를 전 페이지 확인했다
- [ ] docx 스키마 검사 통과 (`python /mnt/skills/public/docx/scripts/office/validate.py 파일.docx`, 있을 때)
