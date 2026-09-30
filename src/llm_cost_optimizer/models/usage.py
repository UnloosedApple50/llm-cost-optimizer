"""Usage tracking and cost analysis models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of LLM tasks with different quality requirements."""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CHAT = "chat"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    ANALYSIS = "analysis"
    CREATIVE_WRITING = "creative_writing"
    FUNCTION_CALLING = "function_calling"
    EMBEDDING = "embedding"
    VISION = "vision"


class LLMUsage(BaseModel):
    """Raw usage data from an LLM API call."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int = 0
    latency_ms: Optional[float] = None
    task_type: TaskType = TaskType.CHAT
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: str = "unknown"
    success: bool = True
    error: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if not self.total_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


class UsageRecord(BaseModel):
    """A stored usage record with cost information."""

    id: Optional[int] = None
    usage: LLMUsage
    cost_usd: float = 0.0
    cost_per_1k_tokens: float = 0.0
    quality_score: Optional[float] = None  # 0-1, user-rated or estimated


class CostBreakdown(BaseModel):
    """Cost breakdown for a specific model or provider."""

    model: str
    provider: str
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_cost_per_call: float = 0.0
    avg_latency_ms: float = 0.0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ModelSuggestion(BaseModel):
    """A model recommendation with reasoning."""

    current_model: str
    suggested_model: str
    provider: str
    estimated_savings_pct: float
    estimated_savings_usd: float
    quality_impact: str  # "none", "minimal", "moderate", "significant"
    reasoning: str
    confidence: float  # 0-1


class OptimizationResult(BaseModel):
    """Complete optimization analysis result."""

    total_cost_usd: float
    total_calls: int
    total_tokens: int
    period_days: int
    breakdown_by_model: list[CostBreakdown]
    suggestions: list[ModelSuggestion]
    potential_monthly_savings: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
