"""Utility functions and helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_api_key(provider: str) -> Optional[str]:
    """Get API key from environment variable."""
    env_var = f"{provider.upper()}_API_KEY"
    return os.environ.get(env_var)


def ensure_data_dir() -> Path:
    """Ensure data directory exists."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir


def format_cost(cost_usd: float) -> str:
    """Format cost in USD for display."""
    if cost_usd == 0:
        return "Free"
    if cost_usd < 0.01:
        return f"${cost_usd:.6f}"
    if cost_usd < 1:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"


def format_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)
