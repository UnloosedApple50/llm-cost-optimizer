"""CLI interface for LLM Cost Optimizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track

from llm_cost_optimizer.core.optimizer import CostOptimizer
from llm_cost_optimizer.core.default_pricing import ALL_PRICING
from llm_cost_optimizer.models.usage import LLMUsage, TaskType
from llm_cost_optimizer.models.pricing import ModelPricing

app = typer.Typer(
    name="llm-cost",
    help="AI-powered LLM cost optimization tool",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    days: int = typer.Option(30, "--days", "-d", help="Analysis period in days"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (JSON)"),
    min_quality: float = typer.Option(0.3, "--min-quality", "-q", help="Minimum quality threshold (0-1)"),
):
    """Analyze LLM usage and suggest cost optimizations."""
    console.print(Panel.fit("[bold blue]LLM Cost Optimizer[/bold blue]"))

    optimizer = CostOptimizer(ALL_PRICING)

    # Load usage data if available
    data_file = Path("data/usage.jsonl")
    if data_file.exists():
        with open(data_file) as f:
            for line in f:
                record = json.loads(line)
                usage = LLMUsage(**record)
                optimizer.add_usage(usage, cost_usd=0)  # Cost calculated from pricing
        console.print(f"[green]Loaded usage data from {data_file}[/green]")
    else:
        console.print("[yellow]No usage data found. Use 'llm-cost log' to track usage.[/yellow]")

    result = optimizer.analyze(days=days, min_quality_threshold=min_quality)

    # Display results
    console.print(f"\n[bold]Analysis Results ({days} days)[/bold]")
    console.print(f"Total cost: [bold green]${result.total_cost_usd:.4f}[/bold green]")
    console.print(f"Total calls: {result.total_calls}")
    console.print(f"Total tokens: {result.total_tokens:,}")

    if result.breakdown_by_model:
        table = Table(title="Cost by Model")
        table.add_column("Model", style="cyan")
        table.add_column("Provider", style="magenta")
        table.add_column("Calls", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="green")

        for b in result.breakdown_by_model:
            table.add_row(
                b.model,
                b.provider,
                str(b.total_calls),
                f"{b.total_tokens:,}",
                f"${b.total_cost_usd:.4f}",
            )
        console.print(table)

    if result.suggestions:
        console.print(f"\n[bold yellow]💡 Suggestions (Potential savings: ${result.potential_monthly_savings:.2f}/mo)[/bold yellow]")
        for i, s in enumerate(result.suggestions, 1):
            console.print(f"\n[bold]{i}. Switch {s.current_model} → {s.suggested_model}[/bold]")
            console.print(f"   Savings: [green]${s.estimated_savings_usd:.2f}/mo ({s.estimated_savings_pct:.1f}%)[/green]")
            console.print(f"   Quality impact: {s.quality_impact}")
            console.print(f"   Reasoning: {s.reasoning}")
    else:
        console.print("\n[green]✅ No optimization suggestions — you're already using cost-effective models![/green]")

    if output:
        with open(output, "w") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        console.print(f"\n[green]Results saved to {output}[/green]")


@app.command()
def suggest(
    task: str = typer.Option("chat", "--task", "-t", help="Task type (chat, code_generation, etc.)"),
    budget: Optional[float] = typer.Option(None, "--budget", "-b", help="Budget per 1K tokens (USD)"),
    min_quality: float = typer.Option(0.5, "--min-quality", "-q", help="Minimum quality threshold"),
):
    """Suggest the best model for a specific task."""
    console.print(Panel.fit("[bold blue]Model Suggestion[/bold blue]"))

    try:
        task_type = TaskType(task)
    except ValueError:
        console.print(f"[red]Invalid task type. Choose from: {', '.join(t.value for t in TaskType)}[/red]")
        raise typer.Exit(1)

    optimizer = CostOptimizer(ALL_PRICING)
    models = optimizer.suggest_model_for_task(task_type, budget_usd=budget, min_quality=min_quality)

    if not models:
        console.print("[yellow]No models match your criteria.[/yellow]")
        return

    table = Table(title=f"Best models for {task.value}")
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Quality", justify="right")
    table.add_column("Speed", justify="right")
    table.add_column("Cost/1K tokens", justify="right", style="green")
    table.add_column("Context", justify="right")

    for m in models[:10]:
        table.add_row(
            m.model,
            m.provider,
            f"{m.quality_score:.0%}",
            f"{m.speed_score:.0%}",
            f"${m.cost_per_1k_tokens():.4f}" if m.cost_per_1k_tokens() > 0 else "Free",
            f"{m.context_window:,}",
        )

    console.print(table)


@app.command()
def compare(
    models: str = typer.Argument(..., help="Comma-separated model names to compare"),
):
    """Compare multiple models side by side."""
    model_names = [m.strip() for m in models.split(",")]

    console.print(Panel.fit("[bold blue]Model Comparison[/bold blue]"))

    table = Table()
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Input $/1M", justify="right")
    table.add_column("Output $/1M", justify="right")
    table.add_column("Context", justify="right")
    table.add_column("Quality", justify="right")
    table.add_column("Vision", justify="center")
    table.add_column("Functions", justify="center")

    for name in model_names:
        found = False
        for provider_pricing in ALL_PRICING.values():
            m = provider_pricing.get_model(name)
            if m:
                table.add_row(
                    m.model,
                    m.provider,
                    f"${m.input_per_1m_tokens:.2f}",
                    f"${m.output_per_1m_tokens:.2f}",
                    f"{m.context_window:,}",
                    f"{m.quality_score:.0%}",
                    "✅" if m.supports_vision else "❌",
                    "✅" if m.supports_function_calling else "❌",
                )
                found = True
                break
        if not found:
            table.add_row(name, "[red]Not found[/red]", "", "", "", "", "", "")

    console.print(table)


@app.command()
def log(
    model: str = typer.Argument(..., help="Model name"),
    prompt_tokens: int = typer.Argument(..., help="Number of prompt tokens"),
    completion_tokens: int = typer.Argument(..., help="Number of completion tokens"),
    provider: str = typer.Option("openai", "--provider", "-p", help="Provider name"),
    task: str = typer.Option("chat", "--task", "-t", help="Task type"),
):
    """Log a usage entry for tracking."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    usage = LLMUsage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        provider=provider,
        task_type=TaskType(task),
    )

    with open(data_dir / "usage.jsonl", "a") as f:
        f.write(json.dumps(usage.model_dump(), default=str) + "\n")

    console.print(f"[green]✅ Logged: {model} — {prompt_tokens + completion_tokens:,} tokens[/green]")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
