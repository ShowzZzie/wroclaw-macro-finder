"""Vercel serverless-function entrypoint for the FastAPI API."""

import sys
from pathlib import Path

# src/ holds the installable app package; add it so
# ``from app.…`` imports resolve in Vercel's runtime.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.api import app  # noqa: E402, F401
