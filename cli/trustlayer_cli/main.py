"""TrustLayer CLI — trust every AI output from your terminal."""

import typer
import httpx
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from typing import Optional

app = typer.Typer(
    name="trustlayer",
    help="TrustLayer — the universal AI trust layer. You bring the AI, we bring the trust.",
    rich_markup_mode="rich",
)

console = Console()

API_BASE = "http://localhost:8000"


def api(path: str, method: str = "GET", data: dict = None) -> dict:
    try:
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            if method == "POST":
                r = client.post(path, json=data)
            else:
                r = client.get(path)
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        console.print("[red]Cannot connect to TrustLayer server. Run: trustlayer server[/red]")
        raise typer.Exit(1)


@app.command()
def server():
    """Start the TrustLayer API server."""
    import uvicorn
    console.print(Panel("[bold green]TrustLayer Server[/bold green]\nStarting on http://localhost:8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


@app.command()
def verify(text: str = typer.Argument(help="Text to verify (or '-' to read from stdin)")):
    """Verify AI-generated content and get a trust score."""
    if text == "-":
        import sys
        text = sys.stdin.read()

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task("Analyzing content...", total=None)
        result = api("/api/verify", "POST", {"content": text})

    score = result["trust_score"]
    color = "green" if score >= 85 else "yellow" if score >= 60 else "red"
    label = result["trust_label"].upper()

    console.print(Panel(
        f"[bold {color}]Trust Score: {score}/100 ({label})[/bold {color}]\n\n{result['summary']}",
        title="[bold]TrustLayer Verification[/bold]",
        border_style=color,
    ))

    if result["issues"]:
        console.print("\n[bold yellow]Issues found:[/bold yellow]")
        for issue in result["issues"]:
            console.print(f"  • {issue}")


@app.command()
def ask(
    prompt: str = typer.Argument(help="Your question or task"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="AI provider to use"),
    model: str = typer.Option("llama3.2", "--model", "-m", help="Model to use"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip trust verification"),
):
    """Ask any connected AI and get a verified response."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as p:
        p.add_task(f"Asking {provider}/{model}...", total=None)
        result = api("/api/connectors/complete", "POST", {
            "provider": provider, "model": model, "prompt": prompt
        })

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    console.print(Panel(result["content"], title=f"[bold]{provider}/{model}[/bold]", border_style="blue"))
    console.print(f"[dim]Tokens: {result['tokens_in']}↑ {result['tokens_out']}↓ | Cost: ${result['cost_usd']:.4f} | Latency: {result['latency_ms']}ms[/dim]")

    if not no_verify:
        verify_result = api("/api/verify", "POST", {"content": result["content"], "context": prompt})
        score = verify_result["trust_score"]
        color = "green" if score >= 85 else "yellow" if score >= 60 else "red"
        console.print(f"\n[{color}]Trust Score: {score}/100[/{color}]", end="")
        if verify_result["issues"]:
            console.print(f" — {len(verify_result['issues'])} concern(s)")
        else:
            console.print(" — No concerns")


@app.command()
def compare(
    prompt: str = typer.Argument(help="Prompt to test across models"),
):
    """Compare the same prompt across multiple AI models."""
    providers = api("/api/connectors/")
    available = [p for p in providers if p["available"] and p["models"]]

    if not available:
        console.print("[yellow]No AI providers available. Check your config.[/yellow]")
        raise typer.Exit(1)

    # Build comparison targets
    targets = []
    for p in available[:3]:
        targets.append({"provider": p["name"], "model": p["models"][0]})

    console.print(f"[dim]Comparing across {len(targets)} model(s)...[/dim]")
    result = api("/api/compare", "POST", {"prompt": prompt, "providers": targets})

    table = Table(title="Model Comparison", show_header=True, header_style="bold")
    table.add_column("Provider/Model", style="cyan")
    table.add_column("Trust", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("Cost", justify="right")

    for r in result.get("ranked", []):
        score = r["trust_score"]
        color = "green" if score >= 85 else "yellow" if score >= 60 else "red"
        table.add_row(
            f"{r['provider']}/{r['model']}",
            f"[{color}]{score}[/{color}]",
            f"{r['latency_ms']}ms",
            f"${r['cost_usd']:.4f}",
        )

    console.print(table)
    if result.get("winner"):
        w = result["winner"]
        console.print(f"\n[green]Winner: {w['provider']}/{w['model']} ({w['trust_score']}/100 trust)[/green]")


@app.command()
def costs():
    """Show your AI spending dashboard."""
    result = api("/api/costs/summary")

    color = "red" if result["alert"] else "green"
    console.print(Panel(
        f"[bold]${result['total_usd']:.2f}[/bold] spent this {result['month']}\n"
        f"Budget: ${result['budget_usd']:.2f} ({result['budget_pct']}% used)",
        title="[bold]Cost Dashboard[/bold]",
        border_style=color,
    ))

    if result["alert_message"]:
        console.print(f"\n[red]⚠ {result['alert_message']}[/red]")

    if result["by_provider"]:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Provider")
        table.add_column("Cost", justify="right")
        for row in result["by_provider"]:
            table.add_row(row["provider"], f"${row['cost_usd']:.4f}")
        console.print(table)


@app.command()
def detect():
    """Detect all AI tools available on this machine."""
    result = api("/api/connectors/detect")
    console.print("\n[bold]Detected AI Tools:[/bold]")
    for name, found in result.items():
        status = "[green]✓[/green]" if found else "[dim]✗[/dim]"
        console.print(f"  {status} {name}")


@app.command()
def status():
    """Show TrustLayer status."""
    try:
        result = api("/")
        insights = api("/api/learn/insights")
        console.print(Panel(
            f"[green]TrustLayer v{result['version']} is running[/green]\n\n"
            f"Sessions tracked: {insights['total_interactions']}\n"
            f"Personalization: {insights['personalization_level']}%\n\n"
            f"{insights['message']}",
            title="[bold]TrustLayer Status[/bold]",
            border_style="green",
        ))
    except Exception:
        console.print("[red]TrustLayer is not running. Start with: trustlayer server[/red]")


if __name__ == "__main__":
    app()
