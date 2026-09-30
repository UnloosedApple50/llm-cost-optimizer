"""Pricing models for different LLM providers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PricingTier(str, Enum):
    """Pricing tier based on volume."""

    STANDARD = "standard"
    VOLUME = "volume"  # Discounted for high volume
    BATCH = "batch"  # 50% discount for batch API


class ModelPricing(BaseModel):
    """Pricing information for a specific model."""

    model: str
    provider: str
    input_per_1m_tokens: float  # USD per 1M input tokens
    output_per_1m_tokens: float  # USD per 1M output tokens
    context_window: int
    max_output_tokens: Optional[int] = None
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_json_mode: bool = False
    quality_score: float = 0.5  # 0-1, relative quality estimate
    speed_score: float = 0.5  # 0-1, relative speed estimate
    pricing_tier: PricingTier = PricingTier.STANDARD
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD for given token counts."""
        input_cost = (prompt_tokens / 1_000_000) * self.input_per_1m_tokens
        output_cost = (completion_tokens / 1_000_000) * self.output_per_1m_tokens
        return input_cost + output_cost

    def cost_per_1k_tokens(self, ratio: float = 0.5) -> float:
        """Average cost per 1K tokens at given input/output ratio."""
        input_cost = (ratio * self.input_per_1m_tokens) / 1000
        output_cost = ((1 - ratio) * self.output_per_1m_tokens) / 1000
        return input_cost + output_cost


class ProviderPricing(BaseModel):
    """All pricing for a provider."""

    provider: str
    models: list[ModelPricing]
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    def get_model(self, model_name: str) -> Optional[ModelPricing]:
        """Get pricing for a specific model."""
        for m in self.models:
            if m.model == model_name:
                return m
        return None

    def find_cheaper_alternatives(
        self,
        model_name: str,
        task_type: str = "general",
        min_quality: float = 0.3,
    ) -> list[ModelPricing]:
        """Find cheaper alternatives with acceptable quality."""
        current = self.get_model(model_name)
        if not current:
            return []

        alternatives = []
        for m in self.models:
            if m.model == model_name:
                continue
            if m.quality_score >= min_quality:
                if m.input_per_1m_tokens < current.input_per_1m_tokens:
                    alternatives.append(m)

        alternatives.sort(key=lambda m: m.input_per_1m_tokens + m.output_per_1m_tokens)
        return alternatives
