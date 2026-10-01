#!/usr/bin/env python3
"""과제 스킬에 필요한 것을 한 번에 설치한다 — 사용자 PC에서 Claude Code·Codex가 돌리는 용도.

  python bootstrap.py --check      # 있는 것과 없는 것만 본다 (필수가 빠지면 exit 1)
  python bootstrap.py --agent codex --yes  # Codex 대상으로 설치 (Claude는 --agent claude)
  python bootstrap.py              # 설치 목록을 보여 주고 y/N을 묻는다
  python bootstrap.py --dry-run    # 실행할 명령만 보여 준다

  --no-ltspice   LTspice·LTspice MCP를 건너뛴다 (회로이론을 안 들을 때)
  --preview      LibreOffice도 설치한다 (미리보기 PDF용, 용량이 큼)
  --deps-only    프로그램만 설치하고 MCP·스킬 등록은 건너뛴다 (클라우드 세션에서 쓸 때)
  --skills-only  선택한 AI의 스킬만 설치/갱신한다 (패키지·MCP 변경 없음)
  --agent        codex | claude | all | auto (세션 신호로 판단, 모호하면 명시)

설치하는 것 (있으면 건너뛴다. 다시 돌려도 안전하다)
  1. 파이썬 패키지 (requirements.txt)          5. uv, ltspice-mcp (LTspice MCP 서버)
  2. pandoc (docx 변환)                         6. MCP 등록: Claude Code, Codex, Claude 앱
  3. LTspice (Windows·macOS)                    7. 스킬 등록: Claude Code 플러그인, Codex(~/.agents/skills)
  4. ngspice (macOS·Linux, 넷리스트 검증)       8. pdftotext (macOS·Linux, 선택)
Windows는 winget, macOS는 Homebrew, Linux는 apt-get을 쓴다.
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ws import ENGINE, SKILLS_DIR, find_tool  # noqa: E402

REPO = "betacircuit/snu_prelab_labreport_sogam_skills"
MARKET, PLUGIN = "snu-ece-skills", "snu-reports"
SKILL_NAMES = sorted(p.name for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists())   # 저장소 맨 위의 스킬 폴더 전부 (새 과목을 넣으면 자동)
REQUIREMENTS = ENGINE.parent / "requirements.txt"
PY_MODULES = ["yaml", "docx", "sympy", "schemdraw", "matplotlib", "numpy", "openpyxl", "fitz", "kiwipiepy", "spicelib"]
WIN, MAC, LINUX = sys.platform == "win32", sys.platform == "darwin", sys.platform.startswith("linux")
USER_ROOT = Path.home()
DRY = False


# ───────── 실행 도구 ─────────
def sh(cmd: list[str], check: bool = False, quiet: bool = False) -> subprocess.CompletedProcess:
    print("  $", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    if DRY:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not quiet and r.returncode:
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print("    " + "\n    ".join(tail))
    if check and r.returncode:
        raise RuntimeError(f"실패 (exit {r.returncode}): {' '.join(cmd)}")
    return r


def exe(name: str) -> str | None:
    """Windows에서는 .cmd/.exe까지 찾는다 (claude.cmd, codex.cmd 등)."""
    return shutil.which(name) or (shutil.which(name + ".cmd") if WIN else None) or (shutil.which(name + ".exe") if WIN else None)


def pkg_install(win_id: str | None = None, brew: str | None = None, cask: str | None = None,
                apt: str | None = None) -> bool:
    if WIN and win_id:
        if not exe("winget"):
            print("  ✗ winget 없음 — Microsoft Store에서 '앱 설치 관리자'를 설치한 뒤 다시 돌린다")
            return False
        r = sh(["winget", "install", "-e", "--id", win_id, "--silent",
                "--accept-package-agreements", "--accept-source-agreements"])
        return r.returncode == 0 or "already installed" in (r.stdout + r.stderr).lower()
    if MAC and (brew or cask):
        if not exe("brew"):
            print("  ✗ Homebrew 없음 — https://brew.sh 의 설치 명령을 터미널에서 먼저 실행한다 (비밀번호 입력 필요)")
            return False
        return sh(["brew", "install", "--cask", cask] if cask else ["brew", "install", brew]).returncode == 0
    if LINUX and apt:
        prefix = []
        if os.geteuid() != 0:
            if not exe("sudo"):
                print(f"  ✗ root 권한 필요: apt-get install {apt}")
                return False
            prefix = ["sudo", "-n"]
        r = sh(prefix + ["apt-get", "install", "-y", "-q", apt])
        if r.returncode:   # 패키지 목록이 오래됐으면 update 후 한 번 더
            sh(prefix + ["apt-get", "update", "-q"], quiet=True)
            r = sh(prefix + ["apt-get", "install", "-y", "-q", apt])
        return r.returncode == 0
    return False


def pip(args: list[str]) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "-q"] + args
    r = sh(cmd, quiet=True)
    out = (r.stdout + r.stderr).lower()
    if r.returncode and "externally-managed" in out:
        r = sh(cmd + ["--break-system-packages"], quiet=True)
        out = (r.stdout + r.stderr).lower()
    if r.returncode and ("permission" in out or "access is denied" in out):
        r = sh(cmd + ["--user"], quiet=True)
    if r.returncode:
        print("    " + "\n    ".join((r.stdout + r.stderr).strip().splitlines()[-6:]))
    return r.returncode == 0


# ───────── 단계 ─────────
def missing_modules() -> list[str]:
    importlib.invalidate_caches()
    return [m for m in PY_MODULES if importlib.util.find_spec(m) is None]


def uv_cmd() -> list[str] | None:
    if importlib.util.find_spec("uv") is not None:
        return [sys.executable, "-m", "uv"]
    u = exe("uv")
    return [u] if u else None


def mcp_exe() -> str | None:
    hit = find_tool("ltspice-mcp")
    if hit:
        return hit
    u = uv_cmd()
    if u and not DRY:
        r = subprocess.run(u + ["tool", "dir", "--bin"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and r.stdout.strip():
            p = Path(r.stdout.strip()) / ("ltspice-mcp.exe" if WIN else "ltspice-mcp")
            if p.exists():
                return str(p)
    return None


def claude_desktop_config() -> Path | None:
    if WIN:
        d = Path(os.environ.get("APPDATA", USER_ROOT / "AppData/Roaming")) / "Claude"
    elif MAC:
        d = USER_ROOT / "Library/Application Support/Claude"
    else:
        return None
    return d / "claude_desktop_config.json" if d.exists() else None


def codex_present() -> bool:
    return bool(exe("codex")) or (USER_ROOT / ".codex").exists()


def claude_code() -> str | None:
    return exe("claude")


def mcp_registered_claude_code() -> bool:
    c = claude_code()
    return bool(c) and subprocess.run([c, "mcp", "get", "ltspice"], capture_output=True).returncode == 0


def mcp_registered_codex() -> bool:
    cfg = USER_ROOT / ".codex/config.toml"
    return cfg.exists() and "[mcp_servers.ltspice]" in cfg.read_text(encoding="utf-8", errors="replace")


def mcp_registered_desktop() -> bool:
    cfg = claude_desktop_config()
    if not cfg or not cfg.exists():
        return False
    try:
        return "ltspice" in (json.loads(cfg.read_text(encoding="utf-8") or "{}").get("mcpServers") or {})
    except json.JSONDecodeError:
        return False


def plugin_installed() -> bool:
    c = claude_code()
    if not c:
        return False
    r = subprocess.run([c, "plugin", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return f"{PLUGIN}@{MARKET}" in r.stdout


SKILL_ROOT: Path | None = None


def codex_skills_dir() -> Path:
    return SKILL_ROOT or USER_ROOT / ".agents/skills"


def codex_skills_installed() -> bool:
    for name in SKILL_NAMES:
        for source in (SKILLS_DIR / name).rglob("*"):
            if not source.is_file() or any(part in ("__pycache__", "build", "evals") for part in source.parts) or source.suffix == ".pyc":
                continue
            target = codex_skills_dir() / name / source.relative_to(SKILLS_DIR / name)
            if not target.is_file() or source.read_bytes() != target.read_bytes():
                return False
    return True


# ───────── 설치 동작 ─────────
def do_python() -> bool:
    return pip(["-r", str(REQUIREMENTS)]) and not missing_modules()


def do_uv_mcp() -> bool:
    if not uv_cmd() and not pip(["uv"]):
        return False
    u = uv_cmd() or [sys.executable, "-m", "uv"]
    sh(u + ["tool", "install", "ltspice-mcp"])
    return DRY or mcp_exe() is not None


def do_register_claude_code() -> bool:
    path = mcp_exe() or "ltspice-mcp"
    return sh([claude_code(), "mcp", "add", "--scope", "user", "ltspice", "--", path]).returncode == 0


def do_register_codex() -> bool:
    path = (mcp_exe() or "ltspice-mcp").replace("\\", "/")
    cfg = USER_ROOT / ".codex/config.toml"
    print(f"  + {cfg}에 [mcp_servers.ltspice] 추가")
    if DRY:
        return True
    cfg.parent.mkdir(parents=True, exist_ok=True)
    old = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    cfg.write_text(old.rstrip("\n") + ("\n\n" if old.strip() else "") +
                   f'[mcp_servers.ltspice]\ncommand = "{path}"\nargs = []\n', encoding="utf-8")
    return True


def do_register_desktop() -> bool:
    cfg = claude_desktop_config()
    path = (mcp_exe() or "ltspice-mcp").replace("\\", "/")
    print(f"  + {cfg}에 mcpServers.ltspice 추가 (원본은 .bak으로 남김)")
    if DRY or cfg is None:
        return cfg is not None
    text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        print("  ✗ 설정 파일이 올바른 JSON이 아님 — 손으로 고친 뒤 다시 돌린다")
        return False
    bak = cfg.with_suffix(".json.bak")
    if text and not bak.exists():
        bak.write_text(text, encoding="utf-8")
    data.setdefault("mcpServers", {})["ltspice"] = {"command": path, "args": []}
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def do_plugin() -> bool:
    c = claude_code()
    r = sh([c, "plugin", "marketplace", "add", REPO])
    if r.returncode and "already" not in (r.stdout + r.stderr).lower():
        sh([c, "plugin", "marketplace", "update", MARKET])
    return sh([c, "plugin", "install", f"{PLUGIN}@{MARKET}"]).returncode == 0


def do_codex_skills() -> bool:
    dst_root = codex_skills_dir()
    print(f"  + {SKILLS_DIR} → {dst_root}")
    if DRY:
        return True
    dst_root.mkdir(parents=True, exist_ok=True)
    for n in SKILL_NAMES:
        src, dst = SKILLS_DIR / n, dst_root / n
        if not (src / "SKILL.md").exists():
            print(f"  ✗ {src} 없음")
            return False
        if dst.resolve() == src.resolve():
            continue
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        elif getattr(dst, "is_junction", lambda: False)():
            raise RuntimeError(f"{dst}는 다른 폴더의 junction이다 — 명시적인 --skill-root를 사용한다")
        # 기존 설치에 사용자가 추가한 파일을 지우지 않는다.
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "build", "evals"))
    return True


def selected_agent(requested: str, environ: dict | None = None) -> str:
    """현재 호스트의 세션 신호만 사용한다. 앱 설치 여부는 호스트 신호가 아니다."""
    if requested != "auto":
        return requested
    env = os.environ if environ is None else environ
    codex = bool(env.get("CODEX_THREAD_ID") or env.get("CODEX_SANDBOX") or env.get("CODEX_CI"))
    claude = bool(env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT"))
    if codex != claude:
        return "codex" if codex else "claude"
    raise ValueError("현재 AI를 구별할 수 없음 — --agent codex 또는 --agent claude를 지정한다 (두 앱 설치는 --agent all)")


# (이름, 필수, 대상인지, 이미 됐는지, 설치)
def steps(a) -> list[tuple]:
    lt = not a.no_ltspice and (WIN or MAC)
    reg = not a.deps_only
    use_codex = a.agent in ("codex", "all")
    use_claude = a.agent in ("claude", "all")
    has_mcp_client = lambda: (use_claude and (bool(claude_code()) or claude_desktop_config() is not None)) or use_codex  # noqa: E731
    plan = [
        ("파이썬 패키지", True, True, lambda: not missing_modules(), do_python),
        ("pandoc", True, True, lambda: bool(find_tool("pandoc")),
         lambda: pkg_install("JohnMacFarlane.Pandoc", brew="pandoc", apt="pandoc")),
        ("LTspice", False, lt, lambda: bool(find_tool("ltspice")),
         lambda: pkg_install("AnalogDevices.LTspice", cask="ltspice")),
        ("ngspice", False, MAC or LINUX, lambda: bool(find_tool("ngspice")),
         lambda: pkg_install(brew="ngspice", apt="ngspice")),
        ("pdftotext (선택)", False, MAC or LINUX, lambda: bool(find_tool("pdftotext")),
         lambda: pkg_install(brew="poppler", apt="poppler-utils")),
        ("LibreOffice (미리보기)", False, a.preview, lambda: bool(find_tool("soffice")) and (not LINUX or any(
            Path(d, "libswlo.so").exists() for d in ("/usr/lib/libreoffice/program", "/opt/libreoffice/program"))),   # Linux: Writer 없이 core만 깔린 경우
         lambda: pkg_install("TheDocumentFoundation.LibreOffice", cask="libreoffice", apt="libreoffice-writer")),
        ("LTspice MCP (uv, ltspice-mcp)", False, reg and lt and has_mcp_client(), lambda: mcp_exe() is not None, do_uv_mcp),
        ("MCP 등록: Claude Code", False, reg and lt and use_claude and bool(claude_code()), mcp_registered_claude_code, do_register_claude_code),
        ("MCP 등록: Codex", False, reg and lt and use_codex, mcp_registered_codex, do_register_codex),
        ("MCP 등록: Claude 앱", False, reg and lt and use_claude and claude_desktop_config() is not None, mcp_registered_desktop, do_register_desktop),
        ("스킬: Claude Code 플러그인", True, reg and use_claude and bool(claude_code()),
         (lambda: False) if a.skills_only else plugin_installed, do_plugin),
        ("스킬: Codex (~/.agents/skills)", True, reg and use_codex, codex_skills_installed, do_codex_skills),
    ]
    return [step for step in plan if step[0].startswith("스킬:")] if a.skills_only else plan


def main():
    global DRY, SKILL_ROOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--yes", "-y", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-ltspice", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--deps-only", action="store_true")
    ap.add_argument("--agent", choices=["auto", "codex", "claude", "all"], default="auto",
                    help="설치·점검 대상 AI. auto는 현재 세션 신호로 판단")
    ap.add_argument("--skills-only", action="store_true", help="선택한 AI의 스킬만 설치/갱신 (패키지·MCP 변경 없음)")
    ap.add_argument("--skill-root", type=Path, help="Codex 스킬 설치 폴더 (기본 ~/.agents/skills)")
    a = ap.parse_args()
    if a.skills_only and a.deps_only:
        ap.error("--skills-only와 --deps-only는 함께 쓸 수 없음")
    try:
        a.agent = selected_agent(a.agent)
    except ValueError as error:
        ap.error(str(error))
    SKILL_ROOT = a.skill_root.resolve() if a.skill_root else None
    DRY = a.dry_run

    todo = []
    print(f"[점검] {a.agent}, {sys.platform}, Python {sys.version.split()[0]} ({sys.executable})")
    for name, required, applies, done, install in steps(a):
        if not applies:
            continue
        ok = done()
        print(f"  {'✓' if ok else ('✗' if required else '·')} {name}{'' if ok else ' — 없음'}")
        if not ok:
            todo.append((name, required, done, install))
    if a.check or not todo:
        missing_required = [n for n, r, _, _ in todo if r]
        print("ok: 모두 준비됨" if not todo else f"없음: {', '.join(n for n, *_ in todo)}")
        sys.exit(1 if missing_required else 0)

    if not (a.yes or a.dry_run):
        if not sys.stdin.isatty():
            sys.exit("설치하려면 --yes를 붙여 다시 실행한다")
        if input(f"\n위 {len(todo)}개를 설치할까? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("취소함")

    results = []
    for name, required, done, install in todo:
        print(f"\n[설치] {name}")
        try:
            ok = bool(install())
        except Exception as e:   # 한 단계가 실패해도 나머지는 계속한다
            print(f"  ✗ {e}")
            ok = False
        ok = ok and (DRY or done())
        results.append((name, required, ok))
        print(f"  {'✓ 완료' if ok else '✗ 실패'}")

    print("\n[결과]")
    for name, required, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}{'' if ok or not required else ' (필수)'}")
    print("\n다음:")
    print(f"  - {a.agent}에서 스킬 변경이 보이지 않으면 새 세션을 시작한다")
    if a.agent in ("claude", "all") and claude_desktop_config() is not None:
        print("  - Claude 앱은 트레이에서 완전히 종료한 뒤 다시 연다")
    if WIN:
        print("  - 새로 깐 프로그램이 PATH에 안 보이면 터미널을 새로 연다 (스크립트는 설치 위치를 직접 찾는다)")
    sys.exit(1 if any(r and not ok for _, r, ok in results) else 0)


if __name__ == "__main__":
    main()
