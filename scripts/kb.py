from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def find_kb_home() -> Path:
    existing = os.environ.get("KB_HOME")
    if existing:
        return Path(existing)

    candidates: list[Path] = []
    home = Path.home()
    candidates.append(home / ".ai-knowledge-base")

    users_dir = Path("C:/Users")
    if users_dir.exists():
        for child in users_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name in {"All Users", "Default", "Default User", "Public"}:
                continue
            candidates.append(child / ".ai-knowledge-base")

    for candidate in candidates:
        if (candidate / "index.md").exists():
            return candidate

    return home / ".ai-knowledge-base"


def main() -> int:
    plugin_root = Path(__file__).resolve().parents[1]
    kb_script = plugin_root / "tools" / "kb.py"
    if not kb_script.exists():
        raise FileNotFoundError(f"Bundled kb.py not found: {kb_script}")

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["KB_HOME"] = str(find_kb_home())

    cmd = [sys.executable, str(kb_script), *sys.argv[1:]]
    completed = subprocess.run(cmd, env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
