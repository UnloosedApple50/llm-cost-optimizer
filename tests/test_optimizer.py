"""Tests for the cost optimizer core engine."""

import pytest
from datetime import datetime, timedelta

from llm_cost_optimizer.core.optimizer import CostOptimizer
from llm_cost_optimizer.core.default_pricing import ALL_PRICING
from llm_cost_optimizer.models.usage import LLMUsage, UsageRecord, TaskType
from llm_cost_optimizer.models.pricing import ModelPricing, ProviderPricing


@pytest.fixture
def optimizer():
    return CostOptimizer(ALL_PRICING)


@pytest.fixture
def sample_usage():
    return LLMUsage(
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=500,
        provider="openai",
        task_type=TaskType.CHAT,
    )


class TestCostOptimizer:
    """Test suite for CostOptimizer."""

    def test_add_usage(self, optimizer, sample_usage):
        optimizer.add_usage(sample_usage, cost_usd=0.002)
        assert len(optimizer._records) == 1

    def test_get_breakdown_empty(self, optimizer):
        breakdowns = optimizer.get_breakdown_by_model()
        assert breakdowns == []

    def test_get_breakdown_with_data(self, optimizer, sample_usage):
        optimizer.add_usage(sample_usage, cost_usd=0.002)
        breakdowns = optimizer.get_breakdown_by_model()
        assert len(breakdowns) == 1
        assert breakdowns[0].model == "gpt-4o"
        assert breakdowns[0].total_calls == 1

    def test_analyze_empty(self, optimizer):
        result = optimizer.analyze()
        assert result.total_cost_usd == 0
        assert result.total_calls == 0
        assert result.suggestions == []

    def test_analyze_with_data(self, optimizer, sample_usage):
        optimizer.add_usage(sample_usage, cost_usd=0.002)
        result = optimizer.analyze()
        assert result.total_cost_usd == 0.002
        assert result.total_calls == 1
        assert result.total_tokens == 1500

    def test_suggest_model_for_task(self, optimizer):
        models = optimizer.suggest_model_for_task(TaskType.CHAT)
        assert len(models) > 0
        # Should be sorted by value (quality/cost) — free models first
        def value_score(m):
            return m.quality_score / (m.cost_per_1k_tokens() + 0.0001)
        assert value_score(models[0]) >= value_score(models[-1])

    def test_suggest_model_with_budget(self, optimizer):
        models = optimizer.suggest_model_for_task(TaskType.CHAT, budget_usd=0.001)
        for m in models:
            assert m.cost_per_1k_tokens() <= 0.001

    def test_suggest_model_with_min_quality(self, optimizer):
        models = optimizer.suggest_model_for_task(TaskType.CHAT, min_quality=0.8)
        for m in models:
            assert m.quality_score >= 0.8


class TestModelPricing:
    """Test suite for ModelPricing."""

    def test_calculate_cost(self):
        pricing = ModelPricing(
            model="test-model",
            provider="test",
            input_per_1m_tokens=1.0,
            output_per_1m_tokens=2.0,
            context_window=1000,
        )
        cost = pricing.calculate_cost(1_000_000, 1_000_000)
        assert cost == 3.0  # $1 + $2

    def test_cost_per_1k_tokens(self):
        pricing = ModelPricing(
            model="test-model",
            provider="test",
            input_per_1m_tokens=1.0,
            output_per_1m_tokens=1.0,
            context_window=1000,
        )
        cost = pricing.cost_per_1k_tokens(ratio=0.5)
        assert cost == 0.001  # $1/1M * 0.5 + $1/1M * 0.5 = $1/1K


class TestProviderPricing:
    """Test suite for ProviderPricing."""

    def test_get_model(self):
        pricing = ALL_PRICING["openai"]
        model = pricing.get_model("gpt-4o")
        assert model is not None
        assert model.model == "gpt-4o"

    def test_get_model_not_found(self):
        pricing = ALL_PRICING["openai"]
        model = pricing.get_model("nonexistent")
        assert model is None

    def test_find_cheaper_alternatives(self):
        pricing = ALL_PRICING["openai"]
        alternatives = pricing.find_cheaper_alternatives("gpt-4o", min_quality=0.5)
        assert len(alternatives) > 0
        # All alternatives should be cheaper
        current = pricing.get_model("gpt-4o")
        for alt in alternatives:
            assert alt.input_per_1m_tokens < current.input_per_1m_tokens
