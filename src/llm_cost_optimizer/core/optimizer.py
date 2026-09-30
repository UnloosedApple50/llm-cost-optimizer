"""Core cost optimization engine."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from llm_cost_optimizer.models.usage import (
    LLMUsage,
    UsageRecord,
    CostBreakdown,
    OptimizationResult,
    ModelSuggestion,
    TaskType,
)
from llm_cost_optimizer.models.pricing import ModelPricing, ProviderPricing


class CostOptimizer:
    """
    Core engine for analyzing LLM usage and suggesting cost optimizations.
    """

    def __init__(self, pricing: dict[str, ProviderPricing]) -> None:
        self._pricing = pricing
        self._records: list[UsageRecord] = []

    def add_record(self, record: UsageRecord) -> None:
        """Add a usage record for analysis."""
        self._records.append(record)

    def add_usage(self, usage: LLMUsage, cost_usd: float) -> None:
        """Add a raw usage entry."""
        record = UsageRecord(
            usage=usage,
            cost_usd=cost_usd,
            cost_per_1k_tokens=(cost_usd / usage.total_tokens * 1000) if usage.total_tokens > 0 else 0,
        )
        self._records.append(record)

    def get_breakdown_by_model(
        self,
        days: int = 30,
    ) -> list[CostBreakdown]:
        """Get cost breakdown grouped by model."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [r for r in self._records if r.usage.timestamp >= cutoff]

        groups: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in recent:
            groups[r.usage.model].append(r)

        breakdowns = []
        for model, records in groups.items():
            total_cost = sum(r.cost_usd for r in records)
            total_prompt = sum(r.usage.prompt_tokens for r in records)
            total_completion = sum(r.usage.completion_tokens for r in records)
            total_tokens = sum(r.usage.total_tokens for r in records)
            latencies = [r.usage.latency_ms for r in records if r.usage.latency_ms is not None]

            provider = records[0].usage.provider

            breakdowns.append(CostBreakdown(
                model=model,
                provider=provider,
                total_calls=len(records),
                total_prompt_tokens=total_prompt,
                total_completion_tokens=total_completion,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                avg_cost_per_call=total_cost / len(records) if records else 0,
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
                period_start=min(r.usage.timestamp for r in records),
                period_end=max(r.usage.timestamp for r in records),
            ))

        breakdowns.sort(key=lambda b: b.total_cost_usd, reverse=True)
        return breakdowns

    def analyze(
        self,
        days: int = 30,
        min_quality_threshold: float = 0.3,
    ) -> OptimizationResult:
        """
        Run full optimization analysis.

        Args:
            days: Analysis period in days.
            min_quality_threshold: Minimum acceptable quality score (0-1).

        Returns:
            OptimizationResult with breakdowns and suggestions.
        """
        breakdowns = self.get_breakdown_by_model(days)
        total_cost = sum(b.total_cost_usd for b in breakdowns)
        total_calls = sum(b.total_calls for b in breakdowns)
        total_tokens = sum(b.total_tokens for b in breakdowns)

        suggestions = self._generate_suggestions(breakdowns, min_quality_threshold)
        potential_savings = sum(s.estimated_savings_usd for s in suggestions)

        return OptimizationResult(
            total_cost_usd=total_cost,
            total_calls=total_calls,
            total_tokens=total_tokens,
            period_days=days,
            breakdown_by_model=breakdowns,
            suggestions=suggestions,
            potential_monthly_savings=potential_savings,
        )

    def _generate_suggestions(
        self,
        breakdowns: list[CostBreakdown],
        min_quality: float,
    ) -> list[ModelSuggestion]:
        """Generate cost-saving suggestions based on usage patterns."""
        suggestions = []

        for breakdown in breakdowns:
            provider_pricing = self._pricing.get(breakdown.provider)
            if not provider_pricing:
                continue

            current_pricing = provider_pricing.get_model(breakdown.model)
            if not current_pricing:
                continue

            # Find cheaper alternatives
            alternatives = provider_pricing.find_cheaper_alternatives(
                breakdown.model,
                min_quality=min_quality,
            )

            for alt in alternatives[:2]:  # Top 2 alternatives
                # Estimate savings
                est_cost = alt.calculate_cost(
                    breakdown.total_prompt_tokens,
                    breakdown.total_completion_tokens,
                )
                savings = breakdown.total_cost_usd - est_cost
                savings_pct = (savings / breakdown.total_cost_usd * 100) if breakdown.total_cost_usd > 0 else 0

                if savings > 0:
                    quality_diff = current_pricing.quality_score - alt.quality_score
                    if quality_diff <= 0.1:
                        quality_impact = "none"
                    elif quality_diff <= 0.2:
                        quality_impact = "minimal"
                    elif quality_diff <= 0.3:
                        quality_impact = "moderate"
                    else:
                        quality_impact = "significant"

                    suggestions.append(ModelSuggestion(
                        current_model=breakdown.model,
                        suggested_model=alt.model,
                        provider=alt.provider,
                        estimated_savings_pct=savings_pct,
                        estimated_savings_usd=savings,
                        quality_impact=quality_impact,
                        reasoning=(
                            f"Switching from {breakdown.model} to {alt.model} "
                            f"could save ${savings:.2f}/month ({savings_pct:.1f}% reduction) "
                            f"with {quality_impact} quality impact."
                        ),
                        confidence=max(0.5, 1.0 - quality_diff),
                    ))

        suggestions.sort(key=lambda s: s.estimated_savings_usd, reverse=True)
        return suggestions

    def suggest_model_for_task(
        self,
        task_type: TaskType,
        budget_usd: Optional[float] = None,
        min_quality: float = 0.5,
    ) -> list[ModelPricing]:
        """
        Suggest the best model for a specific task type.

        Args:
            task_type: Type of task to optimize for.
            budget_usd: Optional budget constraint.
            min_quality: Minimum quality threshold.

        Returns:
            List of suitable models sorted by value (quality/cost).
        """
        all_models = []
        for provider_pricing in self._pricing.values():
            for model in provider_pricing.models:
                if model.quality_score >= min_quality:
                    if budget_usd is None or model.cost_per_1k_tokens() <= budget_usd:
                        all_models.append(model)

        # Sort by value score (quality / cost)
        all_models.sort(
            key=lambda m: m.quality_score / (m.cost_per_1k_tokens() + 0.0001),
            reverse=True,
        )
        return all_models
