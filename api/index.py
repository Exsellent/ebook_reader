"""
Vercel entry point for the ebook_reader Flask app.

Vercel's @vercel/python builder looks for a variable named `app`
in this file that is a WSGI callable.

Layout on disk (repo root):
  api/
    index.py        ← this file
  templates/
    index.html
  app.py            ← Flask app with all routes
  requirements.txt
  vercel.json
"""

import os
import sys

# Make the repo root importable so `from app import app` works.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Import the Flask instance.
# app.py must expose its Flask object as `app`.
from app import app  # noqa: F401  ← Vercel picks up this name

# ── nothing else needed ──
# Vercel calls  app(environ, start_response)  directly.
