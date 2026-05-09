"""Build the Vite SPA into `public/` for Vercel static serving alongside FastAPI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    frontend = root / "frontend"
    dist = frontend / "dist"
    public = root / "public"

    subprocess.run(["npm", "ci"], cwd=frontend, check=True)
    subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)

    if not dist.is_dir():
        sys.exit("frontend/dist missing after npm run build")

    if public.exists():
        shutil.rmtree(public)
    shutil.copytree(dist, public)


if __name__ == "__main__":
    main()
