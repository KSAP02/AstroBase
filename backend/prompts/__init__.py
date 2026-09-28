"""Prompt templates live as .md files in this folder so they can be read and edited as text.

Bump PROMPT_VERSION whenever a prompt's wording changes; every saved evaluation records it.
"""

from pathlib import Path

PROMPT_VERSION = "v2"  # v2: "partial" also requires specific evidence (v1 let vague claims earn partial)

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Return the text of prompts/<name>.md."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
