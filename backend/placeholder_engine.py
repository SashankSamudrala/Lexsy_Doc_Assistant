# backend/placeholder_engine.py
import re

def normalize_key(key: str) -> str:
    """
    Minimal normalization — keep words separated.
    Only strip brackets and trim whitespace.
    Do NOT remove symbols like $ or underscores.
    """
    return key.strip().strip("[]").strip()
