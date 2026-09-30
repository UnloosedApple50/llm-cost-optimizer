# LLM Cost Optimizer

> AI-powered LLM cost optimization tool — analyzes API costs and suggests the best model for each task (cost vs quality).

## Features

- 📊 **Cost Analysis** — Track and analyze your LLM API spending across providers
- 💡 **Smart Suggestions** — Get actionable recommendations to reduce costs
- 🔍 **Model Comparison** — Compare models side by side (price, quality, speed)
- 💰 **Budget Optimization** — Find the best model within your budget
- 📈 **Usage Tracking** — Log and track your LLM usage over time
- 🏠 **Local Models** — Includes Ollama pricing (free) for cost comparison

## Supported Providers

| Provider | Models |
|----------|--------|
| OpenAI | GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo, o1-preview, o1-mini |
| Anthropic | Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus, Claude 3 Haiku |
| Google | Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 1.5 Flash 8B |
| Ollama | Llama 3.1, Qwen 2.5 Coder, DeepSeek Coder, Mistral, CodeLlama |
| DeepSeek | DeepSeek Chat, DeepSeek Coder |

## Installation

```bash
pip install llm-cost-optimizer
```

Or install from source:

```bash
git clone https://github.com/UnloosedApple50/llm-cost-optimizer.git
cd llm-cost-optimizer
pip install -e ".[dev]"
```

## Quick Start

### Analyze your costs

```bash
llm-cost analyze --days 30
```

### Get model suggestions for a task

```bash
llm-cost suggest --task code_generation --budget 0.001
```

### Compare models

```bash
llm-cost compare gpt-4o,gpt-4o-mini,claude-3-5-sonnet-20241022
```

### Log usage

```bash
llm-cost log gpt-4o 1000 500 --provider openai --task chat
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `llm-cost analyze` | Analyze usage and suggest optimizations |
| `llm-cost suggest` | Suggest best model for a task |
| `llm-cost compare` | Compare multiple models |
| `llm-cost log` | Log a usage entry |

## Task Types

- `chat` — General conversation
- `code_generation` — Writing code
- `code_review` — Reviewing code
- `summarization` — Summarizing text
- `translation` — Translating text
- `analysis` — Data analysis
- `creative_writing` — Creative content
- `function_calling` — Tool/function use
- `embedding` — Text embeddings
- `vision` — Image understanding

## Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite+aiosqlite:///./data/costs.db
LOG_LEVEL=INFO
```

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=llm_cost_optimizer --cov-report=html

# Lint
ruff check src tests

# Type check
mypy src
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.
