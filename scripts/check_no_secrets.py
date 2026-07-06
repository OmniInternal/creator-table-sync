from __future__ import annotations

import re
import subprocess
import sys
from typing import Callable, Iterable

TOKEN_RE = re.compile(r"ntn_[A-Za-z0-9]{6,}")
URL_RE = re.compile(r"notion\.com")
HEX32_RE = re.compile(r"\b[0-9a-fA-F]{32}\b")

# Files that are allowed to mention these patterns.
# - ".env.example": documents the expected env var shape, no real values.
# - "scripts/check_no_secrets.py" and "tests/test_secret_guard.py": these are
#   the guard's own detection-logic/fixture files, so they legitimately
#   contain the literal patterns (regexes and dummy test fixtures) being
#   searched for elsewhere in the repo.
ALLOWLIST = {
    ".env.example",
    "scripts/check_no_secrets.py",
    "tests/test_secret_guard.py",
}


def find_violations(paths: Iterable[str], read_text: Callable[[str], str]):
    violations = []
    for path in paths:
        if any(path.endswith(a) for a in ALLOWLIST):
            continue
        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError):
            continue
        if TOKEN_RE.search(text):
            violations.append((path, "notion token"))
        elif URL_RE.search(text):
            violations.append((path, "notion.com url"))
        elif HEX32_RE.search(text):
            violations.append((path, "bare 32-hex id"))
    return violations


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    )
    return [p for p in out.stdout.splitlines() if p.strip()]


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main() -> int:
    violations = find_violations(_tracked_files(), _read)
    for path, reason in violations:
        print(f"SECRET GUARD: {path}: {reason}", file=sys.stderr)
    if violations:
        print(f"{len(violations)} violation(s) found", file=sys.stderr)
        return 1
    print("secret guard: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
