"""Price fetcher — automatically fetch latest pricing from provider APIs."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import httpx

from llm_cost_optimizer.models.pricing import ModelPricing, ProviderPricing, PricingTier
from llm_cost_optimizer.utils.logger import get_logger

logger = get_logger("price_fetcher")


class PriceFetcher:
    """Fetches and updates pricing data from provider APIs."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=30.0)
        self._last_fetch: Optional[datetime] = None

    async def close(self) -> None:
        """Close HTTP client."""
        await self._http.aclose()

    async def fetch_all(self) -> dict[str, ProviderPricing]:
        """Fetch pricing from all providers."""
        results = {}

        # Fetch from each provider
        tasks = [
            self._fetch_openai(),
            self._fetch_anthropic(),
            self._fetch_google(),
            self._fetch_ollama(),
            self._fetch_deepseek(),
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for provider, result in zip(["openai", "anthropic", "google", "ollama", "deepseek"], responses):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {provider} pricing: {result}")
            elif result is not None:
                results[provider] = result

        self._last_fetch = datetime.now(timezone.utc)
        return results

    async def _fetch_openai(self) -> Optional[ProviderPricing]:
        """Fetch OpenAI pricing from their API."""
        try:
            # OpenAI doesn't have a public pricing API, so we scrape their pricing page
            # For now, return None to use hardcoded values
            logger.info("OpenAI pricing: using hardcoded values (no public API)")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch OpenAI pricing: {e}")
            return None

    async def _fetch_anthropic(self) -> Optional[ProviderPricing]:
        """Fetch Anthropic pricing from their API."""
        try:
            # Anthropic doesn't have a public pricing API
            logger.info("Anthropic pricing: using hardcoded values (no public API)")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch Anthropic pricing: {e}")
            return None

    async def _fetch_google(self) -> Optional[ProviderPricing]:
        """Fetch Google Gemini pricing from their API."""
        try:
            # Google AI Studio API requires authentication
            logger.info("Google pricing: using hardcoded values (requires API key)")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch Google pricing: {e}")
            return None

    async def _fetch_ollama(self) -> Optional[ProviderPricing]:
        """Fetch Ollama models from local API."""
        try:
            response = await self._http.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("models", []):
                    models.append(ModelPricing(
                        model=model["name"],
                        provider="ollama",
                        input_per_1m_tokens=0.0,
                        output_per_1m_tokens=0.0,
                        context_window=model.get("context_length", 128000),
                        max_output_tokens=8192,
                        supports_function_calling=True,
                        quality_score=0.7,
                        speed_score=0.6,
                    ))
                logger.info(f"Ollama pricing: fetched {len(models)} models from local API")
                return ProviderPricing(provider="ollama", models=models)
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama pricing: {e}")
        return None

    async def _fetch_deepseek(self) -> Optional[ProviderPricing]:
        """Fetch DeepSeek pricing from their API."""
        try:
            # DeepSeek doesn't have a public pricing API
            logger.info("DeepSeek pricing: using hardcoded values (no public API)")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch DeepSeek pricing: {e}")
            return None

    async def save_to_file(self, pricing: dict[str, ProviderPricing], filepath: str = "data/pricing.json") -> None:
        """Save pricing data to JSON file."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        data = {}
        for provider, p in pricing.items():
            data[provider] = {
                "provider": p.provider,
                "last_updated": p.last_updated.isoformat(),
                "models": [
                    {
                        "model": m.model,
                        "provider": m.provider,
                        "input_per_1m_tokens": m.input_per_1m_tokens,
                        "output_per_1m_tokens": m.output_per_1m_tokens,
                        "context_window": m.context_window,
                        "max_output_tokens": m.max_output_tokens,
                        "supports_vision": m.supports_vision,
                        "supports_function_calling": m.supports_function_calling,
                        "supports_json_mode": m.supports_json_mode,
                        "quality_score": m.quality_score,
                        "speed_score": m.speed_score,
                        "pricing_tier": m.pricing_tier.value,
                    }
                    for m in p.models
                ],
            }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Pricing data saved to {filepath}")

    async def load_from_file(self, filepath: str = "data/pricing.json") -> Optional[dict[str, ProviderPricing]]:
        """Load pricing data from JSON file."""
        try:
            with open(filepath) as f:
                data = json.load(f)

            pricing = {}
            for provider, p_data in data.items():
                models = [
                    ModelPricing(
                        model=m["model"],
                        provider=m["provider"],
                        input_per_1m_tokens=m["input_per_1m_tokens"],
                        output_per_1m_tokens=m["output_per_1m_tokens"],
                        context_window=m["context_window"],
                        max_output_tokens=m.get("max_output_tokens"),
                        supports_vision=m.get("supports_vision", False),
                        supports_function_calling=m.get("supports_function_calling", False),
                        supports_json_mode=m.get("supports_json_mode", False),
                        quality_score=m.get("quality_score", 0.5),
                        speed_score=m.get("speed_score", 0.5),
                        pricing_tier=PricingTier(m.get("pricing_tier", "standard")),
                    )
                    for m in p_data["models"]
                ]
                pricing[provider] = ProviderPricing(
                    provider=provider,
                    models=models,
                    last_updated=datetime.fromisoformat(p_data["last_updated"]),
                )

            logger.info(f"Pricing data loaded from {filepath}")
            return pricing
        except FileNotFoundError:
            logger.warning(f"Pricing file not found: {filepath}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load pricing from file: {e}")
            return None
