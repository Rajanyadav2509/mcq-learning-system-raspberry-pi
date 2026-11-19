"""Vercel serverless entry point for the MCQ admin panel.

The Flask app lives in server/ (unchanged). This file only makes it
importable as a Vercel Python serverless function — no app code is
modified here.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from app import app  # noqa: E402,F401  (Vercel looks for `app`)
