---
name: snu-report-core
description: 서울대 전기정보공학부 과제 스킬(snu-logic-lab, snu-circuit-lab, snu-em-hw)이 함께 쓰는 공통 엔진 — 서식, 문체, 근거 규칙과 docx 빌드 스크립트. 단독 요청에는 쓰지 않고, 과목 스킬이 읽으라고 할 때 읽는다.
---

# 공통 엔진

과목 스킬이 함께 쓰는 규칙과 도구다. 원고는 마크다운으로 쓰고 `build.py`가 docx로 만든다.

## 호스트
실행 환경이 Codex면 [runtime-codex.md](references/runtime-codex.md), Claude면 [runtime-claude.md](references/runtime-claude.md) **하나만** 읽는다. 설치된 앱으로 추측하지 않는다. 호스트에 따라 바뀌는 것은 도구 호출·경로·렌더러뿐이고, 원고 규칙·서식은 같다.

스킬 개선·검토 요청은 코드 작업이다. 프로필을 만들거나 과제 자료를 분류하지 않는다. 서식 개선 요청에 첨부 보고서가 있으면 실제 쪽을 읽고 문제를 특정한 뒤, 원고 지침과 생성 코드를 함께 고친다. 테스트 통과만으로 서식 개선을 끝냈다고 하지 않는다.

## 경로
- **엔진 `$E`** = 이 폴더의 `scripts/` 절대 경로 (저장소에서는 `snu-report-core/scripts`, 설치본은 호스트가 알려 준 스킬 경로 옆). 명령의 `$E`는 이 경로로 바꿔 실행한다.
- **작업 폴더 `W`** = `profile.yaml`이 있는 폴더. 스크립트는 위로 `profile.yaml`을 찾으니 `W` 안에서 실행한다.

```
W/
├── profile.yaml              이름, 학번, 문체 샘플
├── inbox/<과목>/             자료 넣는 곳 (logic, circuit, em)
├── courses/<과목>/
│   ├── course.yaml           조, 조원
│   ├── materials/            Lab00 공통 자료, 교재
│   └── labNN/ (기전연 hwNN/) meta.yaml, requirements.md·.yaml, materials/, prelab/, report/(evidence.yaml, raw/, figs/), build/
└── out/<과목>/               전달본
```

## 원칙
1. **지어내지 않는다.** 측정·관찰·실행 결과는 자료에서만. 자료로 알 수 있는 것은 묻지 않는다 ([evidence.md](references/evidence.md)).
2. **요구한 문항만, 빠짐없이.** 대응표는 `requirements.md`(요약)와 `requirements.yaml`(최종 검사). 요구하지 않은 절("실험 준비", 긴 이론 배경)은 만들지 않는다. lab report에 prelab 그림을 가져오지 않는다.
3. **계산은 스크립트로.** 진리표, 간소화, 핀 배선, 평균, 이론값.
4. **회로도는 그림 검사(`c.save`)와 회로 검증(`c.verify`/`verify_seq`)을 통과해야 넣는다** ([figures.md](references/figures.md)).
5. **원고와 결과물 모두 오탈자·문체 검사를 통과한다** ([proofreading.md](references/proofreading.md), [writing.md](references/writing.md)). 본인이 쓴 글로 읽혀야 한다 (`[본인 글]`).
6. **서식·문체는 사용자가 정한 것이다.** 바꾸라는 말이 있을 때만 바꾼다 ([format.md](references/format.md)).
7. **전달은 `.docx`**, 파일명은 과목 `course.yaml`의 `filename` 규칙 (`build.py`가 검사). 기전연은 PDF·zip까지.
8. 개인정보·과제 자료를 스킬 저장소에 커밋하지 않는다.

## 작업 순서
0. **준비**: `python $E/setup_profile.py --check --course <logic|circuit|em>` — `need:`는 알아서 처리, `missing:`(이름, 학번, 조)만 한 번에 묻는다 ([setup.md](references/setup.md)).
1. **자료**: 채팅 첨부·폴더 자료를 `inbox/<과목>/`에 두고 `python $E/ingest.py`. Lab 번호는 파일명 → 내용 → 날짜로 찾는다. `_unsorted/`에 남으면 묻지 말고 내가 파일을 읽어 course.md 일정과 대조한 뒤 `--course <과목> --lab NN 파일`로 다시 돌린다. 새 Lab이면 `meta.yaml`·`requirements` 초안이 생긴다.
2. **쓰기 전**: 공통·과목 `mistakes.md`에서 이번 주제 항목 확인.
3. **원고**: prelab은 [prelab.md](references/prelab.md), lab report는 [labreport.md](references/labreport.md). 내용 기준은 [report-quality.md](references/report-quality.md).
4. **빌드**: `python $E/build.py courses/<과목>/labNN <prelab|report|hw> [--final]` — 문체·오탈자 검사를 같이 돌리고 `out/drafts/`에 초안을 둔다.
5. **전달** (빌드 성공은 초안일 뿐이다):
   ```
   python $E/quality.py render <DOCX> --renderer <호스트 렌더러>    # 호스트 문서의 방법
   # 모든 쪽 이미지를 실제로 읽고 고친다. 고쳤으면 다시 빌드·렌더링
   python $E/quality.py review <DOCX> --pages 1,2,3
   python $E/quality.py deliver <DOCX> --lab-dir courses/<과목>/labNN --kind <prelab|report|hw>
   ```
   `deliver`는 DOCX·쪽 이미지·엔진의 해시를 맞춰 본다. 렌더링 뒤 한 글자라도 고치거나 엔진이 바뀌면 다시 렌더링·검토한다. YAML 상태만 answered로 바꿔 검증을 대신하지 않는다. 이미 전달한 `out/` 파일을 고쳤으면 비교본만 만들지 말고 그 파일을 검증한 최신본으로 바꾼다. 렌더링이 불가능하면 초안으로 주고 미검증 부분을 밝힌다.

## 원고 문법
| 쓰는 법 | 결과 |
|---|---|
| `# 제목`, `## 소제목`, `# 제목 {-}` | `1. 제목`, `1.1) 소제목`, 번호 없음 |
| `# 4.2) 3-bit comparator` | `2. 3-bit comparator` — 원문 번호는 대응표에만 남고 출력에는 자동 번호 하나 (format.md) |
| `![캡션](figs/a.png){#fig:x width=80%}` | 그림 틀과 `Fig.1 - 캡션`. 파일이 없으면 `hint="무엇을 찍을지"` → 초안에 한 줄 누락 표시 |
| 표 위 `Table: 캡션 (단위: ns) {#tbl:x}` | 표 맨 아래 캡션 행 `Table.1 - 캡션` |
| `@fig:x과`, `@tbl:x의` | `Fig.1과`, `Table.1의` |
| `$…$`, `$$…$$` | Word 수식 |
| `- $B = 0$일 때: …`, `1. 회로 연결: …` | 이름표 목록 (굵게 하지 않음) |
| `[TODO: …]`, `[확인 필요: …]` 등 | 초안 형광펜, `--final`에서 실패 (evidence.md "작업용 표시") |

## 문서와 고칠 곳
| 내용 | 원본 |
|---|---|
| 서식 값 (글꼴, 크기, 여백, 제목 블록, 번호 모양) | `templates/style.yaml` |
| 서식 규칙 (표·그림·수식·쪽 배치) | [format.md](references/format.md) |
| 문체, 쓰지 않는 표현 | [writing.md](references/writing.md), `scripts/style_check.py`의 `BANNED` |
| 용어 (영어로 쓸 말 / 한국어로 쓸 말) | [terms.md](references/terms.md) — `proof.py`가 읽는다 |
| 오탈자 검사 순서와 목록 | [proofreading.md](references/proofreading.md), `scripts/proof.py` |
| 근거·작업용 표시 | [evidence.md](references/evidence.md) |
| 회로도·그래프·순차 회로 검증 | [figures.md](references/figures.md), `scripts/circuit_kit.py` |
| 공통 실수 | [mistakes.md](references/mistakes.md) (과목 실수는 과목 폴더) |
| 과목명·파일명·작업 단위 | `snu-<과목>/course.yaml` |
| 과목 제출 규칙·마감·일정 | `snu-<과목>/references/course.md` |
| **새 과목** | `snu-<과목>/`에 `SKILL.md`, `course.yaml`, `references/course.md`를 만들고 `.claude-plugin/marketplace.json`과 `AGENTS.md` 표에 한 줄씩 |

## 스크립트 (`$E/`)
| 스크립트 | 하는 일 |
|---|---|
| `bootstrap.py` | 설치 (`--agent <codex\|claude> --yes`, `--deps-only`, `--check`) |
| `setup_profile.py` | 준비 확인, 작업 폴더(`--init`), 사용자 정보 저장 |
| `ingest.py` | 자료 분류, 텍스트 추출, meta·requirements 초안, 교재 문항 추출(`--questions NN`) |
| `evidence.py` | 근거표 검사, 계산값, xlsx 셀 덤프 |
| `build.py` | 원고 → docx (`prelab`, `report`, `hw`) |
| `quality.py` | 문항 대응 검사, 렌더링·검토 기록, 전달 |
| `proof.py`, `style_check.py` | 오탈자, 문체 |
| `circuit_kit.py` | 회로도와 검사, 조합·순차 회로 검증, 막대그래프 스타일 |
| `logic.py`, `pinmap.py` | 진리표·최소화·K-map, 74xx 핀 배선표 |
| `timing.py`, `scope.py`, `compare.py` | 예상 파형, 스코프 CSV, 진리표 비교 |
| `spice.py`, `bode.py` | SPICE 검사·실행·파형, 보드 선도·주파수 응답 표·페이저도 |
| `mcode.py` | MATLAB 과제 코드 검사·실행·zip |
| `docx_post.py`, `math_layout.py`, `ooxml_order.py`, `make_template.py` | build.py가 부르는 후처리 |

그림 스크립트(`make_figs.py`)는 맨 위에서 엔진을 찾는다 (`W/.snu-engine`에 경로가 적혀 있다):
```python
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "profile.yaml").exists())   # 작업 폴더
_eng = ROOT / ".snu-engine"
ENGINE = next(e for e in (ROOT / "snu-report-core/scripts",
                          Path(_eng.read_text(encoding="utf-8").strip()) if _eng.exists() else None)
              if e and (e / "circuit_kit.py").exists())
sys.path.insert(0, str(ENGINE))
```
