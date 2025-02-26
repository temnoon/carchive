"""
Utility functions shared across modules: logging, text cleaning, etc.
"""

import re

def contains_latex(text: str) -> bool:
    """
    Simple check if text has LaTeX patterns, e.g., $...$ or $$...$$.
    Expand logic as needed.
    """
    return "$" in text  # or use a regex for a more robust check

def clean_latex(text: str) -> str:
    """
    Example function to try “repairing” or normalizing LaTeX markers.
    Currently a placeholder—expand as needed.
    """
    # Naive example: remove double spaces or fix mismatched $.
    # You can do more complicated text transformations here.
    return text.strip()
