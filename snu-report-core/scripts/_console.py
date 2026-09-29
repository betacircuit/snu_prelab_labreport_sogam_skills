"""Windows 콘솔·파이프(cp949)에서 ✓, 한글 출력이 UnicodeEncodeError로 죽지 않게 UTF-8로 맞춘다. import만 하면 된다."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
