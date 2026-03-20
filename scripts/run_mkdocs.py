from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
WRITING_INDEX_SCRIPT = ROOT / "scripts" / "generate_writing_index.py"


def ensure_last_build() -> None:
    if not os.environ.get("LAST_BUILD"):
        os.environ["LAST_BUILD"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )


def run() -> None:
    ensure_last_build()

    subprocess.run(
        [sys.executable, str(WRITING_INDEX_SCRIPT)],
        cwd=ROOT,
        check=True,
    )

    mkdocs_args = sys.argv[1:] if len(sys.argv) > 1 else ["serve"]
    subprocess.run(
        ["mkdocs", *mkdocs_args],
        cwd=ROOT,
        check=True,
        env=os.environ.copy(),
    )


if __name__ == "__main__":
    run()
